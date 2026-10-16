/*
 * Экран статуса агента — 536x240, LVGL 9.
 * Анимации: плавная смена цвета, заливка сегментов, пульсация,
 * счётчик процентов, появление текста шага.
 */
#include <stdint.h>
#include <string.h>
#include "lvgl.h"
#include "ui_status.h"

#define SCR_W    536
#define M        20
#define BAR_Y    146
#define BAR_H    14
#define GAP      8
#define MAX_SEG  12

#define C_TEXT   0xFFFFFF
#define C_GRAY   0x8E8E93
#define C_EMPTY  0x1C1C1E

/* Шрифты встроены в прошивку (main/CMakeLists.txt → EMBED_FILES) */
extern const uint8_t ttf_reg_start[]  asm("_binary_DejaVuSans_ttf_start");
extern const uint8_t ttf_reg_end[]    asm("_binary_DejaVuSans_ttf_end");
extern const uint8_t ttf_bold_start[] asm("_binary_DejaVuSans_Bold_ttf_start");
extern const uint8_t ttf_bold_end[]   asm("_binary_DejaVuSans_Bold_ttf_end");

static lv_font_t *f_small, *f_title, *f_big;

static lv_obj_t *pill, *dot, *lbl_state, *lbl_time, *lbl_title, *lbl_step;
static lv_obj_t *lbl_count, *lbl_sub, *lbl_pct;
static lv_obj_t *seg_bg[MAX_SEG], *seg_fill[MAX_SEG];
static int32_t   fill_w[MAX_SEG];

static struct {
    status_state_t state;
    lv_color_t color;          /* текущий (анимируемый) акцентный цвет */
    int done, total;
    int32_t seg_w;
    int active;                /* индекс сегмента «в работе» или -1 */
    int pct;                   /* показанный процент */
    uint32_t start_tick;
} S;

static lv_color_t col_from, col_to;

/* ---------- цвета и тексты ---------- */

static uint32_t state_hex(status_state_t s)
{
    switch (s) {
    case ST_START: return 0xFF453A;   /* красный    */
    case ST_WORK:  return 0xFF9F0A;   /* оранжевый  */
    case ST_WAIT:  return 0xFFD60A;   /* жёлтый     */
    case ST_DONE:  return 0x30D158;   /* зелёный    */
    default:       return C_GRAY;
    }
}

static const char *state_text(status_state_t s)
{
    switch (s) {
    case ST_START: return "Старт";
    case ST_WORK:  return "В работе";
    case ST_WAIT:  return "Ждёт вас";
    case ST_DONE:  return "Готово";
    default:       return "Ожидание";
    }
}

status_state_t ui_status_parse_state(const char *s)
{
    if (!s)                      return ST_WORK;
    if (!strcmp(s, "idle"))      return ST_IDLE;
    if (!strcmp(s, "start"))     return ST_START;
    if (!strcmp(s, "wait"))      return ST_WAIT;
    if (!strcmp(s, "done"))      return ST_DONE;
    return ST_WORK;
}

status_state_t ui_status_get_state(void) { return S.state; }

static bool is_active(status_state_t s)
{
    return s == ST_START || s == ST_WORK || s == ST_WAIT;
}

static lv_color_t tint(lv_color_t c) { return lv_color_mix(c, lv_color_black(), 50); }

/* ---------- базовые объекты ---------- */

static lv_obj_t *mk_box(lv_obj_t *parent, uint32_t hex, int32_t radius)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(o, lv_color_hex(hex), 0);
    lv_obj_set_style_radius(o, radius, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    return o;
}

static lv_obj_t *mk_label(lv_obj_t *parent, const lv_font_t *font, uint32_t hex)
{
    lv_obj_t *l = lv_label_create(parent);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, lv_color_hex(hex), 0);
    lv_label_set_text(l, "");
    return l;
}

/* ---------- анимации ---------- */

static void apply_accent(lv_color_t c)
{
    lv_obj_set_style_bg_color(pill, tint(c), 0);
    lv_obj_set_style_bg_color(dot, c, 0);
    lv_obj_set_style_text_color(lbl_state, c, 0);
    lv_obj_set_style_text_color(lbl_pct, c, 0);
    for (int i = 0; i < MAX_SEG; i++)
        lv_obj_set_style_bg_color(seg_fill[i], c, 0);
    if (S.active >= 0)
        lv_obj_set_style_bg_color(seg_bg[S.active], lv_color_mix(c, lv_color_black(), 40), 0);
}

static void color_cb(void *var, int32_t v)
{
    (void)var;
    S.color = lv_color_mix(col_to, col_from, (uint8_t)v);
    apply_accent(S.color);
}

static void accent_to(lv_color_t target)
{
    lv_anim_delete(&S, color_cb);
    col_from = S.color;
    col_to   = target;

    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, &S);
    lv_anim_set_exec_cb(&a, color_cb);
    lv_anim_set_values(&a, 0, 255);
    lv_anim_set_duration(&a, 500);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
}

static void opa_cb(void *obj, int32_t v) { lv_obj_set_style_opa(obj, (lv_opa_t)v, 0); }

static void pulse_start(lv_obj_t *o, uint32_t period)
{
    lv_anim_delete(o, opa_cb);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, opa_cb);
    lv_anim_set_values(&a, LV_OPA_COVER, LV_OPA_30);
    lv_anim_set_duration(&a, period);
    lv_anim_set_playback_duration(&a, period);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
    lv_anim_start(&a);
}

static void pulse_stop(lv_obj_t *o)
{
    lv_anim_delete(o, opa_cb);
    lv_obj_set_style_opa(o, LV_OPA_COVER, 0);
}

static void fade_in(lv_obj_t *o, uint32_t ms)
{
    lv_anim_delete(o, opa_cb);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, opa_cb);
    lv_anim_set_values(&a, LV_OPA_TRANSP, LV_OPA_COVER);
    lv_anim_set_duration(&a, ms);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
}

static void width_cb(void *obj, int32_t v)
{
    lv_obj_set_width(obj, v);
    fill_w[(intptr_t)lv_obj_get_user_data(obj)] = v;
}

static void anim_width(int i, int32_t to, uint32_t delay)
{
    lv_obj_t *o = seg_fill[i];
    lv_anim_delete(o, width_cb);
    if (fill_w[i] == to) return;

    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, width_cb);
    lv_anim_set_values(&a, fill_w[i], to);
    lv_anim_set_duration(&a, 450);
    lv_anim_set_delay(&a, delay);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
}

static void pct_cb(void *var, int32_t v)
{
    (void)var;
    S.pct = v;
    lv_label_set_text_fmt(lbl_pct, "%d%%", (int)v);
}

static void anim_pct(int to)
{
    lv_anim_delete(&S.pct, pct_cb);
    if (S.pct == to) return;
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, &S.pct);
    lv_anim_set_exec_cb(&a, pct_cb);
    lv_anim_set_values(&a, S.pct, to);
    lv_anim_set_duration(&a, 600);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
}

static void clock_cb(lv_timer_t *t)
{
    (void)t;
    if (!is_active(S.state)) return;
    uint32_t s = lv_tick_elaps(S.start_tick) / 1000;
    lv_label_set_text_fmt(lbl_time, "%02u:%02u", (unsigned)(s / 60), (unsigned)(s % 60));
}

/* ---------- сегменты ---------- */

static void layout_segments(int total)
{
    int32_t old_w = S.seg_w;
    S.seg_w = (SCR_W - 2 * M - GAP * (total - 1)) / total;

    for (int i = 0; i < MAX_SEG; i++) {
        lv_anim_delete(seg_fill[i], width_cb);
        if (i >= total) {
            lv_obj_add_flag(seg_bg[i], LV_OBJ_FLAG_HIDDEN);
            fill_w[i] = 0;
            lv_obj_set_width(seg_fill[i], 0);
            continue;
        }
        lv_obj_remove_flag(seg_bg[i], LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_pos(seg_bg[i], M + i * (S.seg_w + GAP), BAR_Y);
        lv_obj_set_size(seg_bg[i], S.seg_w, BAR_H);
        /* пересчитываем уже залитую часть под новую ширину */
        fill_w[i] = old_w ? fill_w[i] * S.seg_w / old_w : 0;
        lv_obj_set_size(seg_fill[i], fill_w[i], BAR_H);
    }
}

/* ---------- API ---------- */

void ui_status_create(void)
{
    f_small = lv_tiny_ttf_create_data(ttf_reg_start,  ttf_reg_end  - ttf_reg_start,  18);
    f_title = lv_tiny_ttf_create_data(ttf_bold_start, ttf_bold_end - ttf_bold_start, 27);
    f_big   = lv_tiny_ttf_create_data(ttf_bold_start, ttf_bold_end - ttf_bold_start, 40);

    lv_obj_t *scr = lv_screen_active();
    lv_obj_set_style_bg_color(scr, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    /* Пилюля статуса: точка + текст, ширина по содержимому */
    pill = mk_box(scr, 0x222222, LV_RADIUS_CIRCLE);
    lv_obj_set_pos(pill, M, 16);
    lv_obj_set_size(pill, LV_SIZE_CONTENT, 32);
    lv_obj_set_style_pad_left(pill, 14, 0);
    lv_obj_set_style_pad_right(pill, 16, 0);
    lv_obj_set_style_pad_column(pill, 10, 0);
    lv_obj_set_flex_flow(pill, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(pill, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);

    dot = mk_box(pill, C_GRAY, LV_RADIUS_CIRCLE);
    lv_obj_set_size(dot, 12, 12);
    lbl_state = mk_label(pill, f_small, C_GRAY);

    lbl_time = mk_label(scr, f_small, C_GRAY);
    lv_label_set_text(lbl_time, "00:00");
    lv_obj_align(lbl_time, LV_ALIGN_TOP_RIGHT, -M, 22);

    lbl_title = mk_label(scr, f_title, C_TEXT);
    lv_obj_set_width(lbl_title, SCR_W - 2 * M);
    lv_label_set_long_mode(lbl_title, LV_LABEL_LONG_DOT);
    lv_obj_set_pos(lbl_title, M, 62);

    lbl_step = mk_label(scr, f_small, C_GRAY);
    lv_obj_set_width(lbl_step, SCR_W - 2 * M);
    lv_label_set_long_mode(lbl_step, LV_LABEL_LONG_DOT);
    lv_obj_set_pos(lbl_step, M, 106);

    for (int i = 0; i < MAX_SEG; i++) {
        seg_bg[i] = mk_box(scr, C_EMPTY, BAR_H / 2);
        lv_obj_set_style_clip_corner(seg_bg[i], true, 0);
        seg_fill[i] = mk_box(seg_bg[i], C_GRAY, 0);
        lv_obj_set_user_data(seg_fill[i], (void *)(intptr_t)i);
        lv_obj_set_size(seg_fill[i], 0, BAR_H);
        fill_w[i] = 0;
    }

    lbl_count = mk_label(scr, f_big, C_TEXT);
    lv_obj_set_pos(lbl_count, M, 178);

    lbl_sub = mk_label(scr, f_small, C_GRAY);
    lv_label_set_text(lbl_sub, "задач готово");

    lbl_pct = mk_label(scr, f_big, C_GRAY);
    lv_label_set_text(lbl_pct, "0%");
    lv_obj_align(lbl_pct, LV_ALIGN_TOP_RIGHT, -M, 178);

    S.state  = ST_IDLE;
    S.color  = lv_color_hex(C_GRAY);
    S.active = -1;
    S.total  = 0;
    S.seg_w  = 0;

    lv_timer_create(clock_cb, 500, NULL);

    ui_status_apply(ST_IDLE, "Жду задачу", "Отправьте задачу агенту", 0, 1);
    lv_label_set_text(lbl_state, state_text(ST_IDLE));
}

void ui_status_apply(status_state_t st, const char *title, const char *step,
                     int done, int total)
{
    if (total < 1)       total = 1;
    if (total > MAX_SEG) total = MAX_SEG;
    if (done < 0)        done = 0;
    if (done > total)    done = total;
    if (st == ST_DONE)   done = total;

    int prev_done = S.done;

    /* Секундомер стартует с новой задачей */
    if (is_active(st) && !is_active(S.state)) {
        S.start_tick = lv_tick_get();
        lv_label_set_text(lbl_time, "00:00");
    }

    /* Тексты */
    if (title && strcmp(title, lv_label_get_text(lbl_title)))
        lv_label_set_text(lbl_title, title);
    if (step && strcmp(step, lv_label_get_text(lbl_step))) {
        lv_label_set_text(lbl_step, step);
        fade_in(lbl_step, 300);
    }

    /* Геометрия сегментов меняется, только если изменилось число задач */
    if (total != S.total) {
        layout_segments(total);
        S.total = total;
    }

    /* Активный сегмент: тот, что сейчас в работе */
    int old_active = S.active;
    S.active = (is_active(st) && done < total) ? done : -1;
    if (old_active >= 0 && old_active != S.active) {
        lv_obj_set_style_bg_color(seg_bg[old_active], lv_color_hex(C_EMPTY), 0);
        pulse_stop(seg_fill[old_active]);
    }

    /* Смена состояния → плавный переход цвета */
    if (st != S.state) {
        lv_label_set_text(lbl_state, state_text(st));
        accent_to(lv_color_hex(state_hex(st)));
    } else {
        apply_accent(S.color);
    }
    S.state = st;

    /* Заливка сегментов; при завершении — «волной» слева направо */
    for (int i = 0; i < total; i++) {
        int32_t target = (i < done) ? S.seg_w
                       : (i == S.active ? S.seg_w * 2 / 5 : 0);
        uint32_t delay = (st == ST_DONE && i >= prev_done) ? (uint32_t)(i - prev_done) * 70 : 0;
        anim_width(i, target, delay);
    }

    /* Пульсация: точка и активный сегмент «дышат», пока идёт работа */
    if (is_active(st)) {
        uint32_t period = (st == ST_WAIT) ? 450 : 900;
        pulse_start(dot, period);
        if (S.active >= 0) pulse_start(seg_fill[S.active], period);
    } else {
        pulse_stop(dot);
    }

    /* Счётчики */
    S.done = done;
    lv_label_set_text_fmt(lbl_count, "%d/%d", done, total);
    lv_obj_align_to(lbl_sub, lbl_count, LV_ALIGN_OUT_RIGHT_BOTTOM, 12, -8);
    anim_pct(done * 100 / total);
}
