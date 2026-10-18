#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "lvgl.h"

typedef enum {
    ST_IDLE,     /* серый: ждём задачу                 */
    ST_START,    /* задача только пришла               */
    ST_WORK,     /* в процессе                         */
    ST_WAIT,     /* нужно подтверждение                */
    ST_DONE,     /* готово                             */
    ST_ERROR,    /* инструмент упал или задача прервана */
    ST_COMPACT,  /* агент сжимает контекст             */
    ST_COUNT
} status_state_t;

typedef enum { THEME_CLAUDE, THEME_CODEX, THEME_COUNT } ui_theme_t;

void ui_status_create(void);

/* title/step = NULL — оставить прежний текст */
/* Задача закончилась, экран уходит к сцене ожидания: состояние становится idle,
 * а картинка остаётся последней задачей (её и покажет кнопка), без «Жду задачу» на полсекунды. */
void ui_status_park(void);

<<<<<<< HEAD
/* Язык подписей: "en" | "ru". Перерисовывает уже показанные подписи. */
void ui_status_set_language(const char *code);

=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
void ui_status_apply(status_state_t st, const char *title, const char *step,
                     int done, int total);

status_state_t ui_status_parse_state(const char *s);
status_state_t ui_status_get_state(void);
bool ui_status_is_active(status_state_t s);

/* Тема экрана по агенту: "claude" | "codex". */
void ui_status_set_theme(const char *agent);
ui_theme_t ui_status_get_theme(void);

/* Сцена ожидания для текущей темы (см. host/scenes.py). */
void ui_status_set_idle_scene(const char *scene);
const char *ui_status_get_idle_scene(void);

/* Счётчики-бейджи: активные субагенты и другие активные сессии. */
void ui_status_set_counters(int subagents, int other_sessions);

/* Связь с хостом: online=true при каждом сообщении, false — когда хост замолчал. */
void ui_status_link(bool online, uint32_t now_ms);
bool ui_status_link_ok(void);

/* Для диспетчера экранов */
lv_obj_t *ui_status_root(void);
const lv_font_t *ui_status_font(int which);        /* 0 — 18 px, 1 — 27 px жирный, 2 — 40 px жирный */
lv_color_t ui_status_state_color(status_state_t s);  /* цвет состояния в текущей теме */
lv_color_t ui_status_text_color(int which);          /* 0 — текст, 1 — серый, 2 — пустой сегмент */
void ui_status_set_right_inset(int32_t px);          /* место справа под индикаторы */

/* Решение кнопкой: хост ждёт «разрешить/отклонить» с платы (поле approve). */
void ui_status_set_approve(bool on);
bool ui_status_approve_pending(void);
void ui_status_approve_hold(float progress);         /* 0..1 — полоса удержания кнопки */

/* Через сколько ожидания подтверждения напоминание становится настойчивее. */
#define UI_WAIT_ESCALATE_MS (60 * 1000)
