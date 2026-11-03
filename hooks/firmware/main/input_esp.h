#pragma once
/* Запустить опрос кнопок. lock/unlock — замок UI из main.c (LVGL не потокобезопасен). */
void input_esp_start(void (*lock)(void), void (*unlock)(void));
