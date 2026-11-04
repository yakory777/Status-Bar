#include "display_scale.h"

void scale_init(scale_t *s)
{
    for (int i = 0; i <= s->out_w; i++) s->xs[i] = (uint16_t)((long)i * s->src_w / s->out_w);
    for (int i = 0; i <= s->out_h; i++) s->ys[i] = (uint16_t)((long)i * s->src_h / s->out_h);
    for (int i = 0; i < s->out_w; i++)
        for (int x = s->xs[i]; x < s->xs[i + 1]; x++) s->cell_x[x] = (uint16_t)i;
    for (int i = 0; i < s->out_h; i++)
        for (int y = s->ys[i]; y < s->ys[i + 1]; y++) s->cell_y[y] = (uint16_t)i;
}

static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

void scale_area(const scale_t *s, int x1, int y1, int x2, int y2,
                int *ox1, int *oy1, int *ox2, int *oy2)
{
    *ox1 = s->cell_x[clampi(x1, 0, s->src_w - 1)];
    *ox2 = s->cell_x[clampi(x2, 0, s->src_w - 1)];
    *oy1 = s->cell_y[clampi(y1, 0, s->src_h - 1)];
    *oy2 = s->cell_y[clampi(y2, 0, s->src_h - 1)];
}

/*
 * Ячейка при уменьшении 536→320 и 240→143 — это 1 или 2 пикселя по каждой оси, то есть 1, 2 или 4
 * пикселя, и делить можно сдвигом. Каналы складываются «в одном слове»: RGB565 раскладывается
 * в 32 бита с промежутками (G — в старшие биты), так что сумма до 4 пикселей не переполняет поля.
 */
static inline uint32_t spread(uint16_t p) { return (p & 0xF81Fu) | ((uint32_t)(p & 0x07E0u) << 16); }

void scale_rows(const scale_t *s, const uint16_t *src, int ox1, int ox2, int oy, int rows,
                uint16_t *out, int swap)
{
    for (int r = 0; r < rows; r++) {
        int y0 = s->ys[oy + r], h = s->ys[oy + r + 1] - y0;
        const uint16_t *row0 = src + (long)y0 * s->src_w;
        const uint16_t *row1 = h > 1 ? row0 + s->src_w : 0;
        for (int ox = ox1; ox <= ox2; ox++) {
            int x0 = s->xs[ox], w = s->xs[ox + 1] - x0;
            uint32_t sum = spread(row0[x0]);
            if (w > 1) sum += spread(row0[x0 + 1]);
            if (row1) {
                sum += spread(row1[x0]);
                if (w > 1) sum += spread(row1[x0 + 1]);
            }
            int sh = (w > 1) + (h > 1);                 /* 1, 2 или 4 пикселя → сдвиг 0, 1, 2 */
            if (sh) {
                uint32_t half = 1u << (sh - 1);
                sum = (sum + (half | half << 11 | half << 21)) >> sh;
            }
            uint16_t v = (uint16_t)((sum & 0xF81Fu) | ((sum >> 16) & 0x07E0u));
            *out++ = swap ? (uint16_t)(v >> 8 | v << 8) : v;
        }
    }
}
