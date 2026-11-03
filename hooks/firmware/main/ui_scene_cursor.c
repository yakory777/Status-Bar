/*
 * Сцена «живой курсор» (обе темы): курсор терминала просыпается, открывает глаза
 * и печатает «Ready to work», перепрыгивая на следующее знакоместо и оставляя букву.
 * В конце мигает «без тела» — глаза висят в воздухе — и растворяется в цвете темы.
 * Эталон: tools/render_idle_cursor.py.
 */
#include <math.h>
#include <string.h>
#include "ui_scene_priv.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define SW 5
#define SH 12
#define ZOOM_LEN 0.9f
#define HOLD 0.12f
#define FADE 0.5f
#define PROMPT_IN0 0.15f
#define PROMPT_IN1 0.45f
#define APPEAR 0.45f
#define WAKE 1.75f
#define START 2.2f

static const char *const TEXT = "Ready to work";
#define TEXT_LEN 13

typedef struct { uint32_t accent, flash, eye, text; const char *font; } theme_cfg_t;
static const theme_cfg_t CFG[THEME_COUNT] = {
    [THEME_CLAUDE] = { 0xD97757, 0xFFC4A0, 0x26140E, 0xFAF9F5, "lora" },
    [THEME_CODEX]  = { 0x10A37F, 0x78E6C4, 0x0A0C0E, 0xECECF1, "mono" },
};

typedef struct { float ts, cr, air; int a, b; float h; int letter; } hop_t;

static const theme_cfg_t *C;
static ui_theme_t TH;
static lv_font_t *f_word;
static float lead, cur_w, cap, tx, text_x, cur_h, foot;
static const float BASE = 140;
static hop_t HOPS[16];
static int NH;
static float TYPED_AT[TEXT_LEN];
static float DONE_T, LOOK_BACK, JOY, GAG, ZOOM, END_T;
static const float JOY_LEN = 0.4f;
static lv_color_t body_col;

static float slot_x(int i)
{
    return text_x + text_w_n(f_word, TEXT, (uint32_t)i) + cur_w / 2 + 2;
}

static void begin(ui_theme_t theme)
{
    TH = theme;
    C = &CFG[theme];
    float line_w = 0;
    for (int size = 50;; size -= 2) {                /* крупнейший шрифт, при котором строка влезает */
        f_word = scene_font(C->font, size);
        lead = text_w(f_word, "> ");
        float tw = text_w(f_word, TEXT);
        cur_w = text_w(f_word, "n") * 0.62f;
        line_w = lead + tw + cur_w + 4;
        if (line_w <= UI_W - 80 || size <= 30) break;
        lv_tiny_ttf_destroy(f_word);
    }
    cap = cap_height(f_word);
    tx = (UI_W - line_w) / 2;
    text_x = tx + lead;
    cur_h = cap + 6;
    foot = BASE + 6;
    body_col = c_hex(theme == THEME_CLAUDE ? C->accent : C->text);

    NH = 0;
    memset(TYPED_AT, 0, sizeof TYPED_AT);
    float t = START;
    for (int i = 0; i < TEXT_LEN; i++) {
        if (TEXT[i] == ' ') continue;
        bool space_next = i + 1 < TEXT_LEN && TEXT[i + 1] == ' ';
        int j = space_next ? i + 2 : i + 1;
        if (j > TEXT_LEN) j = TEXT_LEN;
        float cr = space_next ? 0.08f : 0.06f, air = space_next ? 0.30f : 0.16f, h = space_next ? 26 : 10;
        HOPS[NH++] = (hop_t){ t, cr, air, i, j, h, i };
        TYPED_AT[i] = t + cr;                         /* буква появляется в момент отрыва */
        t += cr + air + (space_next ? 0.10f : 0.04f);
    }
    DONE_T = t;
    LOOK_BACK = t + 0.5f;
    JOY = t + 1.5f;
    HOPS[NH++] = (hop_t){ JOY, 0.1f, JOY_LEN, TEXT_LEN, TEXT_LEN, 22, -1 };
    GAG = JOY + 0.1f + JOY_LEN + 0.45f;
    ZOOM = GAG + 1.3f;
    END_T = ZOOM + ZOOM_LEN + HOLD + FADE;
}

static void end(void)
{
    if (f_word) lv_tiny_ttf_destroy(f_word);
    f_word = NULL;
}

static float length(void) { return END_T; }
static float rest_time(void) { return DONE_T + 0.3f; }

typedef struct { bool vis; float x, y, sx, sy; int look; int eyes; bool happy, body; } pose_t;
/* eyes: -1 — глаз нет (обычный курсор), 0 — закрыты, 1 — открыты */

static pose_t cursor(float t)
{
    pose_t p = { 0 };
    if (t < APPEAR) return p;
    p.vis = true;
    p.x = slot_x(0); p.y = foot; p.sx = p.sy = 1; p.body = true;
    if (t < WAKE) {                                   /* обычный мигающий курсор */
        p.eyes = -1;
        p.body = ((int)((t - APPEAR) * 2)) % 2 == 0;
        return p;
    }
    if (t < START) {                                  /* просыпается */
        float dt = t - WAKE;
        float s = springf(dt, 3.0f, 5.0f) * 0.18f;
        p.sx = 1 - s * 0.7f; p.sy = 1 + s;
        p.look = dt > 0.2f ? 1 : 0;
        p.eyes = (dt >= 0.25f && dt < 0.33f) ? 0 : 1;
        return p;
    }
    float last = START;
    int slot = 0;
    for (int i = 0; i < NH; i++) {
        const hop_t *h = &HOPS[i];
        if (t < h->ts) break;
        if (t < h->ts + h->cr) {
            float k = sinf((t - h->ts) / h->cr * (float)M_PI / 2);
            p.x = slot_x(h->a); p.sx = 1 + 0.18f * k; p.sy = 1 - 0.22f * k; p.look = 1; p.eyes = 1;
            return p;
        }
        if (t < h->ts + h->cr + h->air) {
            float q = (t - h->ts - h->cr) / h->air;
            float st = 1 + 0.2f * fabsf(1 - 2 * q);
            p.x = lerpf(slot_x(h->a), slot_x(h->b), q);
            p.y = foot - h->h * 4 * q * (1 - q);
            p.sx = 1 / sqrtf(st); p.sy = st; p.look = h->b > h->a ? 1 : 0; p.eyes = 1;
            return p;
        }
        last = h->ts + h->cr + h->air;
        slot = h->b;
    }
    float dt = t - last;
    float s = springf(dt, 3.4f, 6.0f) * 0.22f;
    p.sy = 1 - s; p.sx = 1 + s * 0.8f;
    p.look = 1; p.eyes = 1;
    if (t >= DONE_T) {
        p.happy = dt < 0.35f || (t >= JOY && dt < 0.5f);
        if (t >= LOOK_BACK && t < JOY) p.look = -1;
        if (t >= GAG) {                               /* тело гаснет, глаза висят в воздухе */
            float gt = t - GAG;
            p.body = !((gt >= 0.15f && gt < 0.45f) || (gt >= 0.75f && gt < 1.05f));
            p.look = gt < 0.6f ? 0 : 1;
        }
        p.sy *= 1 + sinf((t - DONE_T) * 2 * (float)M_PI / 1.8f) * 0.035f;
    }
    p.x = slot_x(slot);
    return p;
}

static void build_sprite(uint8_t *g, const pose_t *p, lv_color_t *pal, float melt)
{
    for (int i = 0; i < SW * SH; i++) g[i] = p->body ? 1 : 0;
    if (p->eyes >= 0) {
        for (int k = 0; k < 2; k++) {
            int x = (k ? 3 : 1) + p->look;
            if (x < 0) x = 0;
            if (x > SW - 1) x = SW - 1;
            g[4 * SW + x] = 2;
            if (!p->happy && p->eyes == 1) g[3 * SW + x] = 2;
        }
    }
    lv_color_t accent = c_hex(C->accent);
    pal[1] = body_col;
    pal[2] = c_hex(p->body ? C->eye : C->text);
    if (melt > 0) {
        pal[1] = c_mix(pal[1], accent, melt);
        pal[2] = c_mix(pal[2], accent, melt);
    }
}

static void draw(dctx_t *d, const scene_frame_t *f)
{
    float t = f->t;
    lv_color_t accent = c_hex(C->accent), text = c_hex(C->text), flash = c_hex(C->flash);

    if (t >= ZOOM + ZOOM_LEN) {
        float p = clamp01((t - ZOOM - ZOOM_LEN - HOLD) / FADE);
        scene_cover = 1 - p;
        d_fill(d, c_dim(accent, powf(1 - p, 1.5f)));
        return;
    }
    float zp = t >= ZOOM ? clamp01((t - ZOOM) / ZOOM_LEN) : 0.0f;
    scene_cover = clamp01((zp - 0.55f) / 0.45f);
    float gone = clamp01(zp * 2.5f);
    float fade = clamp01((t - PROMPT_IN0) / (PROMPT_IN1 - PROMPT_IN0)) * (1 - gone);
    float text_k = 1 - clamp01(f->exit_p * 2.5f);

    d_text(d, f_word, ">", tx, BASE, c_dim(accent, fade * text_k), LV_OPA_COVER);

    for (int i = 0; i < TEXT_LEN; i++) {
        if (TEXT[i] == ' ' || TYPED_AT[i] == 0 || t < TYPED_AT[i]) continue;
        float dt = t - TYPED_AT[i];
        int word = 0;
        for (int k = 0; k < i; k++) word += TEXT[k] == ' ';
        lv_color_t col = c_mix(word == 2 ? accent : text, flash, (1 - clamp01(dt / 0.35f)) * 0.85f);
        col = c_dim(col, (1 - gone) * text_k);
        char ch[2] = { TEXT[i], 0 };
        float sy = lerpf(0.25f, 1.0f, ease_out_q(clamp01(dt / 0.14f)));
        d_text_squash(d, f_word, ch, text_x + text_w_n(f_word, TEXT, (uint32_t)i), BASE, col, sy);
    }

    pose_t c = cursor(t);
    if (!c.vis) return;
    if (f->asleep) {
        c.eyes = 0; c.happy = false; c.body = true; c.look = 0;
        c.sx = 1; c.sy = 1 + sinf(f->sleep_t * 2 * (float)M_PI / 3.6f) * 0.035f;
    }
    float melt = 0;
    if (zp > 0) {
        c.look = 0; c.body = true; c.eyes = 1;
        if (zp < 0.18f) {
            float k = sinf(zp / 0.18f * (float)M_PI / 2);
            c.sx = 1 + 0.25f * k; c.sy = 1 - 0.3f * k; c.happy = true;
        } else {
            float q = (zp - 0.18f) / 0.82f;
            float g = 1 + 16 * powf(q, 2.2f);
            c.sx = g * 1.35f; c.sy = g; c.happy = false;
            c.x = lerpf(c.x, UI_W / 2.0f, ease_out_q(q));
            c.y = lerpf(c.y - cur_h / 2, UI_H / 2.0f, ease_out_q(q)) + cur_h * c.sy / 2;
        }
        melt = clamp01((zp - 0.45f) / 0.35f);
    }
    scene_exit_pose(f->exit_p, &c.y, &c.sx, &c.sy);

    uint8_t grid[SW * SH];
    lv_color_t pal[3];
    build_sprite(grid, &c, pal, melt);
    float bw = cur_w * c.sx, bh = cur_h * c.sy;
    lv_opa_t opa = (zp == 0 && fade < 1) ? (lv_opa_t)(255 * fade) : LV_OPA_COVER;
    d_sprite(d, grid, SW, SH, pal, c.x - bw / 2, c.y - bh, bw, bh, opa);

    if (zp > 0.8f) {
        float q = ease_in((zp - 0.8f) / 0.2f);
        float r = q * hypotf(UI_W, UI_H) * 0.62f;
        d_circle(d, c.x, c.y - bh / 2, r, accent, LV_OPA_COVER);
    }
    if (f->asleep) scene_draw_zzz(d, c.x + bw / 2, c.y - bh, f->sleep_t, text);
}

const scene_def_t SCENE_CURSOR = { "cursor", begin, end, length, rest_time, draw };
