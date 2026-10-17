#include <stdio.h>
#include "platform.h"
#include "ui_draw.h"
#include "ui_icons.h"
#include "ui_sound.h"

/* Размеры значков в пикселях экрана */
#define H        24               /* высота полосы, всё центрируется по ней */
#define BAT_W    28
#define BAT_H    14
#define NUB_W    3
#define BOLT_W   10
#define WIFI_W   22
#define MUTE_W   20
#define GAP_TXT  6                /* значок — его подпись */
#define GAP      12               /* между группами */
#define OBJ_W    220              /* ширина объекта; рисуем от правого края */

/* Молния 5×7, «пиксель» 2×2 */
static const char *const BOLT_MAP[7] = {
    "...##", "..##.", ".##..", "#####", "..##.", ".##..", "##...",
};

static lv_obj_t *obj;
static const lv_font_t *font;
static platform_battery_t bat;
static int wifi = -1;
static bool muted;
static lv_color_t col_on, col_off, col_text;
static char bat_txt[8];
static uint32_t charge_t0;

static lv_color_t battery_color(int pct)
{
    if (pct > 50) return c_hex(0x30D158);
    if (pct > 20) return c_hex(0xFF9F0A);
    return c_hex(0xFF453A);
}

static float txt_w(void) { return text_w(font, bat_txt); }

int32_t ui_icons_width(void)
{
    float w = BAT_W + NUB_W + GAP_TXT + txt_w();
    if (bat.charging) w += BOLT_W + 4;
    w += GAP + WIFI_W;
    if (muted) w += GAP + MUTE_W;
    return (int32_t)(w + 0.5f);
}

static void draw_battery(dctx_t *d, float x, float cy)
{
    float y = cy - BAT_H / 2.0f;
    bool on = bat.present;
    lv_color_t frame = on ? col_on : col_off;
    /* корпус — рамка 2 px со скруглением, носик справа */
    d_rect(d, x, y, x + BAT_W, y + BAT_H, frame, LV_OPA_COVER, 4);
    d_rect(d, x + 2, y + 2, x + BAT_W - 2, y + BAT_H - 2, lv_color_black(), LV_OPA_COVER, 2);
    d_rect(d, x + BAT_W + 1, cy - 3, x + BAT_W + NUB_W, cy + 3, frame, LV_OPA_COVER, 1);
    if (!on) return;

    float inner = BAT_W - 6;
    float level = bat.pct / 100.0f;
    if (bat.charging) {                   /* бегущая заливка от текущего уровня до полной */
        float p = (float)(lv_tick_elaps(charge_t0) % 1600) / 1600.0f;
        level = lerpf(level, 1.0f, ease_out_q(p));
    }
    float fw = inner * level;
    if (fw < 2 && bat.pct > 0) fw = 2;    /* хоть полоска, пока заряд не ноль */
    if (fw > 0)
        d_rect(d, x + 3, y + 3, x + 3 + fw, y + BAT_H - 3, battery_color(bat.pct), LV_OPA_COVER, 1);
}

static void draw_bolt(dctx_t *d, float x, float cy, lv_color_t c)
{
    float y = cy - 7;
    for (int r = 0; r < 7; r++)
        for (int k = 0; k < 5; k++)
            if (BOLT_MAP[r][k] == '#')
                d_rect(d, x + k * 2, y + r * 2, x + k * 2 + 2, y + r * 2 + 2, c, LV_OPA_COVER, 0);
}

static void draw_wifi(dctx_t *d, float x, float cy)
{
    /* веер: точка и три дуги; нет Wi-Fi — всё тусклое и перечёркнуто */
    float cx = x + WIFI_W / 2.0f, by = cy + 7;
    static const float R[3] = { 6, 10.5f, 15 };
    lv_color_t dim = c_mix(col_off, col_text, 0.35f);   /* погасшие дуги — видны, но не спорят */
    for (int i = 0; i < 3; i++) {
        lv_color_t c = wifi >= i + 1 ? col_on : dim;
        d_arc(d, cx, by, R[i], 2.6f, 228, 312, c, LV_OPA_COVER);
    }
    d_circle(d, cx, by - 1, 2, wifi >= 0 ? col_on : dim, LV_OPA_COVER);
    if (wifi < 0)
        d_line(d, x + 3, cy + 8, x + WIFI_W - 3, cy - 8, 2, col_text, LV_OPA_COVER);
}

static void draw_mute(dctx_t *d, float x, float cy)
{
    /* динамик и крестик */
    d_rect(d, x, cy - 3, x + 4, cy + 3, col_text, LV_OPA_COVER, 0);
    for (int i = 0; i < 5; i++)
        d_rect(d, x + 4 + i, cy - 3 - i, x + 5 + i, cy + 3 + i, col_text, LV_OPA_COVER, 0);
    d_line(d, x + 13, cy - 3, x + 19, cy + 3, 2, col_text, LV_OPA_COVER);
    d_line(d, x + 13, cy + 3, x + 19, cy - 3, 2, col_text, LV_OPA_COVER);
}

static void draw_cb(lv_event_t *e)
{
    dctx_t d = dctx_from_event(e);
    float x = (float)lv_obj_get_width(lv_event_get_target(e)) - NUB_W;
    float cy = H / 2.0f;

    x -= BAT_W;
    draw_battery(&d, x, cy);
    if (bat.charging) {
        x -= 4 + BOLT_W;
        draw_bolt(&d, x, cy, battery_color(bat.pct));
    }
    x -= GAP_TXT + txt_w();
    d_text(&d, font, bat_txt, x, cy + cap_height(font) / 2.0f, col_text, LV_OPA_COVER);

    x -= GAP + WIFI_W;
    draw_wifi(&d, x, cy);

    if (muted) {
        x -= GAP + MUTE_W;
        draw_mute(&d, x, cy);
    }
}

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    static uint32_t last_read;
    if (!last_read || lv_tick_elaps(last_read) > 1000) {
        last_read = lv_tick_get();
        ui_icons_refresh();
    }
    if (bat.charging) lv_obj_invalidate(obj);   /* анимация заливки */
}

void ui_icons_refresh(void)
{
    platform_battery_t b = platform_battery();
    int w = platform_wifi_level();
    bool m = ui_sound_muted();
    bool changed = b.present != bat.present || b.pct != bat.pct || b.charging != bat.charging ||
                   w != wifi || m != muted;
    if (b.charging && !bat.charging) charge_t0 = lv_tick_get();
    bat = b;
    wifi = w;
    muted = m;
    if (bat.present) snprintf(bat_txt, sizeof bat_txt, "%d%%", bat.pct);
    else snprintf(bat_txt, sizeof bat_txt, "USB");
    if (changed) lv_obj_invalidate(obj);
}

void ui_icons_create(lv_obj_t *parent, const lv_font_t *f)
{
    font = f;
    col_on = c_hex(0xFFFFFF);
    col_off = c_hex(0x3A3A3C);
    col_text = c_hex(0x8E8E93);
    obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_set_size(obj, OBJ_W, H);
    lv_obj_remove_flag(obj, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(obj, draw_cb, LV_EVENT_DRAW_MAIN, NULL);
    ui_icons_refresh();
    lv_timer_create(tick_cb, 100, NULL);
}

void ui_icons_place(int32_t right, int32_t center_y)
{
    lv_obj_set_pos(obj, right - OBJ_W, center_y - H / 2);   /* не get_width: до разметки он 0 */
}

void ui_icons_to_front(void) { lv_obj_move_foreground(obj); }

void ui_icons_set_opa(lv_opa_t opa) { lv_obj_set_style_opa(obj, opa, 0); }

void ui_icons_set_colors(lv_color_t on, lv_color_t off, lv_color_t text)
{
    if (lv_color_eq(on, col_on) && lv_color_eq(off, col_off) && lv_color_eq(text, col_text)) return;
    col_on = on;
    col_off = off;
    col_text = text;
    lv_obj_invalidate(obj);
}
