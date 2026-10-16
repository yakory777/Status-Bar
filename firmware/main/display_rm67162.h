#pragma once
#include <stdint.h>
#include "lvgl.h"

#define LCD_W 536
#define LCD_H 240

/* Инициализирует QSPI, панель RM67162 и создаёт LVGL-дисплей */
lv_display_t *display_init(void);

/* Яркость AMOLED 0..255 */
void display_set_brightness(uint8_t level);
