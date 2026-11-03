#pragma once
/*
 * Диспетчер экранов: заставка → сцена ожидания ⇄ экран задачи, празднование,
 * сон, выключение экрана, экран сопряжения. Решает, что сейчас на дисплее.
 */
#include <stdbool.h>
#include <stdint.h>
#include "ui_status.h"

#define UI_BRIGHT_ON        0xD0
#define UI_BRIGHT_SLEEP     0x30
#define UI_SPLASH_MS        2200
#define UI_DONE_TO_IDLE_MS  (90 * 1000)        /* «Готово» висит полторы минуты, потом сцена ожидания */
#define UI_SLEEP_AFTER_MS   (10 * 60 * 1000)   /* без событий 10 мин — маскот засыпает, экран тускнеет */
#define UI_OFF_AFTER_MS     (30 * 60 * 1000)   /* 30 мин — экран гаснет совсем (AMOLED не выгорает) */

/* После ui_status_create(). */
void ui_screen_init(void);

/* Новое сообщение от хоста уже применено к экрану задачи: решить, что показывать. */
void ui_screen_on_state(status_state_t st, bool activity);

/* Экран сопряжения с кодом; NULL или "" — скрыть. */
void ui_screen_pairing(const char *code);

/* Разбудить экран (кнопка, касание). true — экран спал или был выключен. */
bool ui_screen_wake(void);

/* Принудительно показать сцену ожидания / экран задачи (кнопка). */
void ui_screen_toggle(void);

bool ui_screen_is_off(void);

/* Короткое сообщение внизу экрана на полторы секунды («Разрешено», «Звук выключен»). */
void ui_screen_toast(const char *text, lv_color_t color);
