#pragma once
/*
 * Сцены ожидания «Ready to work». Эталон движения — скрипты в tools/:
 *   robot  — render_idle_robot.py   (тема Claude)
 *   cursor — render_idle_cursor.py  (обе темы)
 *   typist — render_idle_typist.py  (тема Codex)
 */
#include <stdbool.h>
#include "lvgl.h"
#include "ui_status.h"

void ui_scene_create(lv_obj_t *parent);

/* Запустить сцену с начала. Неизвестное имя — сцена темы по умолчанию. */
void ui_scene_start(ui_theme_t theme, const char *name);

/* Маскот прыгает за кадр, сцена гаснет; по окончании вызывается done. */
void ui_scene_exit(void (*done)(void));

/* Сон: 0 — бодрствует, 1 — спит (глаза закрыты, «z z z»). */
void ui_scene_set_sleep(bool asleep);

/* Остановить сцену и скрыть (экран выключен). */
void ui_scene_stop(void);

bool ui_scene_visible(void);
/* 0..1 — насколько финал сцены (маскот во весь экран, заливка) закрывает экран */
float ui_scene_cover(void);
const char *ui_scene_name(void);
