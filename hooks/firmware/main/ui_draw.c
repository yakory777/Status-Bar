#include <math.h>
#include <string.h>
#include "ui_draw.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

dctx_t dctx_from_event(lv_event_t *e)
{
    lv_obj_t *o = lv_event_get_target(e);
    lv_area_t a;
    lv_obj_get_coords(o, &a);
    dctx_t d = { lv_event_get_layer(e), a.x1, a.y1 };
    return d;
}

float clampf(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
float clamp01(float x) { return clampf(x, 0.0f, 1.0f); }
float lerpf(float a, float b, float t) { return a + (b - a) * t; }
float ease_in(float t) { return t * t; }
float ease_out_q(float t) { return 1.0f - (1.0f - t) * (1.0f - t); }
float springf(float t, float freq, float damp)
{
    return expf(-damp * t) * cosf(2.0f * (float)M_PI * freq * t);
}

lv_color_t c_hex(uint32_t rgb) { return lv_color_hex(rgb); }

lv_color_t c_mix(lv_color_t a, lv_color_t b, float t)
{
    t = clamp01(t);
    return lv_color_make((uint8_t)lroundf(lerpf(a.red, b.red, t)),
                         (uint8_t)lroundf(lerpf(a.green, b.green, t)),
                         (uint8_t)lroundf(lerpf(a.blue, b.blue, t)));
}

lv_color_t c_dim(lv_color_t c, float k)
{
    k = clamp01(k);
    return lv_color_make((uint8_t)(c.red * k), (uint8_t)(c.green * k), (uint8_t)(c.blue * k));
}

static int32_t ri(float v) { return (int32_t)lroundf(v); }

void d_rect(dctx_t *d, float x0, float y0, float x1, float y1, lv_color_t c, lv_opa_t opa, int32_t radius)
{
    if (opa <= LV_OPA_MIN) return;
    lv_area_t a = { d->ox + ri(x0), d->oy + ri(y0), d->ox + ri(x1) - 1, d->oy + ri(y1) - 1 };
    if (a.x2 < a.x1 || a.y2 < a.y1) return;
    lv_draw_rect_dsc_t r;
    lv_draw_rect_dsc_init(&r);
    r.bg_color = c;
    r.bg_opa = opa;
    r.radius = radius;
    lv_draw_rect(d->layer, &r, &a);
}

void d_circle(dctx_t *d, float cx, float cy, float rad, lv_color_t c, lv_opa_t opa)
{
    d_rect(d, cx - rad, cy - rad, cx + rad, cy + rad, c, opa, LV_RADIUS_CIRCLE);
}

void d_fill(dctx_t *d, lv_color_t c)
{
    d_rect(d, 0, 0, UI_W, UI_H, c, LV_OPA_COVER, 0);
}

float text_w_n(const lv_font_t *f, const char *txt, uint32_t bytes)
{
    return (float)lv_text_get_width(txt, bytes, f, 0);
}

float text_w(const lv_font_t *f, const char *txt) { return text_w_n(f, txt, (uint32_t)strlen(txt)); }

float cap_height(const lv_font_t *f)
{
    lv_font_glyph_dsc_t g;
    if (!lv_font_get_glyph_dsc(f, &g, 'R', 0)) return (float)f->line_height * 0.7f;
    return (float)(g.box_h + g.ofs_y);
}

float d_text(dctx_t *d, const lv_font_t *f, const char *txt, float x, float baseline,
             lv_color_t c, lv_opa_t opa)
{
    float w = text_w(f, txt);
    if (opa <= LV_OPA_MIN) return w;
    int32_t top = ri(baseline) - (f->line_height - f->base_line);
    lv_area_t a = { d->ox + ri(x), d->oy + top, d->ox + ri(x + w) + 2, d->oy + top + f->line_height - 1 };
    lv_draw_label_dsc_t l;
    lv_draw_label_dsc_init(&l);
    l.font = f;
    l.color = c;
    l.opa = opa;
    l.text = txt;
    l.text_local = 1;           /* текст может лежать во временном буфере */
    lv_draw_label(d->layer, &l, &a);
    return w;
}

void d_text_squash(dctx_t *d, const lv_font_t *f, const char *txt, float x, float baseline,
                   lv_color_t c, float scale_y)
{
    if (scale_y >= 0.98f) {
        d_text(d, f, txt, x, baseline, c, LV_OPA_COVER);
        return;
    }
    /* Рисуем букву в слой и выводим его со сжатием по вертикали к базовой линии */
    float w = text_w(f, txt);
    int32_t lh = f->line_height;
    int32_t top = ri(baseline) - (lh - f->base_line);
    lv_area_t area = { d->ox + ri(x), d->oy + top, d->ox + ri(x + w) + 2, d->oy + top + lh - 1 };
    lv_layer_t *child = lv_draw_layer_create(d->layer, LV_COLOR_FORMAT_ARGB8888, &area);
    if (!child) return;
    lv_draw_label_dsc_t l;
    lv_draw_label_dsc_init(&l);
    l.font = f;
    l.color = c;
    l.text = txt;
    l.text_local = 1;
    lv_draw_label(child, &l, &area);

    lv_draw_image_dsc_t img;
    lv_draw_image_dsc_init(&img);
    img.src = child;
    img.scale_x = LV_SCALE_NONE;
    img.scale_y = (int32_t)(LV_SCALE_NONE * clampf(scale_y, 0.05f, 1.0f));
    img.pivot.x = 0;
    img.pivot.y = lh - (lh - f->base_line);   /* сжимаем к базовой линии */
    lv_draw_layer(d->layer, &img, &area);
}

void d_sprite(dctx_t *d, const uint8_t *grid, int w, int h, const lv_color_t *pal,
              float x0, float y0, float bw, float bh, lv_opa_t opa)
{
    float pw = bw / w, ph = bh / h;
    for (int y = 0; y < h; y++) {
        int x = 0;
        while (x < w) {
            uint8_t idx = grid[y * w + x];
            int run = 1;
            while (x + run < w && grid[y * w + x + run] == idx) run++;
            if (idx)
                d_rect(d, x0 + x * pw, y0 + y * ph, x0 + (x + run) * pw, y0 + (y + 1) * ph,
                       pal[idx], opa, 0);
            x += run;
        }
    }
}

void d_arc(dctx_t *d, float cx, float cy, float r, float width, int32_t a0, int32_t a1,
           lv_color_t c, lv_opa_t opa)
{
    if (opa <= LV_OPA_MIN) return;
    lv_draw_arc_dsc_t a;
    lv_draw_arc_dsc_init(&a);
    a.color = c;
    a.opa = opa;
    a.width = ri(width);
    a.radius = (uint16_t)ri(r);
    a.start_angle = a0;
    a.end_angle = a1;
    a.rounded = 1;
    a.center.x = d->ox + ri(cx);
    a.center.y = d->oy + ri(cy);
    lv_draw_arc(d->layer, &a);
}

void d_line(dctx_t *d, float x0, float y0, float x1, float y1, float width, lv_color_t c, lv_opa_t opa)
{
    if (opa <= LV_OPA_MIN) return;
    lv_draw_line_dsc_t l;
    lv_draw_line_dsc_init(&l);
    l.color = c;
    l.opa = opa;
    l.width = ri(width);
    l.round_start = l.round_end = 1;
    l.p1.x = d->ox + x0; l.p1.y = d->oy + y0;
    l.p2.x = d->ox + x1; l.p2.y = d->oy + y1;
    lv_draw_line(d->layer, &l);
}
