#include <stdint.h>
#include "lvgl.h"
#include "platform.h"
#include "ui_sound.h"

typedef struct { uint16_t hz, ms; } note_t;

/* Мелодии: частота, длительность; hz = 0 — пауза */
static const note_t WAIT[]    = { {1760, 70}, {0, 80}, {1760, 70}, {0, 0} };
static const note_t DONE[]    = { {1175, 70}, {1480, 70}, {1976, 120}, {0, 0} };
static const note_t ERROR_[]  = { {392, 180}, {0, 60}, {330, 220}, {0, 0} };
static const note_t CLICK[]   = { {2400, 15}, {0, 0} };
static const note_t APPROVE[] = { {1568, 60}, {2093, 110}, {0, 0} };
static const note_t DENY[]    = { {659, 90}, {440, 140}, {0, 0} };

static const note_t *seq;
static int pos;
static uint32_t note_t0;
static bool muted;

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    if (!seq) return;
    if (lv_tick_elaps(note_t0) < seq[pos].ms) return;
    pos++;
    if (seq[pos].ms == 0) {              /* конец мелодии */
        platform_tone(0);
        seq = NULL;
        return;
    }
    platform_tone(seq[pos].hz);
    note_t0 = lv_tick_get();
}

void ui_sound_init(void)
{
    lv_timer_create(tick_cb, 5, NULL);
}

void ui_sound_play(ui_sound_t s)
{
    if (muted) return;
    static const note_t *const ALL[] = { WAIT, DONE, ERROR_, CLICK, APPROVE, DENY };
    seq = ALL[s];
    pos = 0;
    note_t0 = lv_tick_get();
    platform_tone(seq[0].hz);
}

void ui_sound_set_muted(bool m)
{
    muted = m;
    if (m) {
        seq = NULL;
        platform_tone(0);
    }
}

bool ui_sound_muted(void) { return muted; }
