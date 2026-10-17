#pragma once
/*
 * Короткие звуки на пассивной пищалке: «ждёт вас», «готово», «ошибка».
 * Без пищалки (BUZZER_GPIO = -1) ничего не звучит; на плату это не влияет.
 */
#include <stdbool.h>

typedef enum { SND_WAIT, SND_DONE, SND_ERROR, SND_CLICK, SND_APPROVE, SND_DENY } ui_sound_t;

void ui_sound_init(void);
void ui_sound_play(ui_sound_t s);
void ui_sound_set_muted(bool muted);
bool ui_sound_muted(void);
