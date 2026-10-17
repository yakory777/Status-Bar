#pragma once
/*
 * Помощники рисования для сцен и индикаторов: координаты во float (как в эталонных
 * скриптах tools/), кривые анимации, пиксельные спрайты, буквы по базовой линии.
 */
#include <stdbool.h>
#include <stdint.h>
#include "lvgl.h"

#define UI_W 536
#define UI_H 240

typedef struct {
    lv_layer_t *layer;
    int32_t ox, oy;          /* начало координат объекта на экране */
} dctx_t;

/* Контекст рисования из события LV_EVENT_DRAW_MAIN объекта */
dctx_t dctx_from_event(lv_event_t *e);

/* ---------- кривые ---------- */
float clampf(float x, float a, float b);
float clamp01(float x);
float lerpf(float a, float b, float t);
float ease_in(float t);
float ease_out_q(float t);
float springf(float t, float freq, float damp);

/* ---------- цвет ---------- */
lv_color_t c_hex(uint32_t rgb);
lv_color_t c_mix(lv_color_t a, lv_color_t b, float t);      /* t=0 → a, t=1 → b */
lv_color_t c_dim(lv_color_t c, float k);                     /* на чёрном фоне: прозрачность = затемнение */

/* ---------- примитивы (x1, y1 — не включительно, как в PIL) ---------- */
void d_rect(dctx_t *d, float x0, float y0, float x1, float y1, lv_color_t c, lv_opa_t opa, int32_t radius);
void d_circle(dctx_t *d, float cx, float cy, float r, lv_color_t c, lv_opa_t opa);
void d_fill(dctx_t *d, lv_color_t c);
/* Дуга: углы в градусах по часовой от оси +x (как в LVGL), концы скруглены. */
void d_arc(dctx_t *d, float cx, float cy, float r, float width, int32_t a0, int32_t a1,
           lv_color_t c, lv_opa_t opa);
void d_line(dctx_t *d, float x0, float y0, float x1, float y1, float width, lv_color_t c, lv_opa_t opa);

/* Текст: x — левый край, baseline — базовая линия. Возвращает ширину. */
float d_text(dctx_t *d, const lv_font_t *f, const char *txt, float x, float baseline,
             lv_color_t c, lv_opa_t opa);
/* Буква, сжатая по вертикали к базовой линии (эффект «впечатывания»), scale_y 0..1. */
void d_text_squash(dctx_t *d, const lv_font_t *f, const char *txt, float x, float baseline,
                   lv_color_t c, float scale_y);
float text_w(const lv_font_t *f, const char *txt);
float text_w_n(const lv_font_t *f, const char *txt, uint32_t bytes);
float cap_height(const lv_font_t *f);

/*
 * Пиксельный спрайт: grid[y*w + x] — индекс палитры, 0 — прозрачно.
 * Растягивается до bw×bh с левым верхним углом (x0, y0), без сглаживания.
 */
void d_sprite(dctx_t *d, const uint8_t *grid, int w, int h, const lv_color_t *pal,
              float x0, float y0, float bw, float bh, lv_opa_t opa);
