/*
 * Настройки LVGL для симулятора. Совпадают с firmware/sdkconfig.defaults
 * по всему, что влияет на картинку; остальное — значения LVGL по умолчанию.
 */
#ifndef LV_CONF_H
#define LV_CONF_H

#define LV_COLOR_DEPTH            16
#define LV_USE_STDLIB_MALLOC      LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING      LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF     LV_STDLIB_CLIB
#define LV_DEF_REFR_PERIOD        16
#define LV_USE_OS                 LV_OS_NONE

#define LV_USE_TINY_TTF           1
#define LV_TINY_TTF_FILE_SUPPORT  0
#define LV_TINY_TTF_CACHE_GLYPH_CNT 256

#define LV_FONT_MONTSERRAT_14     1
#define LV_USE_LOG                1
#define LV_LOG_LEVEL              LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF             1

#define LV_BUILD_EXAMPLES         0
#define LV_USE_DEMO_WIDGETS       0

#endif
