#pragma once
/*
 * То, что зависит от железа. На плате — platform_esp.c, в симуляторе — tools/sim/sim_platform.c.
 * Интерфейс (ui_*.c) вызывает только эти функции и не знает, где он запущен.
 */
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool present;      /* аккумулятор подключён */
    int  pct;          /* 0..100 */
    bool charging;     /* идёт зарядка от USB */
    int  mv;           /* напряжение, мВ (для отладки) */
} platform_battery_t;

/* Яркость экрана 0..255; 0 — экран выключен. */
void platform_set_brightness(uint8_t level);

/* Заряд батареи. Можно звать часто: значение кешируется и сглаживается. */
platform_battery_t platform_battery(void);

/* Уровень Wi-Fi: -1 — режим Wi-Fi выключен (плата на USB), 0..3 — полоски. */
int platform_wifi_level(void);

/* Пищалка: включить тон, Гц; 0 — тишина. Не блокирует — длительность ведёт ui_sound.c. */
void platform_tone(uint16_t hz);

/* Отправить хосту строку JSON (без перевода строки — добавится сам). */
void platform_send_line(const char *json);
