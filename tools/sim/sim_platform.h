#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

uint8_t sim_brightness(void);
int sim_beeps(void);
void sim_set_battery(bool present, int pct, bool charging);
void sim_set_wifi(int level);
void sim_set_tx_log(FILE *f);
