#include <stdio.h>
#include <string.h>
#include "lvgl.h"
#include "platform.h"
<<<<<<< HEAD
#include "ui_i18n.h"
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
#include "ui_icons.h"
#include "ui_input.h"
#include "ui_screen.h"
#include "ui_sound.h"
#include "ui_status.h"

static bool down;
static bool long_fired;        /* долгое нажатие уже сработало в этом удержании */
static bool woke;              /* это нажатие только разбудило экран */
static uint32_t down_t;
static int clicks;
static uint32_t last_up_t;

static void send_button(const char *what, const char *extra)
{
    char line[96];
    snprintf(line, sizeof line, "{\"button\":\"%s\"%s}", what, extra ? extra : "");
    platform_send_line(line);
}

static void next_scene(void)
{
    const char *cur = ui_status_get_idle_scene();
    const char *next;
    if (ui_status_get_theme() == THEME_CODEX)
        next = strcmp(cur, "typist") ? "typist" : "cursor";
    else
        next = strcmp(cur, "cursor") ? "cursor" : "robot";
    ui_status_set_idle_scene(next);              /* сразу на экране, хост запомнит выбор */
    ui_screen_on_state(ui_status_get_state(), false);
    char extra[48];
    snprintf(extra, sizeof extra, ",\"scene\":\"%s\"", next);
    send_button("scene_next", extra);
<<<<<<< HEAD
    char title[48];
    snprintf(title, sizeof title, tr(TR_SCENE), tr_scene_name(next));
=======
    const char *title = !strcmp(next, "robot") ? "Сцена: робот"
                      : !strcmp(next, "typist") ? "Сцена: машинистка" : "Сцена: курсор";
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    ui_screen_toast(title, ui_status_text_color(1));
}

static void on_short(void)
{
    if (ui_status_approve_pending()) {
        send_button("deny", NULL);
        ui_status_set_approve(false);
        ui_sound_play(SND_DENY);
<<<<<<< HEAD
        ui_screen_toast(tr(TR_DENIED), ui_status_state_color(ST_ERROR));
=======
        ui_screen_toast("Отклонено", ui_status_state_color(ST_ERROR));
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        return;
    }
    ui_sound_play(SND_CLICK);
    ui_screen_toggle();
}

static void on_long(void)
{
    if (ui_status_approve_pending()) {
        send_button("approve", NULL);
        ui_status_set_approve(false);
        ui_sound_play(SND_APPROVE);
<<<<<<< HEAD
        ui_screen_toast(tr(TR_ALLOWED), ui_status_state_color(ST_DONE));
=======
        ui_screen_toast("Разрешено", ui_status_state_color(ST_DONE));
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        return;
    }
    bool m = !ui_sound_muted();
    ui_sound_set_muted(m);
    ui_icons_refresh();
    if (!m) ui_sound_play(SND_CLICK);
<<<<<<< HEAD
    ui_screen_toast(tr(m ? TR_SOUND_OFF : TR_SOUND_ON), ui_status_text_color(1));
=======
    ui_screen_toast(m ? "Звук выключен" : "Звук включён", ui_status_text_color(1));
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
}

static void tick_cb(lv_timer_t *t)
{
    (void)t;
    if (down) {
        uint32_t held = lv_tick_elaps(down_t);
        if (ui_status_approve_pending() && !woke)
            ui_status_approve_hold((float)held / UI_LONG_PRESS_MS);
        if (!long_fired && !woke && held >= UI_LONG_PRESS_MS) {
            long_fired = true;
            clicks = 0;
            on_long();
        }
        return;
    }
    if (clicks && lv_tick_elaps(last_up_t) >= UI_DOUBLE_CLICK_MS) {
        if (clicks >= 2) next_scene();
        else on_short();
        clicks = 0;
    }
}

void ui_input_button(bool pressed)
{
    if (pressed == down) return;
    down = pressed;
    if (pressed) {
        down_t = lv_tick_get();
        long_fired = false;
        woke = ui_screen_wake();                 /* спал или был выключен — только будим */
        return;
    }
    ui_status_approve_hold(0);
    if (woke || long_fired) return;
    clicks++;
    last_up_t = lv_tick_get();
    /* в режиме решения не ждём второго нажатия — отклоняем сразу */
    if (ui_status_approve_pending() && clicks == 1) {
        clicks = 0;
        on_short();
    }
}

void ui_input_init(void)
{
    lv_timer_create(tick_cb, 10, NULL);
}
