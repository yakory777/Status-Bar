#pragma once
/*
 * Экран платы. Интерфейс всегда рисуется в 536×240 (UI_W × UI_H); драйвер выбранной платы
 * (menuconfig → Agent Status Bar → Board) выводит его на свою панель:
 *   display_rm67162.c — T-Display-S3 AMOLED 1.91″, 536×240, как есть;
 *   display_st7789.c  — T-Display-S3 LCD 1.9″, 320×170, уменьшая кадр (display_scale.c).
 */
#include <stdint.h>
#include "lvgl.h"

/* Создаёт LVGL-дисплей 536×240 поверх панели выбранной платы */
lv_display_t *display_init(void);

/* Яркость 0..255: на AMOLED — команда панели, на LCD — подсветка (ШИМ) */
void display_set_brightness(uint8_t level);
