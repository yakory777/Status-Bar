/*
 * Менеджер сцен ожидания: один полноэкранный объект, который каждый кадр
 * перерисовывает текущая сцена (ui_scene_robot.c, ui_scene_cursor.c, ui_scene_typist.c).
 */
#include <math.h>
#include <string.h>
#include "ui_scene.h"
#include "ui_scene_priv.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define EXIT_MS 520

extern const uint8_t ttf_lora_start[] asm("_binary_Lora_Bold_ttf_start");
extern const uint8_t ttf_lora_end[]   asm("_binary_Lora_Bold_ttf_end");
extern const uint8_t ttf_mono_start[] asm("_binary_DejaVuSansMono_Bold_ttf_start");
extern const uint8_t ttf_mono_end[]   asm("_binary_DejaVuSansMono_Bold_ttf_end");
extern const uint8_t ttf_sans_start[] asm("_binary_DejaVuSans_Bold_ttf_start");
extern const uint8_t ttf_sans_end[]   asm("_binary_DejaVuSans_Bold_ttf_end");

static lv_obj_t *obj;
static lv_timer_t *timer;
static const scene_def_t *cur;
static lv_font_t *f_zzz;

static enum { M_STOPPED, M_RUN, M_EXIT, M_SLEEP } mode = M_STOPPED;
static uint32_t t0;            /* начало цикла сцены */
static uint32_t mode_t0;       /* начало ухода / сна */
static float frozen_t;
static void (*exit_done)(void);
float scene_cover;

/* ---------- общее для сцен ---------- */

const void *scene_font_data(const char *which, size_t *size)
{
    if (!strcmp(which, "lora")) { *size = ttf_lora_end - ttf_lora_start; return ttf_lora_start; }
    if (!strcmp(which, "mono")) { *size = ttf_mono_end - ttf_mono_start; return ttf_mono_start; }
    *size = ttf_sans_end - ttf_sans_start;
    return ttf_sans_start;
}

lv_font_t *scene_font(const char *which, int px)
{
    size_t n;
    const void *data = scene_font_data(which, &n);
    return lv_tiny_ttf_create_data(data, n, px);
}

void scene_draw_zzz(dctx_t *d, float x, float y, float sleep_t, lv_color_t c)
{
    static const char *Z = "z";
    float appear = clamp01(sleep_t / 1.2f);
    for (int k = 0; k < 3; k++) {
        float ph = fmodf(sleep_t * 0.45f + k / 3.0f, 1.0f);
        float zx = x + 6 + ph * 20 + k * 3;
        float zy = y - ph * 40;
        float a = sinf(ph * (float)M_PI) * appear;
        d_text(d, f_zzz, Z, zx, zy, c_dim(c, a), LV_OPA_COVER);
    }
}

void scene_exit_pose(float p, float *y, float *sx, float *sy)
{
    if (p <= 0) return;
    if (p < 0.3f) {                              /* присед */
        float k = sinf(p / 0.3f * (float)M_PI / 2);
        *sx *= 1 + 0.2f * k;
        *sy *= 1 - 0.26f * k;
    } else {                                     /* прыжок вверх за кадр с вытягиванием */
        float q = (p - 0.3f) / 0.7f;
        *y -= ease_in(q) * (UI_H + 90);
        float st = 1 + 0.35f * (1 - q * 0.5f);
        *sx /= sqrtf(st);
        *sy *= st;
    }
}

/* ---------- менеджер ---------- */

static float elapsed_s(uint32_t since) { return lv_tick_elaps(since) / 1000.0f; }

static void draw_cb(lv_event_t *e)
{
    if (!cur || mode == M_STOPPED) return;
    dctx_t d = dctx_from_event(e);
    scene_frame_t f = { 0 };
    switch (mode) {
    case M_RUN:
        f.t = fmodf(elapsed_s(t0), cur->length());
        break;
    case M_EXIT:
        f.t = frozen_t;
        f.exit_p = clamp01(lv_tick_elaps(mode_t0) / (float)EXIT_MS);
        break;
    case M_SLEEP:
        f.t = cur->rest_time();
        f.asleep = true;
        f.sleep_t = elapsed_s(mode_t0);
        break;
    default:
        return;
    }
    cur->draw(&d, &f);
}

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    if (mode == M_STOPPED) return;
    if (mode == M_EXIT && lv_tick_elaps(mode_t0) >= EXIT_MS) {
        mode = M_STOPPED;
        lv_obj_add_flag(obj, LV_OBJ_FLAG_HIDDEN);
        void (*cb)(void) = exit_done;
        exit_done = NULL;
        if (cb) cb();
        return;
    }
    lv_obj_invalidate(obj);
}

void ui_scene_create(lv_obj_t *parent)
{
    f_zzz = scene_font("sans", 18);
    obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_set_size(obj, UI_W, UI_H);
    lv_obj_remove_flag(obj, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(obj, draw_cb, LV_EVENT_DRAW_MAIN, NULL);
    lv_obj_add_flag(obj, LV_OBJ_FLAG_HIDDEN);
    timer = lv_timer_create(tick_cb, 33, NULL);
}

static const scene_def_t *pick(ui_theme_t theme, const char *name)
{
    if (name && !strcmp(name, "robot") && theme == THEME_CLAUDE) return &SCENE_ROBOT;
    if (name && !strcmp(name, "typist") && theme == THEME_CODEX) return &SCENE_TYPIST;
    if (name && !strcmp(name, "cursor")) return &SCENE_CURSOR;
    return theme == THEME_CODEX ? &SCENE_CURSOR : &SCENE_ROBOT;   /* по умолчанию, как в host/scenes.py */
}

void ui_scene_start(ui_theme_t theme, const char *name)
{
    scene_cover = 0;
    const scene_def_t *next = pick(theme, name);
    if (cur) cur->end();
    cur = next;
    cur->begin(theme);
    t0 = lv_tick_get();
    mode = M_RUN;
    exit_done = NULL;
    lv_obj_remove_flag(obj, LV_OBJ_FLAG_HIDDEN);
    lv_obj_invalidate(obj);
}

void ui_scene_exit(void (*done)(void))
{
    if (mode == M_STOPPED) {
        if (done) done();
        return;
    }
    frozen_t = mode == M_SLEEP ? cur->rest_time() : fmodf(elapsed_s(t0), cur->length());
    mode = M_EXIT;
    mode_t0 = lv_tick_get();
    exit_done = done;
}

void ui_scene_set_sleep(bool asleep)
{
    if (!cur) return;
    if (asleep && mode == M_RUN) {
        mode = M_SLEEP;
        mode_t0 = lv_tick_get();
    } else if (!asleep && mode == M_SLEEP) {
        mode = M_RUN;                 /* просыпается в спокойной позе и продолжает цикл оттуда */
        t0 = lv_tick_get() - (uint32_t)(cur->rest_time() * 1000);
    }
}

void ui_scene_stop(void)
{
    scene_cover = 0;
    mode = M_STOPPED;
    lv_obj_add_flag(obj, LV_OBJ_FLAG_HIDDEN);
}

bool ui_scene_visible(void) { return mode != M_STOPPED; }
const char *ui_scene_name(void) { return cur ? cur->name : ""; }

float ui_scene_cover(void) { return ui_scene_visible() ? scene_cover : 0.0f; }
