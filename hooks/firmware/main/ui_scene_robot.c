/*
 * Сцена «робот» (тема Claude): пиксельный робот падает на надпись «Ready to work»,
 * скачет по буквам (каждая проседает и загорается), спрыгивает рядом, дышит,
 * моргает, прыгает в камеру и растворяется в оранжевом.
 * Эталон: tools/render_idle_robot.py — числа и кривые совпадают.
 */
#include <math.h>
#include <string.h>
#include "ui_scene_priv.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define PX 4
#define SW 12
#define SH 13
#define BODY_W (SW * PX)
#define BODY_H (SH * PX)
#define GROUND 150.0f
#define BASE 150.0f
#define GAP_BOT 26.0f

#define TEXT_IN0 0.2f
#define TEXT_IN1 0.8f
#define FALL0 0.8f
#define FALL1 1.25f
#define ZOOM_LEN 0.9f
#define HOLD 0.12f
#define FADE 0.5f

static const char *const SPRITE[SH] = {
    ".....LL.....",
    ".....DD.....",
    ".BBBBBBBBBB.",
    "BBBBBBBBBBBB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BBBBBBBBBBBB",
    "DBBBBBBBBBBD",
    ".DDDDDDDDDD.",
    ".FFF....FFF.",
};
enum { P_B = 1, P_D, P_S, P_F, P_L, P_E, P_COUNT };

#define ORANGE    0xD97757
#define ORANGE_DK 0xA04E34
#define SCREEN    0x26140E
#define EYE       0xFAECDE
#define LAMP_ON   0xFFD68C
#define LAMP_OFF  0x6E3C28
#define WHITE     0xFAF9F5
#define DIM       0x343230
#define GRAY      0x8E8E93

static const char *const TEXT = "Ready to work";

typedef struct { char ch[2]; float x, cx, top; int word; } letter_t;
typedef struct { float ts, cr, air, xa, ya, xb, yb, h; } hop_t;

static lv_font_t *f_word;
static letter_t L[16];
static int NL;
static hop_t HOPS[20];
static int NH;
static float LAND_ON[16];
static float LAND_T[24], LAND_X[24];
static int NLAND;
static float TX, REST_X, SETTLE, ZOOM, END_T;

typedef struct { bool vis; float x, y, sx, sy; int look; bool eyes, happy; } pose_t;

/* ---------- раскладка и таймлайн ---------- */

static void begin(ui_theme_t theme)
{
    (void)theme;
    f_word = scene_font("lora", 54);
    float tw = text_w(f_word, TEXT);
    TX = (UI_W - (tw + GAP_BOT + BODY_W)) / 2.0f;

    NL = 0;
    int word = 0;
    for (int i = 0; TEXT[i]; i++) {
        if (TEXT[i] == ' ') { word++; continue; }
        letter_t *l = &L[NL++];
        l->ch[0] = TEXT[i];
        l->ch[1] = 0;
        l->x = TX + text_w_n(f_word, TEXT, (uint32_t)i);
        float w = text_w_n(f_word, &TEXT[i], 1);
        l->cx = l->x + w / 2;
        lv_font_glyph_dsc_t g;
        lv_font_get_glyph_dsc(f_word, &g, (uint32_t)TEXT[i], 0);
        l->top = BASE - (float)(g.box_h + g.ofs_y);
        l->word = word;
    }
    REST_X = TX + tw + GAP_BOT + BODY_W / 2.0f;

    NH = 0;
    LAND_ON[0] = FALL1;
    float t = FALL1 + 0.22f;
    for (int i = 1; i < NL; i++) {
        bool gap = L[i].word != L[i - 1].word;
        float cr = gap ? 0.12f : 0.07f, air = gap ? 0.40f : 0.24f, h = gap ? 34 : 16;
        HOPS[NH++] = (hop_t){ t, cr, air, L[i - 1].cx, L[i - 1].top, L[i].cx, L[i].top, h };
        LAND_ON[i] = t + cr + air;
        t += cr + air + (gap ? 0.14f : 0.05f);
    }
    t += 0.25f;
    HOPS[NH++] = (hop_t){ t, 0.16f, 0.50f, L[NL - 1].cx, L[NL - 1].top, REST_X, GROUND, 30 };
    SETTLE = t + 0.16f + 0.55f;
    float idle_hop = SETTLE + 1.9f;
    HOPS[NH++] = (hop_t){ idle_hop, 0.12f, 0.38f, REST_X, GROUND, REST_X, GROUND, 22 };
    ZOOM = SETTLE + 3.6f;
    END_T = ZOOM + ZOOM_LEN + HOLD + FADE;

    NLAND = 0;
    LAND_T[NLAND] = FALL1;
    LAND_X[NLAND++] = L[0].cx;
    for (int i = 0; i < NH; i++) {
        LAND_T[NLAND] = HOPS[i].ts + HOPS[i].cr + HOPS[i].air;
        LAND_X[NLAND++] = HOPS[i].xb;
    }
}

static void end(void)
{
    if (f_word) lv_tiny_ttf_destroy(f_word);
    f_word = NULL;
}

static float length(void) { return END_T; }
static float rest_time(void) { return SETTLE + 0.8f; }

/* ---------- поза робота во времени t ---------- */

static pose_t character(float t)
{
    pose_t p = { 0 };
    if (t < FALL0) return p;
    p.vis = true;
    p.eyes = true;
    float x0 = L[0].cx, y0 = L[0].top;
    if (t < FALL1) {
        float q = ease_in((t - FALL0) / (FALL1 - FALL0));
        float st = 1 + 0.35f * q;
        p.x = x0; p.y = lerpf(-BODY_H - 10, y0, q);
        p.sx = 1 / sqrtf(st); p.sy = st;
        return p;
    }
    float x = x0, y = y0, last = FALL1;
    for (int i = 0; i < NH; i++) {
        const hop_t *h = &HOPS[i];
        if (t < h->ts) break;
        int dir = h->xb > h->xa ? 1 : 0;
        if (t < h->ts + h->cr) {
            float k = sinf((t - h->ts) / h->cr * (float)M_PI / 2);
            p.x = h->xa; p.y = h->ya; p.sx = 1 + 0.2f * k; p.sy = 1 - 0.26f * k; p.look = dir;
            return p;
        }
        if (t < h->ts + h->cr + h->air) {
            float q = (t - h->ts - h->cr) / h->air;
            float st = 1 + 0.2f * fabsf(1 - 2 * q);
            p.x = lerpf(h->xa, h->xb, q);
            p.y = lerpf(h->ya, h->yb, q) - h->h * 4 * q * (1 - q);
            p.sx = 1 / sqrtf(st); p.sy = st; p.look = dir;
            return p;
        }
        x = h->xb; y = h->yb; last = h->ts + h->cr + h->air;
    }
    float dt = t - last;
    if (y < GROUND) y += fmaxf(0.0f, springf(dt, 2.6f, 6.0f)) * 7;   /* проседает вместе с буквой */
    float s = springf(dt, 3.6f, 7.0f) * 0.26f;
    float sy = 1 - s, sx = 1 + s * 0.8f;
    int look = 1;
    bool happy = dt < 0.22f;
    if (t > SETTLE) {
        happy = dt < 0.45f;
        float br = sinf((t - SETTLE) * 2 * (float)M_PI / 2.4f) * 0.03f;
        sy *= 1 + br;
        sx *= 1 - br * 0.6f;
        float ph = fmodf(t - SETTLE, 4.0f);
        look = ph < 1.8f ? -1 : (ph < 3.4f ? 0 : 1);
        if ((t >= SETTLE + 1.2f && t < SETTLE + 1.34f) || (t >= SETTLE + 3.0f && t < SETTLE + 3.14f))
            p.eyes = false;
    }
    p.x = x; p.y = y; p.sx = sx; p.sy = sy; p.look = look; p.happy = happy;
    return p;
}

/* ---------- спрайт ---------- */

static void build_sprite(uint8_t *g, int look, bool eyes_open, bool happy, bool lamp, lv_color_t *pal, float melt)
{
    for (int y = 0; y < SH; y++)
        for (int x = 0; x < SW; x++) {
            char c = SPRITE[y][x];
            g[y * SW + x] = c == 'B' ? P_B : c == 'D' ? P_D : c == 'S' ? P_S : c == 'F' ? P_F : c == 'L' ? P_L : 0;
        }
    for (int i = 0; i < 2; i++) {
        int x = (i ? 7 : 3) + look;
        if (happy) {
            g[6 * SW + x] = g[6 * SW + x + 1] = g[7 * SW + x - 1] = g[7 * SW + x + 2] = P_E;
        } else if (eyes_open) {
            for (int y = 5; y <= 7; y++) g[y * SW + x] = g[y * SW + x + 1] = P_E;
        } else {
            g[7 * SW + x] = g[7 * SW + x + 1] = P_E;
        }
    }
    lv_color_t o = c_hex(ORANGE);
    pal[P_B] = o;
    pal[P_D] = c_hex(ORANGE_DK);
    pal[P_S] = c_hex(SCREEN);
    pal[P_F] = c_hex(ORANGE_DK);
    pal[P_L] = c_hex(lamp ? LAMP_ON : LAMP_OFF);
    pal[P_E] = c_hex(EYE);
    if (melt > 0)
        for (int i = 1; i < P_COUNT; i++) pal[i] = c_mix(pal[i], o, melt);
}

/* ---------- кадр ---------- */

static void draw(dctx_t *d, const scene_frame_t *f)
{
    float t = f->t;
    lv_color_t orange = c_hex(ORANGE);

    if (t >= ZOOM + ZOOM_LEN) {                      /* финал: оранжевый экран гаснет */
        float p = clamp01((t - ZOOM - ZOOM_LEN - HOLD) / FADE);
        scene_cover = 1 - p;
        d_fill(d, c_dim(orange, powf(1 - p, 1.5f)));
        return;
    }
    float zp = t >= ZOOM ? clamp01((t - ZOOM) / ZOOM_LEN) : 0.0f;
    scene_cover = clamp01((zp - 0.55f) / 0.45f);
    float gone = clamp01(zp * 2.5f);
    float fade = clamp01((t - TEXT_IN0) / (TEXT_IN1 - TEXT_IN0));
    float text_k = fade * (1 - gone) * (1 - clamp01(f->exit_p * 2.5f));

    /* буквы: тусклые, загораются и проседают под роботом */
    for (int i = 0; i < NL; i++) {
        float tl = LAND_ON[i];
        float lit = t >= tl ? clamp01((t - tl) / 0.18f) : 0.0f;
        float dip = t >= tl ? fmaxf(0.0f, springf(t - tl, 2.6f, 6.0f)) * 7 : 0.0f;
        lv_color_t target = c_hex(L[i].word == 2 ? ORANGE : WHITE);
        lv_color_t col = c_dim(c_mix(c_hex(DIM), target, lit), text_k);
        d_text(d, f_word, L[i].ch, L[i].x, BASE + dip, col, LV_OPA_COVER);
    }

    /* пиксельная пыль при каждом приземлении */
    if (!f->asleep && f->exit_p == 0) {
        for (int i = 0; i < NLAND; i++) {
            float dt = t - LAND_T[i];
            if (dt < 0 || dt >= 0.35f) continue;
            pose_t lp = character(LAND_T[i] + 0.001f);
            float ly = lp.vis ? lp.y : GROUND, p = dt / 0.35f;
            for (int side = -1; side <= 1; side += 2)
                for (int k = 0; k < 2; k++) {
                    float sz = PX * (k == 0 ? 2 : 1);
                    float px = LAND_X[i] + side * (BODY_W / 2.0f + 4 + p * (12 + k * 9));
                    float py = ly - 4 - k * 4 - sinf(p * (float)M_PI) * (3 + k * 3);
                    px = roundf(px / PX) * PX;
                    py = roundf(py / PX) * PX;
                    d_rect(d, px, py, px + sz + 1, py + sz + 1, c_hex(GRAY), (lv_opa_t)(160 * (1 - p)), 0);
                }
        }
    }

    pose_t c = character(t);
    if (!c.vis) return;
    bool lamp = t > SETTLE ? ((int)(t * 1.6f) % 2 == 0) : true;
    if (f->asleep) {                                  /* спит: глаза закрыты, медленно дышит */
        c.eyes = false;
        c.happy = false;
        c.look = 0;
        float br = sinf(f->sleep_t * 2 * (float)M_PI / 3.6f) * 0.035f;
        c.sx = 1 - br * 0.6f;
        c.sy = 1 + br;
        lamp = ((int)(f->sleep_t * 0.5f) % 2) == 0;
    }
    float melt = 0;
    if (zp > 0) {                                     /* замах, затем рост к центру экрана */
        lamp = true;
        c.look = 0;
        if (zp < 0.18f) {
            float k = sinf(zp / 0.18f * (float)M_PI / 2);
            c.sx = 1 + 0.2f * k; c.sy = 1 - 0.25f * k; c.happy = true;
        } else {
            float q = (zp - 0.18f) / 0.82f;
            float g = 1 + 13 * powf(q, 2.2f);
            c.sx = c.sy = g;
            c.happy = false;
            float cy_body = c.y - BODY_H / 2.0f;
            c.x = lerpf(c.x, UI_W / 2.0f, ease_out_q(q));
            c.y = lerpf(cy_body, UI_H / 2.0f, ease_out_q(q)) + BODY_H * g / 2;
        }
        melt = clamp01((zp - 0.45f) / 0.35f);
    }
    scene_exit_pose(f->exit_p, &c.y, &c.sx, &c.sy);

    uint8_t grid[SW * SH];
    lv_color_t pal[P_COUNT];
    build_sprite(grid, c.look, c.eyes, c.happy, lamp, pal, melt);
    float bw = fmaxf(PX, BODY_W * c.sx), bh = fmaxf(PX, BODY_H * c.sy);
    d_sprite(d, grid, SW, SH, pal, c.x - bw / 2, c.y - bh, bw, bh, LV_OPA_COVER);

    if (zp > 0.8f) {                                  /* добиваем края экрана */
        float q = ease_in((zp - 0.8f) / 0.2f);
        float r = q * hypotf(UI_W, UI_H) * 0.62f;
        d_circle(d, c.x, c.y - bh / 2, r, orange, LV_OPA_COVER);
    }
    if (f->asleep) scene_draw_zzz(d, c.x + bw / 2 - 6, c.y - bh, f->sleep_t, c_hex(WHITE));
}

const scene_def_t SCENE_ROBOT = { "robot", begin, end, length, rest_time, draw };
