/*
 * Экран задачи — 536x240, LVGL 9.
 *
 * Состояния: ожидание, старт, работа, ждёт вас, готово, ошибка, сжатие контекста.
 * Анимации: плавная смена цвета, заливка сегментов, пульсация текущего шага,
 * счётчик процентов, тряска при ошибке, «утрамбовка» полосы при сжатии,
 * нарастающее напоминание, если подтверждения ждут дольше минуты.
 * Бейджи: активные субагенты и другие сессии. Плашка «Нет связи», если хост замолчал.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "lvgl.h"
#include "ui_draw.h"
<<<<<<< HEAD
#include "ui_i18n.h"
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
#include "ui_status.h"
#include "ui_sound.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define SCR_W    536
#define SCR_H    240
#define M        20
#define BAR_Y    146
#define BAR_H    14
#define GAP      8
#define MAX_SEG  12

/* Шрифты встроены в прошивку (main/CMakeLists.txt → EMBED_FILES) */
extern const uint8_t ttf_reg_start[]  asm("_binary_DejaVuSans_ttf_start");
extern const uint8_t ttf_reg_end[]    asm("_binary_DejaVuSans_ttf_end");
extern const uint8_t ttf_bold_start[] asm("_binary_DejaVuSans_Bold_ttf_start");
extern const uint8_t ttf_bold_end[]   asm("_binary_DejaVuSans_Bold_ttf_end");

/* ---------- темы ---------- */

typedef struct {
    uint32_t state[ST_COUNT];
    uint32_t text, gray, empty;
} theme_def_t;

static const theme_def_t THEMES[THEME_COUNT] = {
    [THEME_CLAUDE] = {
        .state = {
            [ST_IDLE] = 0x8E8E93, [ST_START] = 0xFF453A, [ST_WORK] = 0xFF9F0A,
            [ST_WAIT] = 0xFFD60A, [ST_DONE] = 0x30D158, [ST_ERROR] = 0xFF2D55,
            [ST_COMPACT] = 0x64D2FF,
        },
        .text = 0xFFFFFF, .gray = 0x8E8E93, .empty = 0x1C1C1E,
    },
    [THEME_CODEX] = {
        .state = {
            [ST_IDLE] = 0x8E8EA0, [ST_START] = 0xECECF1, [ST_WORK] = 0x10A37F,
            [ST_WAIT] = 0xF5A524, [ST_DONE] = 0x6EE7B7, [ST_ERROR] = 0xEF4444,
            [ST_COMPACT] = 0x60A5FA,
        },
        .text = 0xECECF1, .gray = 0x8E8EA0, .empty = 0x26272E,
    },
};

<<<<<<< HEAD
/* Подписи состояний — в ui_i18n.c (TR_ST_IDLE … TR_ST_COMPACT в том же порядке, что ST_*) */
static const char *state_text(status_state_t st) { return tr((tr_id_t)(TR_ST_IDLE + st)); }
=======
static const char *const STATE_TEXT[ST_COUNT] = {
    [ST_IDLE] = "Ожидание", [ST_START] = "Старт", [ST_WORK] = "В работе",
    [ST_WAIT] = "Ждёт вас", [ST_DONE] = "Готово", [ST_ERROR] = "Ошибка",
    [ST_COMPACT] = "Сжатие",
};
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046

/* ---------- объекты ---------- */

static lv_font_t *f_small, *f_title, *f_big;

static lv_obj_t *root;                         /* всё содержимое экрана задачи */
static lv_obj_t *topbar, *pill, *dot, *lbl_state;
static lv_obj_t *badge_sub, *lbl_sub_n, *badge_others, *lbl_others;
static lv_obj_t *lbl_time, *title_box, *lbl_title, *lbl_step;
static lv_obj_t *lbl_count, *lbl_count_sub, *lbl_pct;
static lv_obj_t *seg_bg[MAX_SEG], *seg_fill[MAX_SEG];
static int32_t   fill_w[MAX_SEG];
static lv_obj_t *frame;                        /* рамка-напоминание при долгом ожидании */
<<<<<<< HEAD
static lv_obj_t *link_banner, *link_txt;       /* «Нет связи» */
=======
static lv_obj_t *link_banner;                  /* «Нет связи» */
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
static lv_obj_t *approve_box, *approve_fill, *approve_lbl, *approve_lbl_inv;   /* решение кнопкой */
static bool approve_on;

static struct {
    ui_theme_t theme;
    char idle_scene[16];
    status_state_t state;
    lv_color_t color;          /* текущий (анимируемый) акцентный цвет */
    int done, total;
    int32_t seg_w;
    int active;                /* индекс сегмента «в работе» или -1 */
    int pct;                   /* показанный процент */
    uint32_t start_tick;
    uint32_t wait_since;
    int wait_minutes;          /* сколько минут уже показано в напоминании, 0 — не эскалировано */
    bool link_ok;
<<<<<<< HEAD
    bool had_task;             /* была ли уже задача (иначе на экране подпись ожидания) */
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    int32_t bar_h;             /* текущая высота полосы (меняется при «утрамбовке») */
} S;

static lv_color_t col_from, col_to;

static const theme_def_t *T(void) { return &THEMES[S.theme]; }
static lv_color_t hex(uint32_t c) { return lv_color_hex(c); }

/* ---------- состояния ---------- */

status_state_t ui_status_parse_state(const char *s)
{
    if (!s)                      return ST_WORK;
    if (!strcmp(s, "idle"))      return ST_IDLE;
    if (!strcmp(s, "start"))     return ST_START;
    if (!strcmp(s, "wait"))      return ST_WAIT;
    if (!strcmp(s, "done"))      return ST_DONE;
    if (!strcmp(s, "error"))     return ST_ERROR;
    if (!strcmp(s, "compact"))   return ST_COMPACT;
    return ST_WORK;
}

status_state_t ui_status_get_state(void) { return S.state; }
ui_theme_t ui_status_get_theme(void) { return S.theme; }
const char *ui_status_get_idle_scene(void) { return S.idle_scene; }
bool ui_status_link_ok(void) { return S.link_ok; }

bool ui_status_is_active(status_state_t s)
{
    return s == ST_START || s == ST_WORK || s == ST_WAIT || s == ST_ERROR || s == ST_COMPACT;
}

static lv_color_t tint(lv_color_t c) { return lv_color_mix(c, lv_color_black(), 50); }

/* ---------- базовые объекты ---------- */

static lv_obj_t *mk_box(lv_obj_t *parent, uint32_t c, int32_t radius)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(o, hex(c), 0);
    lv_obj_set_style_radius(o, radius, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    return o;
}

static lv_obj_t *mk_label(lv_obj_t *parent, const lv_font_t *font, uint32_t c)
{
    lv_obj_t *l = lv_label_create(parent);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, hex(c), 0);
    lv_label_set_text(l, "");
    return l;
}

static lv_obj_t *mk_row(lv_obj_t *parent, int32_t gap)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_size(o, LV_SIZE_CONTENT, LV_SIZE_CONTENT);
    lv_obj_set_flex_flow(o, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(o, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_column(o, gap, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    return o;
}

static lv_obj_t *mk_badge(lv_obj_t *parent)
{
    lv_obj_t *b = mk_row(parent, 6);
    lv_obj_set_style_bg_opa(b, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(b, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_height(b, 32);
    lv_obj_set_style_pad_hor(b, 12, 0);
    return b;
}

/* ---------- анимации ---------- */

static void apply_accent(lv_color_t c)
{
    lv_obj_set_style_bg_color(pill, tint(c), 0);
    lv_obj_set_style_bg_color(dot, c, 0);
    lv_obj_set_style_text_color(lbl_state, c, 0);
    lv_obj_set_style_text_color(lbl_pct, c, 0);
    lv_obj_set_style_border_color(frame, c, 0);
    for (int i = 0; i < MAX_SEG; i++)
        lv_obj_set_style_bg_color(seg_fill[i], c, 0);
    if (S.active >= 0)
        lv_obj_set_style_bg_color(seg_bg[S.active], lv_color_mix(c, lv_color_black(), 40), 0);
    lv_obj_set_style_text_color(lbl_step, S.state == ST_ERROR ? c : hex(T()->gray), 0);
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

static void pulse_start(lv_obj_t *o, uint32_t period, lv_opa_t low)
{
    lv_anim_delete(o, opa_cb);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, opa_cb);
    lv_anim_set_values(&a, LV_OPA_COVER, low);
    lv_anim_set_duration(&a, period);
    lv_anim_set_playback_duration(&a, period);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
    lv_anim_start(&a);
}

static void pulse_stop(lv_obj_t *o, lv_opa_t rest)
{
    lv_anim_delete(o, opa_cb);
    lv_obj_set_style_opa(o, rest, 0);
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

/* Ошибка: пилюля статуса трясётся с затуханием */
static void shake_cb(void *obj, int32_t v)
{
    float p = v / 1000.0f;
    int32_t dx = (int32_t)lroundf(9.0f * sinf(p * 6.0f * (float)M_PI) * (1.0f - p));
    lv_obj_set_style_translate_x(obj, dx, 0);
}

static void shake(lv_obj_t *o)
{
    lv_anim_delete(o, shake_cb);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, shake_cb);
    lv_anim_set_values(&a, 0, 1000);
    lv_anim_set_duration(&a, 550);
    lv_anim_start(&a);
}

/* Сжатие контекста: полоса прогресса «утрамбовывается» по высоте */
static void apply_bar_height(int32_t h)
{
    S.bar_h = h;
    for (int i = 0; i < S.total && i < MAX_SEG; i++) {
        lv_obj_set_y(seg_bg[i], BAR_Y + (BAR_H - h) / 2);
        lv_obj_set_height(seg_bg[i], h);
        lv_obj_set_style_radius(seg_bg[i], h / 2, 0);
        lv_obj_set_height(seg_fill[i], h);
    }
}

static void squeeze_cb(void *var, int32_t v) { (void)var; apply_bar_height(v); }

static void squeeze_start(void)
{
    lv_anim_delete(&S.bar_h, squeeze_cb);
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, &S.bar_h);
    lv_anim_set_exec_cb(&a, squeeze_cb);
    lv_anim_set_values(&a, BAR_H, 4);
    lv_anim_set_duration(&a, 380);
    lv_anim_set_playback_duration(&a, 520);
    lv_anim_set_repeat_delay(&a, 200);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
    lv_anim_start(&a);
}

static void squeeze_stop(void)
{
    lv_anim_delete(&S.bar_h, squeeze_cb);
    if (S.bar_h != BAR_H) apply_bar_height(BAR_H);
}

/* ---------- текст пилюли статуса ---------- */

static void update_state_label(void)
{
    if (S.state == ST_WAIT && S.wait_minutes > 0)
<<<<<<< HEAD
        lv_label_set_text_fmt(lbl_state, tr(TR_WAIT_MIN), state_text(ST_WAIT), S.wait_minutes);
    else
        lv_label_set_text(lbl_state, state_text(S.state));
=======
        lv_label_set_text_fmt(lbl_state, "%s · %d мин", STATE_TEXT[ST_WAIT], S.wait_minutes);
    else
        lv_label_set_text(lbl_state, STATE_TEXT[S.state]);
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
}

/* ---------- напоминание при долгом ожидании ---------- */

static void escalate_stop(void)
{
    S.wait_minutes = 0;
    pulse_stop(frame, LV_OPA_TRANSP);
    lv_obj_add_flag(frame, LV_OBJ_FLAG_HIDDEN);
}

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    if (ui_status_is_active(S.state)) {
        uint32_t s = lv_tick_elaps(S.start_tick) / 1000;
        lv_label_set_text_fmt(lbl_time, "%02u:%02u", (unsigned)(s / 60), (unsigned)(s % 60));
    }
    if (S.state == ST_WAIT) {
        uint32_t waited = lv_tick_elaps(S.wait_since);
        if (waited >= UI_WAIT_ESCALATE_MS) {
            int minutes = (int)(waited / 60000);
            if (S.wait_minutes == 0) {          /* первый раз — включаем настойчивый режим */
                lv_obj_remove_flag(frame, LV_OBJ_FLAG_HIDDEN);
                pulse_start(frame, 420, LV_OPA_TRANSP);
                pulse_start(dot, 220, LV_OPA_20);
                if (S.active >= 0) pulse_start(seg_fill[S.active], 220, LV_OPA_20);
            }
            if (minutes != S.wait_minutes) {
                S.wait_minutes = minutes;
                update_state_label();
                ui_sound_play(SND_WAIT);            /* каждую минуту ожидания — напоминание */
            }
        }
    }
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
        lv_obj_set_pos(seg_bg[i], M + i * (S.seg_w + GAP), BAR_Y + (BAR_H - S.bar_h) / 2);
        lv_obj_set_size(seg_bg[i], S.seg_w, S.bar_h);
        fill_w[i] = old_w ? fill_w[i] * S.seg_w / old_w : 0;
        lv_obj_set_size(seg_fill[i], fill_w[i], S.bar_h);
    }
}

/* ---------- тема ---------- */

static void apply_theme_static(void)
{
    const theme_def_t *t = T();
    lv_obj_set_style_text_color(lbl_title, hex(t->text), 0);
    lv_obj_set_style_text_color(lbl_count, hex(t->text), 0);
    lv_obj_set_style_text_color(lbl_time, hex(t->gray), 0);
    lv_obj_set_style_text_color(lbl_count_sub, hex(t->gray), 0);
    lv_obj_set_style_bg_color(badge_sub, hex(t->empty), 0);
    lv_obj_set_style_text_color(lbl_sub_n, hex(t->text), 0);
    lv_obj_set_style_bg_color(badge_others, hex(t->empty), 0);
    lv_obj_set_style_text_color(lbl_others, hex(t->gray), 0);
    for (int i = 0; i < MAX_SEG; i++)
        if (i != S.active) lv_obj_set_style_bg_color(seg_bg[i], hex(t->empty), 0);
}

void ui_status_set_theme(const char *agent)
{
    ui_theme_t th = (agent && !strcmp(agent, "codex")) ? THEME_CODEX : THEME_CLAUDE;
    if (th == S.theme) return;
    S.theme = th;
    apply_theme_static();
    accent_to(hex(T()->state[S.state]));
}

void ui_status_set_idle_scene(const char *scene)
{
    if (!scene) return;
    strncpy(S.idle_scene, scene, sizeof S.idle_scene - 1);
    S.idle_scene[sizeof S.idle_scene - 1] = '\0';
}

/* ---------- бейджи ---------- */

<<<<<<< HEAD
static int last_sub, last_others;

void ui_status_set_counters(int subagents, int other_sessions)
{
    last_sub = subagents;
    last_others = other_sessions;
=======
static const char *sessions_word(int n)
{
    int a = n % 100, b = n % 10;
    if (a >= 11 && a <= 14) return "сессий";
    if (b == 1) return "сессия";
    if (b >= 2 && b <= 4) return "сессии";
    return "сессий";
}

void ui_status_set_counters(int subagents, int other_sessions)
{
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    if (subagents > 0) {
        lv_label_set_text_fmt(lbl_sub_n, "×%d", subagents);
        lv_obj_remove_flag(badge_sub, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(badge_sub, LV_OBJ_FLAG_HIDDEN);
    }
    if (other_sessions > 0) {
<<<<<<< HEAD
        char buf[32];
        tr_sessions(buf, sizeof buf, other_sessions);
        lv_label_set_text(lbl_others, buf);
=======
        lv_label_set_text_fmt(lbl_others, "+%d %s", other_sessions, sessions_word(other_sessions));
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        lv_obj_remove_flag(badge_others, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(badge_others, LV_OBJ_FLAG_HIDDEN);
    }
}

/* ---------- связь ---------- */

void ui_status_link(bool online, uint32_t now_ms)
{
    (void)now_ms;
    if (online == S.link_ok) return;
    S.link_ok = online;
    if (online) {
        lv_obj_add_flag(link_banner, LV_OBJ_FLAG_HIDDEN);
        lv_obj_remove_flag(lbl_time, LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_style_opa(root, LV_OPA_COVER, 0);
    } else {
        lv_obj_remove_flag(link_banner, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lbl_time, LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_style_opa(root, LV_OPA_40, 0);  /* старый статус не выдаём за текущий */
    }
}

/* ---------- решение кнопкой ---------- */

void ui_status_set_approve(bool on)
{
    on = on && S.state == ST_WAIT;
    if (on == approve_on) return;
    approve_on = on;
    if (on) {
        lv_obj_remove_flag(approve_box, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lbl_count, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lbl_count_sub, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lbl_pct, LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_style_bg_color(approve_box, hex(T()->empty), 0);
        lv_obj_set_style_bg_color(approve_fill, hex(T()->state[ST_WAIT]), 0);
        lv_obj_set_width(approve_fill, 0);
    } else {
        lv_obj_add_flag(approve_box, LV_OBJ_FLAG_HIDDEN);
        lv_obj_remove_flag(lbl_count, LV_OBJ_FLAG_HIDDEN);
        lv_obj_remove_flag(lbl_count_sub, LV_OBJ_FLAG_HIDDEN);
        lv_obj_remove_flag(lbl_pct, LV_OBJ_FLAG_HIDDEN);
    }
}

bool ui_status_approve_pending(void) { return approve_on; }

void ui_status_approve_hold(float p)
{
    if (!approve_on) return;
    if (p < 0) p = 0;
    if (p > 1) p = 1;
    int32_t w = (int32_t)((SCR_W - 2 * M) * p);
    lv_obj_set_width(approve_fill, w);       /* тёмная копия текста внутри полосы обрезается по её ширине */
}

/* ---------- для диспетчера экранов ---------- */

lv_obj_t *ui_status_root(void) { return root; }

const lv_font_t *ui_status_font(int which)
{
    return which == 2 ? f_big : which == 1 ? f_title : f_small;
}

lv_color_t ui_status_state_color(status_state_t s) { return hex(T()->state[s]); }

lv_color_t ui_status_text_color(int which)
{
    return hex(which == 2 ? T()->empty : which == 1 ? T()->gray : T()->text);
}

void ui_status_set_right_inset(int32_t px)
{
    lv_obj_align(lbl_time, LV_ALIGN_TOP_RIGHT, -M - px, 22);
}

/* «Готово»: пилюля статуса коротко подпрыгивает.
 * Сдвиг, а не масштаб: масштаб уводит объект в отдельный слой, и скругление теряется. */
static void pop_cb(void *obj, int32_t v)
{
    lv_obj_set_style_translate_y(obj, -v, 0);
}

static void pop(lv_obj_t *o)
{
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, o);
    lv_anim_set_exec_cb(&a, pop_cb);
    lv_anim_set_values(&a, 0, 9);
    lv_anim_set_duration(&a, 150);
    lv_anim_set_playback_duration(&a, 420);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
}

/* Длинный заголовок: стоит 2 с с начала, плавно доезжает до конца, стоит, возвращается */
static void title_x_cb(void *obj, int32_t v) { lv_obj_set_style_translate_x(obj, v, 0); }

static void title_marquee(void)
{
    lv_anim_delete(lbl_title, title_x_cb);
    lv_obj_set_style_translate_x(lbl_title, 0, 0);
    int32_t over = (int32_t)text_w(f_title, lv_label_get_text(lbl_title)) - (SCR_W - 2 * M);
    if (over <= 0) return;
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, lbl_title);
    lv_anim_set_exec_cb(&a, title_x_cb);
    lv_anim_set_values(&a, 0, -over);
    uint32_t ms = (uint32_t)over * 1000 / 45;          /* 45 px/с */
    if (ms < 600) ms = 600;
    lv_anim_set_duration(&a, ms);
    lv_anim_set_delay(&a, 2000);
    lv_anim_set_playback_duration(&a, ms);
    lv_anim_set_playback_delay(&a, 1500);
    lv_anim_set_repeat_delay(&a, 2500);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
    lv_anim_start(&a);
}

<<<<<<< HEAD
/* Подсказка кнопки: светлая надпись и её тёмная копия на полосе — в одних координатах */
static void set_approve_text(void)
{
    lv_label_set_text(approve_lbl, tr(TR_APPROVE_HINT));
    lv_label_set_text(approve_lbl_inv, tr(TR_APPROVE_HINT));
    lv_obj_center(approve_lbl);
    lv_obj_update_layout(approve_lbl);
    lv_obj_set_pos(approve_lbl_inv, lv_obj_get_x(approve_lbl), lv_obj_get_y(approve_lbl));
}

=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
/* ---------- создание ---------- */

void ui_status_create(void)
{
    f_small = lv_tiny_ttf_create_data(ttf_reg_start,  ttf_reg_end  - ttf_reg_start,  18);
    f_title = lv_tiny_ttf_create_data(ttf_bold_start, ttf_bold_end - ttf_bold_start, 27);
    f_big   = lv_tiny_ttf_create_data(ttf_bold_start, ttf_bold_end - ttf_bold_start, 40);

    S.theme = THEME_CLAUDE;
    strcpy(S.idle_scene, "robot");
    S.bar_h = BAR_H;
    S.link_ok = true;
    const theme_def_t *t = T();

    lv_obj_t *scr = lv_screen_active();
    lv_obj_set_style_bg_color(scr, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    root = lv_obj_create(scr);
    lv_obj_remove_style_all(root);
    lv_obj_set_size(root, SCR_W, SCR_H);
    lv_obj_remove_flag(root, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);

    /* Верхняя строка: пилюля статуса + бейджи субагентов и сессий */
    topbar = mk_row(root, 8);
    lv_obj_set_pos(topbar, M, 16);

    pill = mk_box(topbar, 0x222222, LV_RADIUS_CIRCLE);
    lv_obj_set_size(pill, LV_SIZE_CONTENT, 32);
    lv_obj_set_style_pad_left(pill, 14, 0);
    lv_obj_set_style_pad_right(pill, 16, 0);
    lv_obj_set_style_pad_column(pill, 10, 0);
    lv_obj_set_flex_flow(pill, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(pill, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    dot = mk_box(pill, t->gray, LV_RADIUS_CIRCLE);
    lv_obj_set_size(dot, 12, 12);
    lbl_state = mk_label(pill, f_small, t->gray);

    badge_sub = mk_badge(topbar);
    lv_obj_t *icon = lv_obj_create(badge_sub);         /* два квадратика — «копии» агента */
    lv_obj_remove_style_all(icon);
    lv_obj_set_size(icon, 16, 14);
    lv_obj_t *sq1 = mk_box(icon, t->gray, 2);
    lv_obj_set_size(sq1, 10, 10);
    lv_obj_set_pos(sq1, 0, 0);
    lv_obj_t *sq2 = mk_box(icon, t->text, 2);
    lv_obj_set_size(sq2, 10, 10);
    lv_obj_set_pos(sq2, 6, 4);
    lbl_sub_n = mk_label(badge_sub, f_small, t->text);
    lv_obj_add_flag(badge_sub, LV_OBJ_FLAG_HIDDEN);

    badge_others = mk_badge(topbar);
    lbl_others = mk_label(badge_others, f_small, t->gray);
    lv_obj_add_flag(badge_others, LV_OBJ_FLAG_HIDDEN);

    lbl_time = mk_label(root, f_small, t->gray);
    lv_label_set_text(lbl_time, "00:00");
    lv_obj_align(lbl_time, LV_ALIGN_TOP_RIGHT, -M, 22);

    title_box = lv_obj_create(root);                 /* окно, в котором длинный заголовок ездит */
    lv_obj_remove_style_all(title_box);
    lv_obj_set_size(title_box, SCR_W - 2 * M, 36);
    lv_obj_set_pos(title_box, M, 62);
    lv_obj_remove_flag(title_box, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    lbl_title = mk_label(title_box, f_title, t->text);
    lv_label_set_long_mode(lbl_title, LV_LABEL_LONG_CLIP);

    lbl_step = mk_label(root, f_small, t->gray);
    lv_obj_set_width(lbl_step, SCR_W - 2 * M);
    lv_label_set_long_mode(lbl_step, LV_LABEL_LONG_DOT);
    lv_obj_set_pos(lbl_step, M, 106);

    for (int i = 0; i < MAX_SEG; i++) {
        seg_bg[i] = mk_box(root, t->empty, BAR_H / 2);
        lv_obj_set_style_clip_corner(seg_bg[i], true, 0);
        seg_fill[i] = mk_box(seg_bg[i], t->gray, 0);
        lv_obj_set_user_data(seg_fill[i], (void *)(intptr_t)i);
        lv_obj_set_size(seg_fill[i], 0, BAR_H);
        fill_w[i] = 0;
    }

    lbl_count = mk_label(root, f_big, t->text);
    lv_obj_set_pos(lbl_count, M, 178);
    lbl_count_sub = mk_label(root, f_small, t->gray);
<<<<<<< HEAD
    lv_label_set_text(lbl_count_sub, tr(TR_TASKS_DONE));
=======
    lv_label_set_text(lbl_count_sub, "задач готово");
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    lbl_pct = mk_label(root, f_big, t->gray);
    lv_label_set_text(lbl_pct, "0%");
    lv_obj_align(lbl_pct, LV_ALIGN_TOP_RIGHT, -M, 178);

    /* Рамка по краю экрана — только для долгого ожидания */
    frame = lv_obj_create(scr);
    lv_obj_remove_style_all(frame);
    lv_obj_set_size(frame, SCR_W, SCR_H);
    lv_obj_set_style_border_width(frame, 3, 0);
    lv_obj_set_style_border_opa(frame, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(frame, 10, 0);
    lv_obj_remove_flag(frame, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_flag(frame, LV_OBJ_FLAG_HIDDEN);

    /* Плашка «Нет связи» — по центру поверх затемнённого экрана */
    link_banner = mk_badge(scr);
    lv_obj_set_style_bg_color(link_banner, hex(0x3A1012), 0);
    lv_obj_set_style_border_width(link_banner, 1, 0);
    lv_obj_set_style_border_color(link_banner, hex(0x7A2420), 0);
    lv_obj_set_height(link_banner, 48);
    lv_obj_set_style_pad_hor(link_banner, 22, 0);
    lv_obj_t *ldot = mk_box(link_banner, 0xFF453A, LV_RADIUS_CIRCLE);
    lv_obj_set_size(ldot, 12, 12);
<<<<<<< HEAD
    link_txt = mk_label(link_banner, f_small, 0xFF8A80);
    lv_label_set_text(link_txt, tr(TR_LINK_LOST));
=======
    lv_obj_t *ltxt = mk_label(link_banner, f_small, 0xFF8A80);
    lv_label_set_text(ltxt, "Нет связи с компьютером");
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    lv_obj_align(link_banner, LV_ALIGN_CENTER, 0, 0);     /* по центру, поверх затемнённого экрана */
    lv_obj_add_flag(link_banner, LV_OBJ_FLAG_HIDDEN);

    /* Подсказка «удерживайте — разрешить» на месте счётчиков; полоса растёт, пока держат кнопку */
    approve_box = mk_box(root, t->empty, 14);
    lv_obj_set_size(approve_box, SCR_W - 2 * M, 42);
    lv_obj_set_pos(approve_box, M, 180);
    lv_obj_set_style_clip_corner(approve_box, true, 0);
    approve_fill = mk_box(approve_box, t->state[ST_WAIT], 0);
    lv_obj_set_size(approve_fill, 0, 42);
    approve_lbl = mk_label(approve_box, f_small, t->text);
<<<<<<< HEAD
    approve_lbl_inv = mk_label(approve_fill, f_small, 0x000000);   /* та же надпись, тёмная, на полосе */
    set_approve_text();
=======
    lv_label_set_text(approve_lbl, "Удержать — разрешить · нажать — отклонить");
    lv_obj_center(approve_lbl);
    lv_obj_update_layout(approve_lbl);
    approve_lbl_inv = mk_label(approve_fill, f_small, 0x000000);   /* та же надпись, тёмная, на полосе */
    lv_label_set_text(approve_lbl_inv, lv_label_get_text(approve_lbl));
    lv_obj_set_pos(approve_lbl_inv, lv_obj_get_x(approve_lbl), lv_obj_get_y(approve_lbl));
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    lv_obj_move_foreground(approve_fill);    /* полоса с тёмным текстом — поверх белого */
    lv_obj_add_flag(approve_box, LV_OBJ_FLAG_HIDDEN);

    S.state  = ST_IDLE;
    S.color  = hex(t->state[ST_IDLE]);
    S.active = -1;
    S.total  = 0;
    S.seg_w  = 0;

    apply_theme_static();
    lv_timer_create(tick_cb, 250, NULL);

<<<<<<< HEAD
    ui_status_apply(ST_IDLE, tr(TR_IDLE_TITLE), tr(TR_IDLE_STEP), 0, 1);
=======
    ui_status_apply(ST_IDLE, "Жду задачу", "Отправьте задачу агенту", 0, 1);
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    update_state_label();
}

/* ---------- обновление ---------- */

void ui_status_park(void)
{
    if (S.state == ST_IDLE) return;
    if (S.active >= 0) {
        pulse_stop(seg_fill[S.active], LV_OPA_COVER);
        S.active = -1;
    }
    pulse_stop(dot, LV_OPA_COVER);
    if (S.wait_minutes) escalate_stop();
    squeeze_stop();
    ui_status_set_approve(false);
    S.state = ST_IDLE;
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
<<<<<<< HEAD
    if (st != ST_IDLE) S.had_task = true;
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    status_state_t prev = S.state;

    /* Секундомер стартует с новой задачей */
    if (ui_status_is_active(st) && !ui_status_is_active(prev)) {
        S.start_tick = lv_tick_get();
        lv_label_set_text(lbl_time, "00:00");
    }

    /* Тексты */
    if (title && strcmp(title, lv_label_get_text(lbl_title))) {
        lv_label_set_text(lbl_title, title);
        title_marquee();
    }
    if (step && strcmp(step, lv_label_get_text(lbl_step))) {
        lv_label_set_text(lbl_step, step);
        fade_in(lbl_step, 300);
    }

    if (total != S.total) {
        layout_segments(total);
        S.total = total;
    }

    /* Активный сегмент: тот, что сейчас в работе */
    int old_active = S.active;
    S.active = (ui_status_is_active(st) && done < total) ? done : -1;
    if (old_active >= 0 && old_active != S.active) {
        lv_obj_set_style_bg_color(seg_bg[old_active], hex(T()->empty), 0);
        pulse_stop(seg_fill[old_active], LV_OPA_COVER);
    }

    /* Ждёт вас: заводим таймер напоминания; вышли из ожидания — снимаем */
    if (st == ST_WAIT && prev != ST_WAIT) S.wait_since = lv_tick_get();
    if (st != ST_WAIT && S.wait_minutes) escalate_stop();

    S.state = st;
    if (st != ST_WAIT) ui_status_set_approve(false);
    if (st != prev) {
        update_state_label();
        accent_to(hex(T()->state[st]));
        if (st == ST_ERROR) shake(pill);
        if (st == ST_DONE) pop(topbar);   /* вся строка: сама пилюля обрезалась бы по краю строки */
    } else {
        apply_accent(S.color);
    }

    /* Заливка сегментов; при завершении — «волной» слева направо */
    for (int i = 0; i < total; i++) {
        int32_t target = (i < done) ? S.seg_w
                       : (i == S.active ? S.seg_w * 2 / 5 : 0);
        uint32_t delay = (st == ST_DONE && i >= prev_done) ? (uint32_t)(i - prev_done) * 70 : 0;
        anim_width(i, target, delay);
    }

    /* Пульсация: точка и активный сегмент «дышат», пока идёт работа */
    if (ui_status_is_active(st) && st != ST_ERROR) {
        uint32_t period = (st == ST_WAIT) ? 450 : 900;
        if (!(st == ST_WAIT && S.wait_minutes)) {
            pulse_start(dot, period, LV_OPA_30);
            if (S.active >= 0) pulse_start(seg_fill[S.active], period, LV_OPA_30);
        }
    } else {
        pulse_stop(dot, LV_OPA_COVER);
        if (S.active >= 0) pulse_stop(seg_fill[S.active], LV_OPA_COVER);
    }

    if (st == ST_COMPACT) squeeze_start();
    else squeeze_stop();

    /* Счётчики */
    S.done = done;
    lv_label_set_text_fmt(lbl_count, "%d/%d", done, total);
    lv_obj_align_to(lbl_count_sub, lbl_count, LV_ALIGN_OUT_RIGHT_BOTTOM, 12, -8);
    anim_pct(done * 100 / total);
}

void ui_status_set_language(const char *code)
{
    if (!ui_i18n_set_code(code)) return;
    update_state_label();
    lv_label_set_text(lbl_count_sub, tr(TR_TASKS_DONE));
    lv_obj_align_to(lbl_count_sub, lbl_count, LV_ALIGN_OUT_RIGHT_BOTTOM, 12, -8);
    lv_label_set_text(link_txt, tr(TR_LINK_LOST));
    set_approve_text();
    ui_status_set_counters(last_sub, last_others);
    if (!S.had_task) {                       /* задач ещё не было — подпись ожидания на новом языке */
        lv_label_set_text(lbl_title, tr(TR_IDLE_TITLE));
        lv_label_set_text(lbl_step, tr(TR_IDLE_STEP));
        title_marquee();
    }
}
