#pragma once
/*
 * Протокол хост → плата: одна строка JSON на сообщение.
 * Разбор отделён от железа, чтобы тот же код работал в симуляторе (tools/sim).
 */
#include <stdbool.h>
#include <stdint.h>

#define PROTO_TEXT_MAX 160

typedef struct {
    bool ping;                    /* {"ping":1} — хост жив, экран не трогаем */

    bool has_state;
    char state[16];               /* idle | start | work | wait | done | error | compact */

    bool has_title, has_step;
    char title[PROTO_TEXT_MAX];
    char step[PROTO_TEXT_MAX];

    bool has_done, has_total;
    int done, total;

    bool has_sub, has_others;
    int sub;                      /* активных субагентов */
    int others;                   /* других активных сессий */

    bool has_approve, approve;    /* хост ждёт решения кнопкой */

    bool has_pair;
    char pair[8];                 /* код сопряжения; "" — скрыть экран сопряжения */

    bool has_agent, has_idle;
    char agent[16];               /* claude | codex — тема */
    char idle[16];                /* сцена ожидания */
} proto_msg_t;

/* Разбирает строку. false — не JSON или не объект. */
bool protocol_parse(const char *line, proto_msg_t *out);

/*
 * Применяет сообщение к интерфейсу, помня поля из прошлых сообщений
 * (done/total/sub/others можно присылать не каждый раз).
 * Вызывать под замком UI. now_ms — монотонное время.
 */
void protocol_apply(const proto_msg_t *m, uint32_t now_ms);

/*
 * Вызывать периодически (несколько раз в секунду). Если хост молчит дольше
 * PROTO_LINK_TIMEOUT_MS, интерфейс получает ui_status_link(false).
 * Демон шлёт {"ping":1} каждые 5 с, так что тишина значит обрыв.
 */
#define PROTO_LINK_TIMEOUT_MS 15000
void protocol_tick(uint32_t now_ms);

/* Время последнего сообщения от хоста (включая ping). */
uint32_t protocol_last_rx_ms(void);
