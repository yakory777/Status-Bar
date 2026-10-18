/*
 * Платформа симулятора: яркость затемняет кадры, батарею, Wi-Fi и пищалку
 * задаёт сценарий строками {"sim":{...}} (см. sim_main.c).
 */
#include <stdio.h>
#include "platform.h"
#include "sim_platform.h"

static uint8_t brightness = 0xD0;
static platform_battery_t battery = { .present = false, .pct = 100, .charging = false, .mv = 0 };
static int wifi = -1;
static int beeps;
static FILE *tx_log;

void platform_set_brightness(uint8_t level) { brightness = level; }
platform_battery_t platform_battery(void) { return battery; }
int platform_wifi_level(void) { return wifi; }
void platform_tone(uint16_t hz) { if (hz) beeps++; }

void platform_send_line(const char *json)
{
    fprintf(tx_log ? tx_log : stderr, "[tx] %s\n", json);   /* что плата отправила бы хосту */
    if (tx_log) fflush(tx_log);
}

void sim_set_tx_log(FILE *f) { tx_log = f; }

uint8_t sim_brightness(void) { return brightness; }
int sim_beeps(void) { return beeps; }

void sim_set_battery(bool present, int pct, bool charging)
{
    battery.present = present;
    battery.pct = pct;
    battery.charging = charging;
    battery.mv = present ? 3300 + pct * 9 : 0;
}

void sim_set_wifi(int level) { wifi = level; }
