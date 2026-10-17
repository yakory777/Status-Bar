/*
 * Симулятор экрана: прогоняет сценарий через настоящий UI-код прошивки
 * и пишет кадры RGB565 подряд в один файл.
 *
 *   agent_sim <сценарий.txt> <кадры.rgb565> [fps] [длительность_мс] [писать_с_мс]
 *
 * Строка сценария: «<время_мс> <JSON>», например
 *   600 {"state":"start","title":"Почини тесты","agent":"codex"}
 * Пустые строки и строки с # игнорируются. Время модельное, не реальное.
 *
 * Строки {"sim":{...}} не уходят в прошивку, а настраивают «железо» симулятора:
 *   {"sim":{"battery":35,"charging":true}}   — батарея (battery:-1 — нет батареи)
 *   {"sim":{"wifi":3}}                        — уровень Wi-Fi (-1 — режим USB)
 *   {"sim":{"press":200}}                     — нажать кнопку на 200 мс (1500 — удержание)
 * Что плата отправила бы хосту (нажатия кнопки), печатается в stderr строками [tx].
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lvgl.h"
#include "protocol.h"
#include "ui_status.h"
#include "ui_screen.h"
#include "cJSON.h"
#include "sim_platform.h"
#include "ui_input.h"
#include "ui_sound.h"

#define W 536
#define H 240

static uint32_t sim_ms;
static uint16_t framebuf[W * H];

static uint32_t tick_cb(void) { return sim_ms; }

static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px)
{
    (void)area; (void)px;
    lv_display_flush_ready(disp);      /* DIRECT: буфер и есть кадр */
}

typedef struct { uint32_t t; char *json; } event_t;

static uint32_t release_at;      /* когда отпустить кнопку, нажатую из сценария */

/* {"sim":{...}} — настройки «железа»; true, если строка была такой */
static bool sim_command(const char *json)
{
    cJSON *j = cJSON_Parse(json);
    cJSON *sim = j ? cJSON_GetObjectItem(j, "sim") : NULL;
    if (!sim) { cJSON_Delete(j); return false; }
    static int pct = 78;
    static bool charging, present;
    cJSON *b = cJSON_GetObjectItem(sim, "battery"), *c = cJSON_GetObjectItem(sim, "charging");
    cJSON *w = cJSON_GetObjectItem(sim, "wifi");
    cJSON *press = cJSON_GetObjectItem(sim, "press");
    if (cJSON_IsNumber(press)) {
        ui_input_button(true);
        release_at = sim_ms + (uint32_t)press->valueint;
    }
    if (cJSON_IsNumber(b)) { present = b->valueint >= 0; if (present) pct = b->valueint; }
    if (cJSON_IsBool(c)) charging = cJSON_IsTrue(c);
    if (b || c) sim_set_battery(present, pct, charging);
    if (cJSON_IsNumber(w)) sim_set_wifi(w->valueint);
    cJSON_Delete(j);
    return true;
}

/* Яркость дисплея → затемнение кадра (0xD0 — обычная яркость, как UI_BRIGHT_ON) */
static void write_frame(FILE *out)
{
    static uint16_t dimmed[W * H];
    unsigned k = sim_brightness() * 256u / 0xD0;
    if (k >= 256) { fwrite(framebuf, sizeof framebuf, 1, out); return; }
    for (int i = 0; i < W * H; i++) {
        uint16_t p = framebuf[i];
        unsigned r = (p >> 11) * k >> 8, g = ((p >> 5) & 63) * k >> 8, b = (p & 31) * k >> 8;
        dimmed[i] = (uint16_t)(r << 11 | g << 5 | b);
    }
    fwrite(dimmed, sizeof dimmed, 1, out);
}

static int load(const char *path, event_t **out)
{
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(1); }
    int n = 0, cap = 64;
    event_t *ev = malloc(sizeof(event_t) * cap);
    char line[2048];
    while (fgets(line, sizeof line, f)) {
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '#' || *p == '\n' || *p == '\r' || !*p) continue;
        char *rest;
        unsigned long t = strtoul(p, &rest, 10);
        while (*rest == ' ' || *rest == '\t') rest++;
        rest[strcspn(rest, "\r\n")] = '\0';
        if (n == cap) ev = realloc(ev, sizeof(event_t) * (cap *= 2));
        ev[n].t = (uint32_t)t;
        ev[n].json = strdup(rest);
        n++;
    }
    fclose(f);
    *out = ev;
    return n;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s scenario.txt frames.rgb565 [fps] [duration_ms] [from_ms]\n", argv[0]);
        return 2;
    }
    int fps = argc > 3 ? atoi(argv[3]) : 30;
    event_t *ev;
    int n = load(argv[1], &ev);
    uint32_t end = argc > 4 && atoi(argv[4]) > 0 ? (uint32_t)atoi(argv[4]) : (n ? ev[n - 1].t + 3000 : 3000);
    uint32_t from = argc > 5 ? (uint32_t)atoi(argv[5]) : 0;   /* кадры раньше не пишем — для длинных сценариев */

    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t *disp = lv_display_create(W, H);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(disp, framebuf, NULL, sizeof framebuf, LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(disp, flush_cb);

    ui_status_create();
    ui_screen_init();
    ui_input_init();
    ui_sound_init();

    FILE *out = fopen(argv[2], "wb");
    if (!out) { perror(argv[2]); return 1; }

    int next = 0, frames = 0, bad = 0;
    for (sim_ms = 0; sim_ms <= end; ) {
        while (next < n && ev[next].t <= sim_ms) {
            proto_msg_t m;
            if (sim_command(ev[next].json))
                ;
            else if (protocol_parse(ev[next].json, &m))
                protocol_apply(&m, sim_ms);
            else {
                fprintf(stderr, "bad json at %u ms: %s\n", ev[next].t, ev[next].json);
                bad++;
            }
            next++;
        }
        protocol_tick(sim_ms);
        if (release_at && sim_ms >= release_at) {
            ui_input_button(false);
            release_at = 0;
        }
        /* продвигаем модельное время шагами по 4 мс (как часто зовётся lv_timer_handler
         * на плате) до момента следующего кадра — без накопления ошибки округления */
        uint32_t next_frame = (uint32_t)((uint64_t)(frames + 1) * 1000 / fps);
        while (sim_ms < next_frame) {
            uint32_t d = next_frame - sim_ms;
            sim_ms += d < 4 ? d : 4;
            lv_timer_handler();
        }
        frames++;
        if (sim_ms >= from) {
            lv_refr_now(disp);
            write_frame(out);
        }
    }
    fclose(out);
    fprintf(stderr, "%d frames, %d fps, %u ms, %d tones\n", frames, fps, end, sim_beeps());
    return bad ? 1 : 0;              /* битая строка в сценарии — ошибка для CI */
}
