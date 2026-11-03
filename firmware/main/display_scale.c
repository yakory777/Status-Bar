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

void scale_rows(const scale_t *s, const uint16_t *src, int ox1, int ox2, int oy, int rows,
                uint16_t *out, int swap)
{
    for (int r = 0; r < rows; r++) {
        int y0 = s->ys[oy + r], y1 = s->ys[oy + r + 1];
        for (int ox = ox1; ox <= ox2; ox++) {
            int x0 = s->xs[ox], x1 = s->xs[ox + 1];
            unsigned rs = 0, gs = 0, bs = 0, n = 0;
            for (int y = y0; y < y1; y++) {
                const uint16_t *p = src + (long)y * s->src_w + x0;
                for (int x = x0; x < x1; x++, p++) {
                    rs += *p >> 11;
                    gs += (*p >> 5) & 0x3F;
                    bs += *p & 0x1F;
                    n++;
                }
            }
            uint16_t v = (uint16_t)(((rs + n / 2) / n) << 11 | ((gs + n / 2) / n) << 5 | ((bs + n / 2) / n));
            *out++ = swap ? (uint16_t)(v >> 8 | v << 8) : v;
        }
    }
}
