/*
 * Сцена «машинистка» (тема Codex): слайм сидит за пиксельной клавиатурой, стучит
 * по клавишам короткими лапками, буквы появляются в строке терминала, удар по Enter,
 * прыжок радости, прыжок в камеру и растворение в зелёном.
 * Эталон: tools/render_idle_typist.py.
 */
#include <math.h>
#include <string.h>
#include "ui_scene_priv.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define PX 4
#define SW 12
#define SH 10
#define SC 1.5f
#define BW (SW * PX * SC)
#define BH (SH * PX * SC)

#define GREEN    0x10A37F
#define GREEN_LT 0x78E6C4
#define GREEN_DK 0x096C54
#define EYE      0x061C16
#define WHITE    0xECECF1
#define KEY_BG   0x282932
#define KEY      0x40414F
#define KEY_EDGE 0x1E1F26

#define ZOOM_LEN 0.9f
#define HOLD 0.12f
#define FADE 0.5f
#define FADE_IN0 0.1f
#define FADE_IN1 0.5f
#define FALL0 0.45f
#define FALL1 0.85f
#define REACH 0.06f
#define PRESS 0.05f
#define BACK 0.08f
#define JOY_LEN 0.42f

static const char *const SPRITE[SH] = {
    "....GGGG....",
    "..GGGGGGGG..",
    ".GHHGGGGGGG.",
    ".GHGGGGGGGG.",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    ".DDDDDDDDDD.",
};
enum { P_G = 1, P_H, P_D, P_E, P_COUNT };

static const char *const TEXT = "Ready to work";
#define TEXT_LEN 13

/* клавиатура */
#define KW 12
#define KH 8
#define KG 3
#define SPACE_SLOTS 5
static const char *const ROWS[3] = { "QWERTYUIOP", "ASDFGHJKL\n", "ZXC MN" };   /* \n — Enter, пробел — Space */
typedef struct { char lab; float x, y, w; } key_t;
static key_t KEYS[32];
static int NK;
static float BXK, board_w, board_h;
static const float BY = 178;
static const float BASE = 92;
static const float CX = UI_W / 2.0f;
static const float SHOULDER_K = 0.62f;
#define SEAT_Y (BY + 14)

static lv_font_t *f_word;
static float CH, CAP, TX, TEXT_X;
static float STROKE_T[TEXT_LEN];
static float LAST_KEY, ENTER_UP, ENTER_HIT, JOY, SETTLE, ZOOM, END_T;

static const key_t *key_of(char lab)
{
    for (int i = 0; i < NK; i++)
        if (KEYS[i].lab == lab) return &KEYS[i];
    return &KEYS[0];
}

static char key_for(char ch) { return ch == ' ' ? ' ' : (char)(ch >= 'a' && ch <= 'z' ? ch - 32 : ch); }

static void key_top(char lab, float *x, float *y)
{
    const key_t *k = key_of(lab);
    *x = k->x + k->w / 2;
    *y = k->y + 2;
}

static int arm_for(char lab)
{
    if (lab == ' ') return 1;                         /* пробел — правой, как многие печатают */
    const key_t *k = key_of(lab);
    return (k->x + k->w / 2) < CX ? 0 : 1;
}

static void begin(ui_theme_t theme)
{
    (void)theme;
    f_word = scene_font("mono", 40);
    CH = text_w(f_word, "M");
    CAP = cap_height(f_word);
    float line_w = CH * (2 + TEXT_LEN + 1);
    TX = (UI_W - line_w) / 2;
    TEXT_X = TX + CH * 2;

    board_w = 10 * KW + 11 * KG + 8;
    board_h = 3 * KH + 4 * KG;
    BXK = (UI_W - board_w) / 2;
    NK = 0;
    for (int r = 0; r < 3; r++) {
        float x = BXK + KG + r * 4, y = BY + KG + r * (KH + KG);
        for (const char *c = ROWS[r]; *c; c++) {
            float w = *c == ' ' ? KW * SPACE_SLOTS + KG * (SPACE_SLOTS - 1) : KW;
            KEYS[NK++] = (key_t){ *c, x, y, w };
            x += w + KG;
        }
    }

    static const float rhythm[13] = { 0.0f, 0.03f, -0.02f, 0.04f, 0.0f, -0.03f, 0.02f, 0.05f, -0.01f, 0.0f, 0.03f, -0.02f, 0.01f };
    float t = 1.25f;
    for (int i = 0; i < TEXT_LEN; i++) {
        STROKE_T[i] = t;
        t += (TEXT[i] == ' ' ? 0.26f : 0.17f) + rhythm[i % 13];
    }
    LAST_KEY = STROKE_T[TEXT_LEN - 1];
    ENTER_UP = LAST_KEY + 0.65f;
    ENTER_HIT = ENTER_UP + 0.22f;
    JOY = ENTER_HIT + 0.55f;
    SETTLE = JOY + JOY_LEN;
    ZOOM = SETTLE + 1.9f;
    END_T = ZOOM + ZOOM_LEN + HOLD + FADE;
}

static void end(void)
{
    if (f_word) lv_tiny_ttf_destroy(f_word);
    f_word = NULL;
}

static float length(void) { return END_T; }
static float rest_time(void) { return SETTLE + 1.5f; }

/* ---------- лапки ---------- */

typedef struct { float x, y; } pt_t;

static void arm_tips(float t, pt_t tips[2], char *pressed, int *npressed)
{
    pt_t home[2];
    key_top('F', &home[0].x, &home[0].y);
    key_top('J', &home[1].x, &home[1].y);
    tips[0] = home[0];
    tips[1] = home[1];
    *npressed = 0;
    for (int i = 0; i < TEXT_LEN; i++) {
        char lab = key_for(TEXT[i]);
        int side = arm_for(lab);
        float dt = t - STROKE_T[i];
        pt_t tgt;
        key_top(lab, &tgt.x, &tgt.y);
        if (dt >= -REACH && dt < 0) {
            float p = ease_out_q((dt + REACH) / REACH);
            tips[side] = (pt_t){ lerpf(home[side].x, tgt.x, p), lerpf(home[side].y, tgt.y - 6, p) };
        } else if (dt >= 0 && dt < PRESS) {
            tips[side] = (pt_t){ tgt.x, tgt.y + 2 };
            pressed[(*npressed)++] = lab;
        } else if (dt >= PRESS && dt < PRESS + BACK) {
            float p = ease_out_q((dt - PRESS) / BACK);
            tips[side] = (pt_t){ lerpf(tgt.x, home[side].x, p), lerpf(tgt.y, home[side].y, p) };
        }
    }
    pt_t e;
    key_top('\n', &e.x, &e.y);
    float up_y = SEAT_Y - BH - 8;
    if (t >= ENTER_UP && t < ENTER_HIT) {             /* Enter: правая замахивается, левая вскинута */
        float p = ease_out_q((t - ENTER_UP) / (ENTER_HIT - ENTER_UP));
        tips[0] = (pt_t){ lerpf(home[0].x, CX - BW / 2 - 10, p), lerpf(home[0].y, up_y + 6, p) };
        tips[1] = (pt_t){ lerpf(home[1].x, CX + BW / 2 + 12, p), lerpf(home[1].y, up_y, p) };
    } else if (t >= ENTER_HIT && t < ENTER_HIT + 0.16f) {
        tips[0] = (pt_t){ CX - BW / 2 - 10, up_y + 6 };
        tips[1] = (pt_t){ e.x, e.y + 2 };
        pressed[(*npressed)++] = '\n';
    } else if (t >= ENTER_HIT + 0.16f && t < ENTER_HIT + 0.3f) {
        float p = ease_out_q((t - ENTER_HIT - 0.16f) / 0.14f);
        tips[0] = (pt_t){ lerpf(CX - BW / 2 - 10, home[0].x, p), lerpf(up_y + 6, home[0].y, p) };
        tips[1] = (pt_t){ lerpf(e.x, home[1].x, p), lerpf(e.y, home[1].y, p) };
    } else if (t >= JOY && t < JOY + JOY_LEN) {       /* лапки вверх от радости */
        float q = (t - JOY) / JOY_LEN;
        float lift = 20 * 4 * q * (1 - q);
        tips[0] = (pt_t){ CX - BW / 2 - 8, SEAT_Y - BH - 6 - lift };
        tips[1] = (pt_t){ CX + BW / 2 + 8, SEAT_Y - BH - 6 - lift };
    }
}

static float key_glow(char lab, float t)
{
    float best = 0;
    if (lab == '\n') {
        float dt = t - ENTER_HIT;
        return (dt >= 0 && dt < 0.35f) ? 1 - dt / 0.35f : 0;
    }
    for (int i = 0; i < TEXT_LEN; i++) {
        if (key_for(TEXT[i]) != lab) continue;
        float dt = t - STROKE_T[i];
        if (dt >= 0 && dt < 0.35f) best = fmaxf(best, 1 - dt / 0.35f);
    }
    return best;
}

/* ---------- тело ---------- */

typedef struct { bool vis; float x, y, sx, sy; int look_x, look_y; bool eyes, happy; } pose_t;

static pose_t body(float t)
{
    pose_t p = { 0 };
    if (t < FALL0) return p;
    p.vis = true;
    p.eyes = true;
    if (t < FALL1) {
        float q = ease_in((t - FALL0) / (FALL1 - FALL0));
        float st = 1 + 0.45f * q;
        p.x = CX; p.y = lerpf(-10, SEAT_Y, q); p.sx = 1 / sqrtf(st); p.sy = st;
        return p;
    }
    float x = CX, y = SEAT_Y;
    float s = springf(t - FALL1, 2.8f, 4.2f) * 0.38f;
    float sx = 1 + s * 0.9f, sy = 1 - s;
    for (int i = 0; i < TEXT_LEN; i++) {               /* каждое нажатие — кивок и наклон к лапке */
        float dt = t - STROKE_T[i];
        if (dt >= 0 && dt < 0.18f) {
            float k = sinf(dt / 0.18f * (float)M_PI);
            int side = arm_for(key_for(TEXT[i]));
            y += 2 * k;
            x += (side ? 2 : -2) * k;
            sy *= 1 - 0.05f * k;
            sx *= 1 + 0.04f * k;
        }
    }
    if (t > 1.0f && t < ENTER_UP) p.look_y = -1;      /* смотрит на экран, пока печатает */
    if (t >= ENTER_UP && t < ENTER_HIT) {
        float k = ease_out_q((t - ENTER_UP) / (ENTER_HIT - ENTER_UP));
        sy *= 1 + 0.12f * k;
        sx *= 1 - 0.08f * k;
        p.look_y = -1;
    }
    if (t >= ENTER_HIT && t < JOY) {
        float s2 = springf(t - ENTER_HIT, 3.0f, 5.0f) * 0.3f;
        sy = 1 - s2; sx = 1 + s2 * 0.9f;
        p.happy = true;
    }
    if (t >= JOY && t < JOY + JOY_LEN) {
        float q = (t - JOY) / JOY_LEN;
        y -= 20 * 4 * q * (1 - q);
        float st = 1 + 0.25f * fabsf(1 - 2 * q);
        sx = 1 / sqrtf(st); sy = st;
        p.happy = true;
    }
    if (t >= SETTLE) {
        float dt = t - SETTLE;
        float s3 = springf(dt, 2.8f, 4.2f) * 0.3f;
        float br = sinf(dt * 2 * (float)M_PI / 2.0f) * 0.045f;
        sy = (1 - s3) * (1 + br);
        sx = (1 + s3 * 0.9f) * (1 - br * 0.7f);
        p.happy = dt < 0.4f;
        float ph = fmodf(dt, 3.0f);
        p.look_x = ph < 1.0f ? 0 : (ph < 1.8f ? 1 : 0);
        p.look_y = ph < 1.0f ? -1 : 0;
        if (dt >= 1.1f && dt < 1.24f) p.eyes = false;
    }
    p.x = x; p.y = y; p.sx = sx; p.sy = sy;
    return p;
}

static void build_sprite(uint8_t *g, const pose_t *p, lv_color_t *pal, float melt)
{
    for (int y = 0; y < SH; y++)
        for (int x = 0; x < SW; x++) {
            char c = SPRITE[y][x];
            g[y * SW + x] = c == 'G' ? P_G : c == 'H' ? P_H : c == 'D' ? P_D : 0;
        }
    for (int k = 0; k < 2; k++) {
        int x = (k ? 7 : 3) + p->look_x;
        if (p->happy) {
            g[5 * SW + x] = g[5 * SW + x + 1] = g[6 * SW + x - 1] = g[6 * SW + x + 2] = P_E;
        } else if (p->eyes) {
            int top = p->look_y < 0 ? 4 : 5;          /* взгляд вверх: глаза на пиксель выше */
            for (int y = top; y <= top + 1; y++) g[y * SW + x] = g[y * SW + x + 1] = P_E;
        } else {
            g[6 * SW + x] = g[6 * SW + x + 1] = P_E;
        }
    }
    lv_color_t green = c_hex(GREEN);
    pal[P_G] = green;
    pal[P_H] = c_hex(GREEN_LT);
    pal[P_D] = c_hex(GREEN_DK);
    pal[P_E] = c_hex(EYE);
    if (melt > 0)
        for (int i = 1; i < P_COUNT; i++) pal[i] = c_mix(pal[i], green, melt);
}

static void draw_arm(dctx_t *d, float x0, float y0, float x1, float y1)
{
    float half = PX / 2.0f, r = PX * 0.75f;
    int n = (int)(hypotf(x1 - x0, y1 - y0) / half);
    if (n < 2) n = 2;
    lv_color_t col = c_hex(GREEN);
    for (int i = 0; i <= n; i++) {
        float p = (float)i / n;
        float x = roundf(lerpf(x0, x1, p) / half) * half;
        float y = roundf(lerpf(y0, y1, p) / half) * half;
        d_rect(d, x - r, y - r, x + r, y + r, col, LV_OPA_COVER, 0);
    }
}

static void draw(dctx_t *d, const scene_frame_t *f)
{
    float t = f->t;
    lv_color_t green = c_hex(GREEN), white = c_hex(WHITE), green_lt = c_hex(GREEN_LT);

    if (t >= ZOOM + ZOOM_LEN) {
        float p = clamp01((t - ZOOM - ZOOM_LEN - HOLD) / FADE);
        scene_cover = 1 - p;
        d_fill(d, c_dim(green, powf(1 - p, 1.5f)));
        return;
    }
    float zp = t >= ZOOM ? clamp01((t - ZOOM) / ZOOM_LEN) : 0.0f;
    scene_cover = clamp01((zp - 0.55f) / 0.45f);
    float gone = clamp01(zp * 2.5f);
    float ex = 1 - clamp01(f->exit_p * 2.5f);
    float fade = clamp01((t - FADE_IN0) / (FADE_IN1 - FADE_IN0)) * (1 - gone) * ex;

    /* строка терминала */
    d_text(d, f_word, ">", TX, BASE, c_dim(green, fade), LV_OPA_COVER);
    float enter_flash = t >= ENTER_HIT ? clamp01(1 - (t - ENTER_HIT) / 0.5f) : 0.0f;
    int typed = 0;
    for (int i = 0; i < TEXT_LEN; i++) {
        if (t < STROKE_T[i]) continue;
        typed = i + 1;
        if (TEXT[i] == ' ') continue;
        int word = 0;
        for (int k = 0; k < i; k++) word += TEXT[k] == ' ';
        float fl = fmaxf(1 - clamp01((t - STROKE_T[i]) / 0.3f), enter_flash);
        lv_color_t col = c_dim(c_mix(word == 2 ? green : white, green_lt, fl * 0.8f), (1 - gone) * ex);
        char ch[2] = { TEXT[i], 0 };
        float sy = lerpf(0.35f, 1.0f, ease_out_q(clamp01((t - STROKE_T[i]) / 0.12f)));
        d_text_squash(d, f_word, ch, TEXT_X + CH * i, BASE, col, sy);
    }
    float cur_x = TEXT_X + CH * typed;
    bool typing = t >= STROKE_T[0] - 0.3f && t < LAST_KEY + 0.25f;
    if (fade > 0 && (typing || ((int)(t * 2)) % 2 == 0))
        d_rect(d, cur_x + 2, BASE - CAP, cur_x + CH * 0.62f, BASE + 2, c_dim(white, fade * 0.85f), LV_OPA_COVER, 0);

    /* слайм рисуется до клавиатуры: клавиатура закрывает низ тела */
    pose_t b = body(t);
    pt_t tips[2];
    char pressed[4];
    int np;
    arm_tips(t, tips, pressed, &np);
    if (f->asleep && b.vis) {
        b.eyes = false; b.happy = false; b.look_x = b.look_y = 0;
        b.sx = 1; b.sy = 1 + sinf(f->sleep_t * 2 * (float)M_PI / 3.6f) * 0.04f;
        tips[0].y += 1; tips[1].y += 1;
    }
    float bx_off = 0, by_exit = b.y, sx_e = b.sx, sy_e = b.sy;
    scene_exit_pose(f->exit_p, &by_exit, &sx_e, &sy_e);
    if (b.vis && zp == 0) {
        float bw = BW * sx_e, bh = BH * sy_e;
        uint8_t grid[SW * SH];
        lv_color_t pal[P_COUNT];
        build_sprite(grid, &b, pal, 0);
        d_sprite(d, grid, SW, SH, pal, b.x - bw / 2 + bx_off, by_exit - bh, bw, bh, LV_OPA_COVER);
    }

    /* клавиатура */
    if (fade > 0) {
        d_rect(d, BXK, BY, BXK + board_w, BY + board_h, c_dim(c_hex(KEY_BG), fade), LV_OPA_COVER, 4);
        for (int i = 0; i < NK; i++) {
            const key_t *k = &KEYS[i];
            bool down = memchr(pressed, k->lab, (size_t)np) != NULL;
            float glow = key_glow(k->lab, t);
            lv_color_t base_col = c_hex(k->lab == '\n' ? GREEN : KEY);
            lv_color_t col = c_mix(base_col, green_lt, glow);
            d_rect(d, k->x, k->y + 2, k->x + k->w, k->y + KH + 2, c_dim(c_hex(KEY_EDGE), fade), LV_OPA_COVER, 0);
            d_rect(d, k->x, k->y + (down ? 2 : 0), k->x + k->w, k->y + KH - 2 + (down ? 2 : 0),
                   c_dim(col, fade), LV_OPA_COVER, 0);
        }
    }

    /* лапки поверх клавиатуры (при уходе прячутся вместе с телом) */
    if (b.vis && zp == 0 && t >= FALL1 && f->exit_p < 0.3f) {
        float bh = BH * b.sy, top = b.y - bh;
        for (int side = 0; side < 2; side++) {
            float sxo = (side == 0 ? -1 : 1) * (BW * b.sx / 2 - 8);
            draw_arm(d, b.x + sxo, top + bh * SHOULDER_K, tips[side].x, tips[side].y);
        }
    }

    /* финал: прыжок в камеру и растворение в зелёном */
    if (zp > 0 && b.vis) {
        float x = b.x, y = b.y, sx, sy;
        bool happy;
        if (zp < 0.18f) {
            float k = sinf(zp / 0.18f * (float)M_PI / 2);
            sx = 1 + 0.3f * k; sy = 1 - 0.34f * k; happy = true;
        } else {
            float q = (zp - 0.18f) / 0.82f;
            float g = 1 + 10 * powf(q, 2.2f);
            sx = sy = g; happy = false;
            x = lerpf(x, UI_W / 2.0f, ease_out_q(q));
            y = lerpf(y - BH / 2, UI_H / 2.0f, ease_out_q(q)) + BH * g / 2;
        }
        pose_t zpz = { true, x, y, sx, sy, 0, 0, true, happy };
        uint8_t grid[SW * SH];
        lv_color_t pal[P_COUNT];
        build_sprite(grid, &zpz, pal, clamp01((zp - 0.45f) / 0.35f));
        float bw = BW * sx, bh = BH * sy;
        d_sprite(d, grid, SW, SH, pal, x - bw / 2, y - bh, bw, bh, LV_OPA_COVER);
        if (zp > 0.8f) {
            float q = ease_in((zp - 0.8f) / 0.2f);
            d_circle(d, x, y - bh / 2, q * hypotf(UI_W, UI_H) * 0.62f, green, LV_OPA_COVER);
        }
    }
    if (f->asleep && b.vis) scene_draw_zzz(d, b.x + BW / 2 - 4, b.y - BH, f->sleep_t, white);
}

const scene_def_t SCENE_TYPIST = { "typist", begin, end, length, rest_time, draw };
