#pragma once
/*
 * Подписи на экране на двух языках. Язык по умолчанию — CONFIG_ASB_LANGUAGE
 * (menuconfig → Agent Status Bar), хост меняет его полем "lang" ("en" | "ru").
 * Шаги и заголовки задач переводит хост (host/i18n.py), здесь — только то, что рисует плата.
 */
#include <stdbool.h>

typedef enum { LANG_EN, LANG_RU, LANG_COUNT } ui_lang_t;

typedef enum {
    TR_ST_IDLE, TR_ST_START, TR_ST_WORK, TR_ST_WAIT, TR_ST_DONE, TR_ST_ERROR, TR_ST_COMPACT,
    TR_WAIT_MIN,        /* "%s · %d min" */
    TR_TASKS_DONE,
    TR_LINK_LOST,
    TR_APPROVE_HINT,
    TR_IDLE_TITLE, TR_IDLE_STEP,
    TR_ALLOWED, TR_DENIED,
    TR_SOUND_OFF, TR_SOUND_ON,
    TR_SCENE,           /* "Scene: %s" */
    TR_SCENE_ROBOT, TR_SCENE_CURSOR, TR_SCENE_TYPIST,
    TR_PAIR_TITLE, TR_PAIR_HINT1, TR_PAIR_HINT2,
    TR_COUNT
} tr_id_t;

const char *tr(tr_id_t id);

/* "+1 session" / "+3 сессии" — с правильным склонением */
void tr_sessions(char *buf, unsigned size, int n);

/* Название сцены ожидания для подсказки: robot → «робот» */
const char *tr_scene_name(const char *scene);

ui_lang_t ui_i18n_get(void);
/* true — язык поменялся (экран надо перерисовать) */
bool ui_i18n_set(ui_lang_t lang);
/* "en" | "ru" → язык; что-то другое — false */
bool ui_i18n_set_code(const char *code);
