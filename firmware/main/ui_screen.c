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

#include "version.h"


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
/*
 * Ночное небо, робот Claude и слайм Codex по очереди подпрыгивают и пускают сердечки,
 * название набирается по буквам переливом оранжевого в зелёный, подпись «prod by yakory777»
 * колышется волной. Внизу — статус Wi-Fi и полоска загрузки. Заставка ждёт Wi-Fi до 15 с
 * (UI_SPLASH_MAX_MS), уходит раньше, когда сеть подключилась, пришла задача, сопряжение
 * или нажали кнопку, — см. tick_cb().
 */

static uint32_t splash_end = UI_SPLASH_MAX_MS;   /* когда заставка уходит, мс от старта; только уменьшается */
static uint32_t boot_wifi_at;                    /* когда подключился Wi-Fi (0 — ещё нет) */
static bool boot_skip;                           /* нажали кнопку или пришло сопряжение */
static uint32_t splash_fade = 450;               /* затухание в конце, мс; при пропуске короче */

static const char *const HEART[6] = { ".HH.HH.", "HHHHHHH", "HHHHHHH", ".HHHHH.", "..HHH..", "...H..." };

#define C_CLAUDE 0xD97757
#define C_GOLD   0xFFD68C
#define C_CODEX  0x10A37F
#define C_MINT   0x78E6C4

/* переливы по кругу: оранжевый → золотой → зелёный → мятный → оранжевый */
static lv_color_t shimmer(float u)
{
    static const uint32_t P[4] = { C_CLAUDE, C_GOLD, C_CODEX, C_MINT };
    u -= floorf(u);
    float x = u * 4;
    int i = (int)x;
    return c_mix(c_hex(P[i % 4]), c_hex(P[(i + 1) % 4]), x - i);
}

static float hash01(uint32_t n)                    /* детерминированный «случай» для звёзд */
{
    n ^= n >> 16; n *= 0x7FEB352Du;
    n ^= n >> 15; n *= 0x846CA68Bu;
    n ^= n >> 16;
    return (n >> 8) / 16777216.0f;
}

/* падающая звезда раз в несколько секунд: голова и хвост переливом */
static void draw_meteor(dctx_t *d, float t, float k)
{
    const float every = 3.6f, dur = 0.7f;
    if (t < 2.2f) return;
    int n = (int)((t - 2.2f) / every);
    float p = (t - 2.2f - n * every) / dur;
    if (p > 1) return;
    float x0 = 120 + hash01(n * 13 + 3) * 300, y0 = 10 + hash01(n * 13 + 4) * 30;
    float hx = x0 + p * 170, hy = y0 + p * 70;
    float a = sinf(p * (float)M_PI) * k;
    for (int j = 0; j < 6; j++) {
        float q = j / 6.0f;
        d_line(d, hx - (q) * 60, hy - q * 24.7f, hx - (q + 1 / 6.0f) * 60, hy - (q + 1 / 6.0f) * 24.7f, 2.2f - q * 1.6f,
               c_dim(shimmer(n * 0.3f + q * 0.4f), a * (1 - q)), LV_OPA_COVER);
    }
    d_circle(d, hx, hy, 2.2f, c_dim(c_hex(0xFFFFFF), a), LV_OPA_COVER);
}

static void draw_stars(dctx_t *d, float t, float k)
{
    for (int i = 0; i < 46; i++) {
        float x = hash01(i * 3 + 1) * UI_W, y = 8 + hash01(i * 3 + 2) * 132;
        x = fmodf(x - t * (4 + 6 * hash01(i * 7)) + UI_W, UI_W);           /* медленно плывут влево */
        float tw = 0.35f + 0.65f * (0.5f + 0.5f * sinf(t * (1.3f + 2.2f * hash01(i * 5)) + i));
        float appear = clamp01((t - hash01(i * 11) * 0.8f) / 0.5f);
        float a = tw * appear * k;
        lv_color_t c = (i % 5 == 0) ? c_hex(C_CLAUDE) : (i % 5 == 1) ? c_hex(C_MINT) : c_hex(0xFFFFFF);
        float r = (i % 9 == 0) ? 1.6f : 1.0f;
        d_rect(d, x - r, y - r, x + r, y + r, c_dim(c, a), LV_OPA_COVER, 0);
        if (i % 9 == 0 && tw > 0.85f) {                                       /* яркие — искоркой-крестиком */
            float l = 4 * (tw - 0.85f) / 0.15f;
            d_rect(d, x - l, y - 0.5f, x + l, y + 0.5f, c_dim(c, a * 0.7f), LV_OPA_COVER, 0);
            d_rect(d, x - 0.5f, y - l, x + 0.5f, y + l, c_dim(c, a * 0.7f), LV_OPA_COVER, 0);
        }
    }
}

/* прыжок по кругу: 0 — на земле, иначе высота; sx, sy — сплющивание на толчке и приземлении */
static float hop(float t, float phase, float *sx, float *sy)
{
    const float period = 2.4f, dur = 0.55f;
    float p = fmodf(t - phase + period * 10, period);
    *sx = *sy = 1;
    if (p < 0.08f) { float q = p / 0.08f; *sy = 1 - 0.18f * sinf(q * (float)M_PI); *sx = 1 / sqrtf(*sy); return 0; }
    p -= 0.08f;
    if (p < dur) return sinf(p / dur * (float)M_PI) * 16;
    p -= dur;
    if (p < 0.12f) { float q = p / 0.12f; *sy = 1 - 0.2f * sinf(q * (float)M_PI); *sx = 1 / sqrtf(*sy); }
    return 0;
}

static void draw_heart(dctx_t *d, float x, float y, float age, uint32_t col, float k)
{
    if (age < 0 || age > 1.3f) return;
    float a = (1 - clamp01((age - 0.7f) / 0.6f)) * k;
    float s = 0.6f + 0.4f * ease_out_q(clamp01(age / 0.25f));
    const uint32_t cols[1] = { col };
    draw_ascii_sprite(d, HEART, 7, 6, "H", cols, x + sinf(age * 7) * 3, y - age * 34, 14 * s, 12 * s, a);
}

/* ---------- логотип: экран с «>_», делениями прогресса и точкой «в эфире» ----------
 * Те же фигуры, что в docs/logo/logo.svg и LOGO в hardware/case/lcd/geometry.py: квадрат 100 × 100 единиц.
 * s — пикселей на единицу; t — секунды от начала появления (большие t — всё уже на месте). */

#define LOGO_INTRO  1.5f                 /* сколько логотип один в центре, с */
#define LOGO_FLY    0.55f                /* перелёт к названию, с */

static void draw_logo(dctx_t *d, float cx, float cy, float s, float t, float k)
{
#define LX(u) (cx + ((u) - 50) * s)
#define LY(v) (cy + ((v) - 50) * s)
    const lv_color_t cream = c_hex(0xF5F0E8);
    float fa = clamp01(t / 0.2f) * k;
    d_rect(d, LX(4), LY(14), LX(96), LY(86), c_dim(cream, fa), LV_OPA_COVER, (int32_t)(15.5f * s));
    d_rect(d, LX(11), LY(21), LX(89), LY(79), c_dim(c_hex(0x17151C), fa), LV_OPA_COVER, (int32_t)(8.5f * s));

    float p = clamp01((t - 0.25f) / 0.3f);                                   /* «>» прочерчивается */
    if (p > 0) {
        lv_color_t o = c_dim(c_hex(C_CLAUDE), k);
        float a = clamp01(p * 2), b = clamp01(p * 2 - 1);
        d_line(d, LX(24), LY(34), LX(24 + 16 * a), LY(34 + 12 * a), 7 * s, o, LV_OPA_COVER);
        if (b > 0) d_line(d, LX(40), LY(46), LX(40 - 16 * b), LY(46 + 12 * b), 7 * s, o, LV_OPA_COVER);
    }
    if (t > 0.55f && fmodf(t - 0.55f, 1.0f) < 0.6f)                          /* курсор мигает */
        d_rect(d, LX(46), LY(52), LX(62), LY(58), c_dim(cream, k), LV_OPA_COVER, (int32_t)(1.5f * s));

    static const uint32_t SEG[3] = { C_CLAUDE, C_GOLD, C_MINT };
    for (int i = 0; i < 5; i++) {
        float u = 22 + 12 * i;
        float on = i < 3 ? clamp01((t - 0.6f - i * 0.15f) / 0.12f) : 0;
        lv_color_t c = c_mix(c_hex(0x3A3A40), c_hex(i < 3 ? SEG[i] : 0x3A3A40), on);
        if (i == 3 && t > 1.2f) c = c_mix(c, c_hex(C_GOLD), 0.25f + 0.25f * sinf(t * 5));   /* четвёртое — «в работе» */
        float pop = i < 3 && on > 0 && on < 1 ? 1.5f * (1 - on) : 0;
        d_rect(d, LX(u - pop), LY(67 - pop), LX(u + 10 + pop), LY(74 + pop), c_dim(c, fa), LV_OPA_COVER, (int32_t)(1.5f * s));
    }
    float da = clamp01((t - 1.0f) / 0.2f) * k;                               /* точка «в эфире» пульсирует */
    if (da > 0) {
        float pulse = 0.5f + 0.5f * sinf((t - 1.0f) * 4);
        d_circle(d, LX(78), LY(32), (6 + 3 * pulse) * s, c_dim(c_hex(C_MINT), da * 0.3f), LV_OPA_COVER);
        d_circle(d, LX(78), LY(32), 4.5f * s, c_dim(c_hex(C_MINT), da), LV_OPA_COVER);
    }
#undef LX
#undef LY
}

/* текст по буквам: каждая буква своим цветом и своей высотой (только ASCII) */
typedef lv_color_t (*letter_color_fn)(int i, float t);
static void d_letters(dctx_t *d, const lv_font_t *f, const char *txt, float x0, float base, float t,
                      float reveal_t0, float per, float wave, int wave_from, letter_color_fn color, float k)
{
    int n = (int)strlen(txt);
    for (int i = 0; i < n; i++) {
        float age = t - (reveal_t0 + i * per);
        if (age < 0) break;
        char ch[2] = { txt[i], 0 };
        float pop = (1 - ease_out_q(clamp01(age / 0.25f))) * 7;                /* буква «впрыгивает» */
        float y = base - pop + (i >= wave_from ? sinf(t * 3.2f + i * 0.55f) * wave : 0);
        float a = clamp01(age / 0.15f) * k;
        d_text(d, f, ch, x0 + text_w_n(f, txt, (uint32_t)i), y, c_dim(color(i, t), a), LV_OPA_COVER);
    }
}

static lv_color_t title_color(int i, float t) { return shimmer(t * 0.18f - i * 0.035f); }
static lv_color_t credit_color(int i, float t) { return i < 8 ? c_hex(0x8E8E93) : shimmer(t * 0.35f + (i - 8) * 0.09f); }

static void splash_draw(lv_event_t *e)
{
    dctx_t d = dctx_from_event(e);
    float t = since_s(boot_t0);
    float end = splash_end / 1000.0f;
    float fade = splash_fade / 1000.0f;
    float k = 1 - clamp01((t - (end - fade)) / fade);                         /* гаснет в конце */
    d_fill(&d, lv_color_black());
    draw_stars(&d, t, k);
    draw_meteor(&d, t, k);

    /* сначала логотип крупно в центре, потом он перелетает к названию, и начинается остальное */
    const lv_font_t *ft = ui_status_font(1), *fs = ui_status_font(0);
    const char *title = "Agent Status Bar";
    const float ls = 0.42f, gap = 10;                                        /* маленький логотип у названия */
    float lock_w = 92 * ls + gap + text_w(ft, title);
    float tx = (UI_W - lock_w) / 2 + 92 * ls + gap;                          /* название сдвинуто вправо */
    float q = ease_out_q(clamp01((t - LOGO_INTRO) / LOGO_FLY));
    float lpop = t < 0.45f ? 1 - springf(t, 1.6f, 6.0f) * 0.35f : 1;         /* выпрыгивает */
    float big = 1.25f * lpop;
    draw_logo(&d, lerpf(UI_W / 2.0f, (UI_W - lock_w) / 2 + 46 * ls, q), lerpf(108, 164 - 10, q),
              lerpf(big, ls, q), t, k);
    t -= LOGO_INTRO;                                                         /* дальше — прежняя заставка */
    if (t < 0) return;

    /* маскоты: падают, пружинят, потом прыгают по очереди и пускают сердечки */
    float cx = UI_W / 2.0f, ground = 118;
    for (int i = 0; i < 2; i++) {
        float t0 = 0.15f + i * 0.18f, x = cx + (i ? 48 : -48);
        if (t < t0) continue;
        float dt = t - t0, y, sx = 1, sy = 1;
        if (dt < 0.35f) {
            float q = ease_in(dt / 0.35f);
            y = lerpf(-60, ground, q);
            sy = 1 + 0.35f * q; sx = 1 / sqrtf(sy);
        } else if (t < 1.6f) {
            y = ground;
            float s = springf(dt - 0.35f, 3.2f, 5.0f) * 0.3f;
            sy = 1 - s; sx = 1 + s * 0.8f;
        } else {
            y = ground - hop(t, 1.6f + i * 1.2f, &sx, &sy);
        }
        if (i == 0) {
            uint32_t cols[6];
            memcpy(cols, ROBOT_COLS, sizeof cols);
            if (fmodf(t, 0.8f) > 0.4f) cols[4] = 0xFF8A5C;                   /* огонёк антенны мигает */
            draw_ascii_sprite(&d, ROBOT, 12, 13, "BDSFLE", cols, x, y, 60 * sx, 65 * sy, k);
        } else {
            uint32_t cols[4];
            memcpy(cols, SLIME_COLS, sizeof cols);
            if (fmodf(t + 0.9f, 2.7f) < 0.13f) cols[3] = cols[0];             /* слайм моргает */
            draw_ascii_sprite(&d, SLIME, 12, 10, "GHDE", cols, x, y, 60 * sx, 50 * sy, k);
        }
    }
    /* сердечко при приземлении и на вершине каждого прыжка — цвета чередуются */
    draw_heart(&d, cx, ground - 34, t - 0.75f, 0xFF5C8A, k);
    for (int j = 0; j < 8; j++) {
        float at = 1.6f + j * 1.2f + 0.35f;
        static const uint32_t HC[4] = { C_CLAUDE, C_MINT, 0xFF5C8A, C_GOLD };
        draw_heart(&d, cx + (j % 2 ? 26 : -26), ground - 56, t - at, HC[j % 4], k);
    }

    /* название по буквам рядом с логотипом, перелив; подпись волной */
    d_letters(&d, ft, title, tx, 164, t, 0.4f, 0.05f, 0, 0, title_color, k);
    const char *credit = "prod by yakory777";
    d_letters(&d, fs, credit, (UI_W - text_w(fs, credit)) / 2, 193, t, 1.7f, 0.035f, 2.5f, 8, credit_color, k);

    char ver[16];
    snprintf(ver, sizeof ver, "v%s", FW_VERSION);
    d_text(&d, fs, ver, 16, 30, c_dim(c_hex(0x6E6E73), clamp01((t - 1.0f) / 0.4f) * k), LV_OPA_COVER);

    /* статус Wi-Fi и полоска загрузки */
    float st = clamp01((t - 1.2f) / 0.4f) * k;
    char line[80];
    lv_color_t lc = c_hex(0x8E8E93);
    if (boot_wifi_at) {
        snprintf(line, sizeof line, "%s", tr(TR_BOOT_WIFI_OK));
        lc = c_hex(0x34C759);
        float pop = ease_out_q(clamp01((t - boot_wifi_at / 1000.0f) / 0.3f));   /* галочка рисуется линиями — */
        float x = (UI_W - text_w(fs, line)) / 2 + 12, y = 216;                  /* в урезанном шрифте её нет */
        d_line(&d, x - 30, y - 1, x - 30 + 5 * pop, y + 4 * pop, 2.5f, c_dim(lc, st), LV_OPA_COVER);
        if (pop > 0.5f)
            d_line(&d, x - 25, y + 4, x - 25 + 10 * (pop - 0.5f) * 2, y + 4 - 11 * (pop - 0.5f) * 2, 2.5f, c_dim(lc, st), LV_OPA_COVER);
        d_text(&d, fs, line, x, 222, c_dim(lc, st), LV_OPA_COVER);
        line[0] = 0;
    } else if (!platform_wifi_configured()) {
        snprintf(line, sizeof line, "%s", tr(TR_BOOT_WIFI_NONE));
    } else {
        int dots = (int)(t * 2.5f) % 4;
        snprintf(line, sizeof line, "%s%.*s", tr(TR_BOOT_WIFI_WAIT), dots, "...");
        float w = text_w(fs, tr(TR_BOOT_WIFI_WAIT));                           /* точки не двигают текст */
        d_text(&d, fs, line, (UI_W - w) / 2 - 6, 222, c_dim(lc, st), LV_OPA_COVER);
        line[0] = 0;
    }
    if (line[0]) d_text(&d, fs, line, (UI_W - text_w(fs, line)) / 2, 222, c_dim(lc, st), LV_OPA_COVER);

    float prog = clamp01((t + LOGO_INTRO) / end);
    float bw = UI_W - 2 * 120.0f, bx = 120, by = 232;
    d_rect(&d, bx, by, bx + bw, by + 3, c_dim(c_hex(0x2C2C2E), k), LV_OPA_COVER, 2);
    if (prog > 0.01f) {
        d_rect(&d, bx, by, bx + bw * prog, by + 3, c_dim(shimmer(t * 0.25f), k), LV_OPA_COVER, 2);
        d_circle(&d, bx + bw * prog, by + 1.5f, 3.2f, c_dim(c_hex(0xFFFFFF), k * (0.6f + 0.4f * sinf(t * 8))), LV_OPA_COVER);
    }
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
    d_text(&d, fs, hint2, (UI_W - text_w(fs, hint2)) / 2, 217, c_hex(0xFFFFFF), LV_OPA_COVER);
}

void ui_screen_pairing(const char *code)
{
    if (code && *code && mode == MODE_BOOT) boot_skip = true;                 /* сопряжение — не ждём конца заставки */
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

bool ui_screen_pairing_visible(void) { return !lv_obj_has_flag(pairing, LV_OBJ_FLAG_HIDDEN); }

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
    if (mode == MODE_BOOT) { boot_skip = true; return; }                       /* кнопка на заставке — пропустить */
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
        uint32_t el = lv_tick_elaps(boot_t0), want = UI_SPLASH_MAX_MS;
        if (!boot_wifi_at && platform_wifi_level() >= 0) boot_wifi_at = el ? el : 1;
        if (boot_wifi_at) want = boot_wifi_at + UI_SPLASH_WIFI_MS;                 /* сеть есть — ещё чуть-чуть */
        else if (!platform_wifi_configured()) want = UI_SPLASH_MIN_MS;            /* ждать нечего */
        if (want < UI_SPLASH_MIN_MS) want = UI_SPLASH_MIN_MS;
        if (pending_task) want = el > UI_SPLASH_TASK_MS ? el : UI_SPLASH_TASK_MS;  /* задача важнее заставки */
        if (boot_skip) want = el;
        if (want < el + 250) want = el + 250;                                       /* короткое затухание, а не обрыв */
        if (want < splash_end) {                                                    /* конец только приближается */
            uint32_t left = splash_end > el ? splash_end - el : 0;
            if (want - el < 450 && left > 450) splash_fade = want - el;           /* затухание начинается с полной яркости */
            splash_end = want;
        }
        if (el >= splash_end) {
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
