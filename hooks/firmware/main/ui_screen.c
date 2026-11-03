/*
 * Диспетчер экранов.
 *
 *   заставка ──► сцена ожидания ──(задача пришла: маскот прыгает за кадр)──► экран задачи
 *                     ▲                                                          │
 *                     └──(«Готово» полторы минуты или SessionEnd: экран гаснет)──┘
 *
 * Плюс: конфетти на «Готово», сон маскота и тусклый экран через 10 мин без событий,
 * полное выключение через 30 мин, экран сопряжения с кодом поверх всего.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "platform.h"
#include "ui_draw.h"
#include "ui_i18n.h"
#include "ui_icons.h"
#include "ui_scene.h"
#include "ui_screen.h"
#include "ui_sound.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define FW_VERSION "0.2.0"


typedef enum { MODE_BOOT, MODE_IDLE, MODE_TO_TASK, MODE_TASK, MODE_TO_IDLE } mode_t_;

static mode_t_ mode = MODE_BOOT;
static lv_obj_t *splash, *confetti, *pairing, *toast, *toast_lbl;
static uint32_t toast_t0;
static uint32_t boot_t0, confetti_t0, last_activity, done_since;
static status_state_t cur_state = ST_IDLE;
static bool pending_task;          /* задача пришла во время заставки */
static bool asleep, screen_off;
static char pair_code[8];
static ui_theme_t scene_theme;
static char scene_name[16];

static float since_s(uint32_t t) { return lv_tick_elaps(t) / 1000.0f; }

/* ---------- маскоты для заставки (те же спрайты, что в сценах) ---------- */

static const char *const ROBOT[13] = {
    ".....LL.....", ".....DD.....", ".BBBBBBBBBB.", "BBBBBBBBBBBB", "BSSSSSSSSSSB",
    "BSEESSSSEESB", "BSEESSSSEESB", "BSEESSSSEESB", "BSSSSSSSSSSB", "BBBBBBBBBBBB",
    "DBBBBBBBBBBD", ".DDDDDDDDDD.", ".FFF....FFF.",
};
static const char *const SLIME[10] = {
    "....GGGG....", "..GGGGGGGG..", ".GHHGGGGGGG.", ".GHGGGGGGGG.", "GGGGGGGGGGGG",
    "GGGEEGGGEEGG", "GGGEEGGGEEGG", "GGGGGGGGGGGG", "GGGGGGGGGGGG", ".DDDDDDDDDD.",
};

/* rows — строки спрайта, keys — какие символы красить, cols — их цвета (по порядку) */
static void draw_ascii_sprite(dctx_t *d, const char *const *rows, int w, int h, const char *keys,
                              const uint32_t *cols, float x, float y, float bw, float bh, float k)
{
    uint8_t g[13 * 12];
    lv_color_t pal[8];
    int nk = (int)strlen(keys);
    for (int i = 0; i < nk; i++) pal[i + 1] = c_dim(c_hex(cols[i]), k);
    for (int yy = 0; yy < h; yy++)
        for (int xx = 0; xx < w; xx++) {
            const char *p = strchr(keys, rows[yy][xx]);
            g[yy * w + xx] = (uint8_t)(p && rows[yy][xx] != '.' ? (p - keys) + 1 : 0);
        }
    d_sprite(d, g, w, h, pal, x - bw / 2, y - bh, bw, bh, LV_OPA_COVER);
}

static const uint32_t ROBOT_COLS[] = { 0xD97757, 0xA04E34, 0x26140E, 0xA04E34, 0xFFD68C, 0xFAECDE };
static const uint32_t SLIME_COLS[] = { 0x10A37F, 0x78E6C4, 0x096C54, 0x061C16 };

/* ---------- заставка ---------- */

static void splash_draw(lv_event_t *e)
{
    dctx_t d = dctx_from_event(e);
    float t = since_s(boot_t0);
    float out = clamp01((t - (UI_SPLASH_MS / 1000.0f - 0.45f)) / 0.45f);   /* гаснет в конце */
    float k = 1 - out;
    d_fill(&d, lv_color_black());

    /* два маскота падают и пружинят: робот Claude и слайм Codex */
    for (int i = 0; i < 2; i++) {
        float t0 = 0.15f + i * 0.18f, x = UI_W / 2.0f + (i ? 36 : -36), ground = 112;
        if (t < t0) continue;
        float dt = t - t0, y, sx = 1, sy = 1;
        if (dt < 0.35f) {
            float q = ease_in(dt / 0.35f);
            y = lerpf(-60, ground, q);
            sy = 1 + 0.35f * q; sx = 1 / sqrtf(sy);
        } else {
            y = ground;
            float s = springf(dt - 0.35f, 3.2f, 5.0f) * 0.3f;
            sy = 1 - s; sx = 1 + s * 0.8f;
        }
        if (i == 0) draw_ascii_sprite(&d, ROBOT, 12, 13, "BDSFLE", ROBOT_COLS, x, y, 48 * sx, 52 * sy, k);
        else        draw_ascii_sprite(&d, SLIME, 12, 10, "GHDE", SLIME_COLS, x, y, 48 * sx, 40 * sy, k);
    }
    float tk = clamp01((t - 0.8f) / 0.4f) * k;
    const lv_font_t *ft = ui_status_font(1), *fs = ui_status_font(0);
    const char *title = "Agent Status Bar";
    float w = text_w(ft, title);
    d_text(&d, ft, title, (UI_W - w) / 2, 168, c_dim(c_hex(0xFFFFFF), tk), LV_OPA_COVER);
    char ver[32];
    snprintf(ver, sizeof ver, "Claude Code · Codex · v%s", FW_VERSION);
    w = text_w(fs, ver);
    d_text(&d, fs, ver, (UI_W - w) / 2, 200, c_dim(c_hex(0x8E8E93), tk), LV_OPA_COVER);
}

/* ---------- конфетти на «Готово» ---------- */

#define CONFETTI_N 64
#define CONFETTI_S 2.2f

static float rnd(uint32_t *s)                     /* детерминированно: одинаково на плате и в симуляторе */
{
    *s = *s * 1664525u + 1013904223u;
    return (*s >> 8) / 16777216.0f;
}

static void confetti_draw(lv_event_t *e)
{
    dctx_t d = dctx_from_event(e);
    float t = since_s(confetti_t0);
    if (t > CONFETTI_S) return;
    lv_color_t pal[6] = {
        ui_status_state_color(ST_DONE), ui_status_state_color(ST_WORK), ui_status_state_color(ST_WAIT),
        ui_status_state_color(ST_COMPACT), ui_status_state_color(ST_START), c_hex(0xFFFFFF),
    };
    uint32_t seed = 12345;
    float fade = 1 - clamp01((t - (CONFETTI_S - 0.5f)) / 0.5f);
    for (int i = 0; i < CONFETTI_N; i++) {
        float x0 = lerpf(40, UI_W - 40, rnd(&seed));
        float vx = lerpf(-150, 150, rnd(&seed));
        float vy = lerpf(-430, -200, rnd(&seed));
        float sz = 5 + 4 * rnd(&seed);
        float delay = 0.12f * rnd(&seed);
        lv_color_t c = pal[(int)(rnd(&seed) * 6) % 6];
        float tt = t - delay;
        if (tt < 0) continue;
        float x = x0 + vx * tt;
        float y = 200 + vy * tt + 0.5f * 560 * tt * tt;
        float wob = sinf(tt * 14 + i) * 0.5f + 0.5f;         /* «кувыркается»: меняет ширину */
        float w = sz * (0.25f + 0.75f * wob);
        d_rect(&d, x - w / 2, y, x + w / 2, y + sz * 0.7f, c, (lv_opa_t)(255 * fade), 1);
    }
}

/* ---------- сопряжение ---------- */

static void pairing_draw(lv_event_t *e)
{
    dctx_t d = dctx_from_event(e);
    d_fill(&d, lv_color_black());
    const lv_font_t *ft = ui_status_font(1), *fb = ui_status_font(2), *fs = ui_status_font(0);
    lv_color_t accent = ui_status_state_color(ST_WORK);
    const char *title = tr(TR_PAIR_TITLE);
    d_text(&d, ft, title, (UI_W - text_w(ft, title)) / 2, 74, c_hex(0xFFFFFF), LV_OPA_COVER);
    int n = (int)strlen(pair_code);
    float cell = 54, gap = 10, x = (UI_W - (n * cell + (n - 1) * gap)) / 2;
    for (int i = 0; i < n; i++) {
        float cx = x + i * (cell + gap);
        d_rect(&d, cx, 90, cx + cell, 90 + 62, ui_status_text_color(2), LV_OPA_COVER, 10);
        char ch[2] = { pair_code[i], 0 };
        d_text(&d, fb, ch, cx + (cell - text_w(fb, ch)) / 2, 136, accent, LV_OPA_COVER);
    }
    const char *hint1 = tr(TR_PAIR_HINT1);    /* проверка «тот же код», как при сопряжении Bluetooth */
    const char *hint2 = tr(TR_PAIR_HINT2);
    d_text(&d, fs, hint1, (UI_W - text_w(fs, hint1)) / 2, 190, ui_status_text_color(1), LV_OPA_COVER);
    d_text(&d, fs, hint2, (UI_W - text_w(fs, hint2)) / 2, 217, ui_status_text_color(1), LV_OPA_COVER);
}

void ui_screen_pairing(const char *code)
{
    if (code && *code) {
        strncpy(pair_code, code, sizeof pair_code - 1);
        pair_code[sizeof pair_code - 1] = '\0';
        lv_obj_remove_flag(pairing, LV_OBJ_FLAG_HIDDEN);
        lv_obj_invalidate(pairing);
        ui_screen_wake();
    } else {
        lv_obj_add_flag(pairing, LV_OBJ_FLAG_HIDDEN);
    }
}

/* ---------- переходы ---------- */

static void place_icons(bool task)
{
    lv_color_t on = ui_status_text_color(0), off = ui_status_text_color(2), txt = ui_status_text_color(1);
    ui_icons_set_colors(on, off, txt);
    if (task) {
        ui_icons_place(UI_W - 20, 30);          /* по центру строки с таймером */
        ui_status_set_right_inset(ui_icons_width() + 16);
    } else {
        ui_icons_place(UI_W - 16, 22);
    }
}

static void root_anim_cb(void *var, int32_t v)
{
    lv_obj_t *root = var;
    lv_obj_set_style_opa(root, (lv_opa_t)v, 0);
    lv_obj_set_style_translate_y(root, (255 - v) * 26 / 255, 0);
}

static void start_scene(void)
{
    scene_theme = ui_status_get_theme();
    strncpy(scene_name, ui_status_get_idle_scene(), sizeof scene_name - 1);
    ui_scene_start(scene_theme, scene_name);
    place_icons(false);
    ui_icons_set_opa(LV_OPA_COVER);
}

static void show_task_done_cb(void)
{
    lv_obj_t *root = ui_status_root();
    lv_obj_remove_flag(root, LV_OBJ_FLAG_HIDDEN);
    place_icons(true);
    ui_icons_set_opa(LV_OPA_COVER);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, root);
    lv_anim_set_exec_cb(&a, root_anim_cb);
    lv_anim_set_values(&a, 0, 255);
    lv_anim_set_duration(&a, 380);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
    mode = MODE_TASK;
}

static void go_task(void)
{
    if (mode == MODE_TASK || mode == MODE_TO_TASK) return;
    lv_obj_t *root = ui_status_root();
    lv_anim_delete(root, root_anim_cb);
    mode = MODE_TO_TASK;
    ui_scene_set_sleep(false);
    ui_scene_exit(show_task_done_cb);           /* маскот прыгает за кадр, потом выезжает экран задачи */
}

static void hide_root_ready_cb(lv_anim_t *a)
{
    lv_obj_add_flag(a->var, LV_OBJ_FLAG_HIDDEN);
    start_scene();
    mode = MODE_IDLE;
}

static void go_idle(void)
{
    if (mode == MODE_IDLE || mode == MODE_TO_IDLE) return;
    if (mode == MODE_TO_TASK) {                 /* задача отменилась, пока маскот прыгал */
        start_scene();
        mode = MODE_IDLE;
        return;
    }
    mode = MODE_TO_IDLE;
    lv_obj_t *root = ui_status_root();
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, root);
    lv_anim_set_exec_cb(&a, root_anim_cb);
    lv_anim_set_values(&a, 255, 0);
    lv_anim_set_duration(&a, 320);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in);
    lv_anim_set_ready_cb(&a, hide_root_ready_cb);
    lv_anim_start(&a);
}

/* ---------- сон и пробуждение ---------- */

bool ui_screen_wake(void)
{
    last_activity = lv_tick_get();
    bool was = asleep || screen_off;
    if (screen_off) {
        screen_off = false;
        lv_obj_remove_flag(lv_layer_top(), LV_OBJ_FLAG_HIDDEN);
        if (mode == MODE_IDLE) start_scene();
    }
    if (asleep) {
        asleep = false;
        ui_scene_set_sleep(false);
    }
    if (was) platform_set_brightness(UI_BRIGHT_ON);
    return was;
}

bool ui_screen_is_off(void) { return screen_off; }

void ui_screen_toggle(void)
{
    if (ui_screen_wake()) return;
    if (mode == MODE_IDLE) go_task();
    else if (mode == MODE_TASK) go_idle();
}

/* ---------- всплывающее сообщение ---------- */

void ui_screen_toast(const char *text, lv_color_t color)
{
    lv_label_set_text(toast_lbl, text);
    lv_obj_set_style_text_color(toast_lbl, color, 0);
    lv_obj_set_style_border_color(toast, c_mix(c_hex(0x3A3A3C), color, 0.45f), 0);
    if (mode == MODE_TASK) {                   /* на экране задачи — плашка целиком поверх счётчиков */
        lv_obj_set_size(toast, UI_W - 40, 46);
        lv_obj_set_style_radius(toast, 14, 0);
        lv_obj_align(toast, LV_ALIGN_BOTTOM_MID, 0, -16);
    } else {
        lv_obj_set_size(toast, LV_SIZE_CONTENT, 38);
        lv_obj_set_style_radius(toast, LV_RADIUS_CIRCLE, 0);
        lv_obj_update_layout(toast);
        lv_obj_align(toast, LV_ALIGN_BOTTOM_MID, 0, -12);
    }
    lv_obj_remove_flag(toast, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_opa(toast, LV_OPA_COVER, 0);
    lv_obj_set_style_translate_y(toast, 10, 0);
    toast_t0 = lv_tick_get();
}

/* ---------- реакция на сообщения ---------- */

void ui_screen_on_state(status_state_t st, bool activity)
{
    status_state_t prev = cur_state;
    cur_state = st;
    if (activity) ui_screen_wake();

    if (activity && st != prev) {                 /* звук на важные события */
        if (st == ST_WAIT) ui_sound_play(SND_WAIT);
        else if (st == ST_DONE) ui_sound_play(SND_DONE);
        else if (st == ST_ERROR) ui_sound_play(SND_ERROR);
    }
    if (st == ST_DONE && prev != ST_DONE) {
        done_since = lv_tick_get();
        if (mode == MODE_TASK) {
            confetti_t0 = lv_tick_get();
            lv_obj_remove_flag(confetti, LV_OBJ_FLAG_HIDDEN);
        }
    }

    if (mode == MODE_BOOT) {
        pending_task = ui_status_is_active(st) || st == ST_DONE;
        return;
    }
    if (ui_status_is_active(st)) {
        go_task();
    } else if (st == ST_IDLE) {
        go_idle();
    } else if (st == ST_DONE && mode == MODE_IDLE && prev != ST_DONE) {
        go_task();                              /* быстрая задача: старт и финиш пришли разом */
    }

    /* в ожидании поменялась тема или выбранная сцена — перезапускаем сцену */
    if (mode == MODE_IDLE && (scene_theme != ui_status_get_theme() ||
                              strcmp(scene_name, ui_status_get_idle_scene()))) {
        start_scene();
    }
    if (mode == MODE_TASK) place_icons(true);
}

/* ---------- таймер ---------- */

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    if (mode == MODE_BOOT) {
        lv_obj_invalidate(splash);
        if (lv_tick_elaps(boot_t0) >= UI_SPLASH_MS) {
            lv_obj_add_flag(splash, LV_OBJ_FLAG_HIDDEN);
            if (pending_task) {
                mode = MODE_IDLE;               /* через сцену не идём — сразу экран задачи */
                show_task_done_cb();
            } else {
                start_scene();
                mode = MODE_IDLE;
            }
        }
        return;
    }
    if (!lv_obj_has_flag(toast, LV_OBJ_FLAG_HIDDEN)) {
        uint32_t el = lv_tick_elaps(toast_t0);
        /* въезжает снизу и уезжает вниз за край — без полупрозрачности, чтобы не просвечивал текст под ним */
        int32_t ty = 0;
        if (el < 160) ty = (int32_t)(10 * (160 - el) / 160);
        else if (el > 1450) { float p = (el - 1450) / 250.0f; ty = (int32_t)(90 * p * p); }
        lv_obj_set_style_translate_y(toast, ty, 0);
        if (el > 1700) lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);
    }
    if (mode == MODE_IDLE && !screen_off)        /* в финале сцены экран залит цветом — значки уступают */
        ui_icons_set_opa((lv_opa_t)(255 * (1 - ui_scene_cover())));
    if (mode == MODE_TASK) place_icons(true);   /* ширина значков меняется (зарядка, звук) — таймер сдвигается */
    if (!lv_obj_has_flag(confetti, LV_OBJ_FLAG_HIDDEN)) {
        if (since_s(confetti_t0) > CONFETTI_S) lv_obj_add_flag(confetti, LV_OBJ_FLAG_HIDDEN);
        else lv_obj_invalidate(confetti);
    }

    /* «Готово» повисело — возвращаемся к сцене ожидания */
    if (mode == MODE_TASK && cur_state == ST_DONE && lv_tick_elaps(done_since) >= UI_DONE_TO_IDLE_MS)
        go_idle();

    /* сон и выключение — только когда задачи нет */
    bool quiet = mode == MODE_IDLE && !ui_status_is_active(cur_state);
    uint32_t idle_ms = lv_tick_elaps(last_activity);
    if (quiet && !asleep && !screen_off && idle_ms >= UI_SLEEP_AFTER_MS) {
        asleep = true;
        ui_scene_set_sleep(true);
        platform_set_brightness(UI_BRIGHT_SLEEP);
    }
    if (quiet && !screen_off && idle_ms >= UI_OFF_AFTER_MS) {
        screen_off = true;
        ui_scene_stop();
        lv_obj_add_flag(lv_layer_top(), LV_OBJ_FLAG_HIDDEN);
        platform_set_brightness(0);
    }
}

/* ---------- создание ---------- */

static lv_obj_t *mk_canvas(lv_obj_t *parent, lv_event_cb_t cb)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_size(o, UI_W, UI_H);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(o, cb, LV_EVENT_DRAW_MAIN, NULL);
    return o;
}

void ui_screen_init(void)
{
    lv_obj_t *scr = lv_screen_active();
    ui_scene_create(scr);
    lv_obj_move_to_index(ui_status_root(), -1);   /* экран задачи поверх сцены */
    lv_obj_add_flag(ui_status_root(), LV_OBJ_FLAG_HIDDEN);

    confetti = mk_canvas(scr, confetti_draw);
    lv_obj_add_flag(confetti, LV_OBJ_FLAG_HIDDEN);

    /* индикаторы — на верхнем слое, поверх и сцены, и экрана задачи */
    ui_icons_create(lv_layer_top(), ui_status_font(0));

    pairing = mk_canvas(lv_layer_top(), pairing_draw);
    lv_obj_add_flag(pairing, LV_OBJ_FLAG_HIDDEN);

    toast = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(toast);
    lv_obj_set_size(toast, LV_SIZE_CONTENT, 38);
    lv_obj_set_style_bg_color(toast, c_hex(0x1C1C1E), 0);
    lv_obj_set_style_bg_opa(toast, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(toast, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_pad_hor(toast, 18, 0);
    lv_obj_set_style_border_width(toast, 1, 0);
    lv_obj_set_style_border_color(toast, c_hex(0x3A3A3C), 0);
    lv_obj_remove_flag(toast, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    toast_lbl = lv_label_create(toast);
    lv_obj_set_style_text_font(toast_lbl, ui_status_font(0), 0);
    lv_obj_center(toast_lbl);
    lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);

    splash = mk_canvas(lv_layer_top(), splash_draw);
    ui_icons_to_front();                        /* батарея и Wi-Fi видны и на заставке, и при сопряжении */
    place_icons(false);
    boot_t0 = last_activity = lv_tick_get();
    mode = MODE_BOOT;
    platform_set_brightness(UI_BRIGHT_ON);
    lv_timer_create(tick_cb, 33, NULL);
}
