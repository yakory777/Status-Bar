#pragma once
/*
 * Уменьшение кадра интерфейса 536×240 до меньшего экрана с усреднением (box filter):
 * текст и линии остаются гладкими. Чистый C без зависимостей — проверяется и на ПК.
 */
#include <stdint.h>

typedef struct {
    int src_w, src_h, out_w, out_h;
    uint16_t *xs, *ys;          /* границы ячеек: ячейка i = [xs[i], xs[i+1]) в исходнике */
    uint16_t *cell_x, *cell_y;  /* исходный пиксель → номер ячейки */
} scale_t;

/* Память под таблицы выделяет вызывающий: xs[out_w+1], ys[out_h+1], cell_x[src_w], cell_y[src_h] */
void scale_init(scale_t *s);

/* Какие пиксели результата затрагивает изменённый прямоугольник исходника (включительно) */
void scale_area(const scale_t *s, int x1, int y1, int x2, int y2,
                int *ox1, int *oy1, int *ox2, int *oy2);

/*
 * Посчитать строки результата [oy, oy + rows) и столбцы [ox1, ox2] из исходного кадра src
 * (RGB565, порядок байт процессора). out — подряд, по (ox2 - ox1 + 1) пикселей в строке;
 * swap — переставить байты (для панелей, которые ждут big-endian).
 */
void scale_rows(const scale_t *s, const uint16_t *src, int ox1, int ox2, int oy, int rows,
                uint16_t *out, int swap);
