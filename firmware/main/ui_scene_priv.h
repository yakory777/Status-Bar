#pragma once
/* Внутренний интерфейс сцен: каждая сцена — набор функций, менеджер в ui_scene.c. */
#include <stdbool.h>
#include "ui_draw.h"
#include "ui_status.h"

/* Что менеджер передаёт сцене на каждом кадре */
typedef struct {
    float t;            /* время сцены, с (во сне и при уходе — заморожено) */
    float exit_p;       /* 0..1 — маскот уходит за кадр; 0 — нет */
    bool asleep;
    float sleep_t;      /* сколько спит, с — для «z z z» и дыхания */
} scene_frame_t;

typedef struct {
    const char *name;
    void (*begin)(ui_theme_t theme);    /* шрифты, раскладка, таймлайн */
    void (*end)(void);                  /* освободить шрифты */
    float (*length)(void);              /* длина цикла, с */
    float (*rest_time)(void);           /* момент, где маскот спокойно стоит (для сна) */
    void (*draw)(dctx_t *d, const scene_frame_t *f);
} scene_def_t;

extern const scene_def_t SCENE_ROBOT, SCENE_CURSOR, SCENE_TYPIST;

/* Насколько маскот/заливка закрывают экран (0..1) — индикаторы на это время прячутся */
extern float scene_cover;

/* Общее для сцен */
const void *scene_font_data(const char *which, size_t *size);   /* "lora" | "mono" | "sans" */
lv_font_t *scene_font(const char *which, int px);

/* «z z z» над головой спящего маскота */
void scene_draw_zzz(dctx_t *d, float x, float y, float sleep_t, lv_color_t c);

/* Маскот уходит: присед, затем прыжок вверх за кадр. Меняет позу на месте. */
void scene_exit_pose(float exit_p, float *y, float *sx, float *sy);
