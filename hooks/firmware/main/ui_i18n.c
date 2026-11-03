#include <stdio.h>
#include <string.h>
#include "ui_i18n.h"

#if __has_include("sdkconfig.h")
#include "sdkconfig.h"
#endif
#ifndef CONFIG_ASB_LANGUAGE
#define CONFIG_ASB_LANGUAGE "en"
#endif

static const char *const TEXT[TR_COUNT][LANG_COUNT] = {
    [TR_ST_IDLE]      = { "Idle",          "Ожидание" },
    [TR_ST_START]     = { "Start",         "Старт" },
    [TR_ST_WORK]      = { "Working",       "В работе" },
    [TR_ST_WAIT]      = { "Needs you",     "Ждёт вас" },
    [TR_ST_DONE]      = { "Done",          "Готово" },
    [TR_ST_ERROR]     = { "Error",         "Ошибка" },
    [TR_ST_COMPACT]   = { "Compacting",    "Сжатие" },
    [TR_WAIT_MIN]     = { "%s · %d min",   "%s · %d мин" },
    [TR_TASKS_DONE]   = { "tasks done",    "задач готово" },
    [TR_LINK_LOST]    = { "No connection to the computer", "Нет связи с компьютером" },
    [TR_APPROVE_HINT] = { "Hold — allow · tap — deny", "Удержать — разрешить · нажать — отклонить" },
    [TR_IDLE_TITLE]   = { "Waiting for a task", "Жду задачу" },
    [TR_IDLE_STEP]    = { "Send a task to the agent", "Отправьте задачу агенту" },
    [TR_ALLOWED]      = { "Allowed",       "Разрешено" },
    [TR_DENIED]       = { "Denied",        "Отклонено" },
    [TR_SOUND_OFF]    = { "Sound off",     "Звук выключен" },
    [TR_SOUND_ON]     = { "Sound on",      "Звук включён" },
    [TR_SCENE]        = { "Scene: %s",     "Сцена: %s" },
    [TR_SCENE_ROBOT]  = { "robot",         "робот" },
    [TR_SCENE_CURSOR] = { "cursor",        "курсор" },
    [TR_SCENE_TYPIST] = { "typist",        "машинистка" },
    [TR_PAIR_TITLE]   = { "Wi-Fi pairing", "Сопряжение по Wi-Fi" },
    [TR_PAIR_HINT1]   = { "Check that this code matches", "Проверьте, что код совпадает" },
    [TR_PAIR_HINT2]   = { "the one on your computer", "с кодом на компьютере" },
};

static ui_lang_t lang = (CONFIG_ASB_LANGUAGE[0] == 'r') ? LANG_RU : LANG_EN;

const char *tr(tr_id_t id)
{
    if ((unsigned)id >= TR_COUNT) return "";
    const char *s = TEXT[id][lang];
    return s ? s : TEXT[id][LANG_EN];
}

void tr_sessions(char *buf, unsigned size, int n)
{
    if (lang == LANG_RU) {
        int a = n % 100, b = n % 10;
        const char *w = (a >= 11 && a <= 14) ? "сессий" : b == 1 ? "сессия" : (b >= 2 && b <= 4) ? "сессии" : "сессий";
        snprintf(buf, size, "+%d %s", n, w);
    } else {
        snprintf(buf, size, "+%d %s", n, n == 1 ? "session" : "sessions");
    }
}

const char *tr_scene_name(const char *scene)
{
    if (!strcmp(scene, "robot")) return tr(TR_SCENE_ROBOT);
    if (!strcmp(scene, "typist")) return tr(TR_SCENE_TYPIST);
    return tr(TR_SCENE_CURSOR);
}

ui_lang_t ui_i18n_get(void) { return lang; }

bool ui_i18n_set(ui_lang_t l)
{
    if (l >= LANG_COUNT || l == lang) return false;
    lang = l;
    return true;
}

bool ui_i18n_set_code(const char *code)
{
    if (!code) return false;
    if (!strcmp(code, "ru")) return ui_i18n_set(LANG_RU);
    if (!strcmp(code, "en")) return ui_i18n_set(LANG_EN);
    return false;
}
