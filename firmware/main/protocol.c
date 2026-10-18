#include <string.h>
#include "cJSON.h"
#include "protocol.h"
#include "ui_status.h"
#include "ui_screen.h"

static uint32_t last_rx_ms;

static void copy_str(char *dst, size_t cap, const cJSON *item, bool *flag)
{
    const char *s = cJSON_GetStringValue(item);
    if (!s) return;
    strncpy(dst, s, cap - 1);
    dst[cap - 1] = '\0';
    *flag = true;
}

static void copy_int(int *dst, const cJSON *item, bool *flag)
{
    if (!cJSON_IsNumber(item)) return;
    *dst = item->valueint;
    *flag = true;
}

bool protocol_parse(const char *line, proto_msg_t *m)
{
    memset(m, 0, sizeof(*m));
    cJSON *j = cJSON_Parse(line);
    if (!cJSON_IsObject(j)) {
        cJSON_Delete(j);
        return false;
    }
    m->ping = cJSON_GetObjectItem(j, "ping") != NULL;
    const cJSON *ap = cJSON_GetObjectItem(j, "approve");
    if (cJSON_IsBool(ap)) { m->has_approve = true; m->approve = cJSON_IsTrue(ap); }
    copy_str(m->state, sizeof m->state, cJSON_GetObjectItem(j, "state"), &m->has_state);
    copy_str(m->title, sizeof m->title, cJSON_GetObjectItem(j, "title"), &m->has_title);
    copy_str(m->step,  sizeof m->step,  cJSON_GetObjectItem(j, "step"),  &m->has_step);
    copy_str(m->agent, sizeof m->agent, cJSON_GetObjectItem(j, "agent"), &m->has_agent);
    copy_str(m->idle,  sizeof m->idle,  cJSON_GetObjectItem(j, "idle"),  &m->has_idle);
    copy_str(m->pair,  sizeof m->pair,  cJSON_GetObjectItem(j, "pair"),  &m->has_pair);
<<<<<<< HEAD
    copy_str(m->lang,  sizeof m->lang,  cJSON_GetObjectItem(j, "lang"),  &m->has_lang);
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    copy_int(&m->done,   cJSON_GetObjectItem(j, "done"),   &m->has_done);
    copy_int(&m->total,  cJSON_GetObjectItem(j, "total"),  &m->has_total);
    copy_int(&m->sub,    cJSON_GetObjectItem(j, "sub"),    &m->has_sub);
    copy_int(&m->others, cJSON_GetObjectItem(j, "others"), &m->has_others);
    cJSON_Delete(j);
    return true;
}

void protocol_apply(const proto_msg_t *m, uint32_t now_ms)
{
    static int done = 0, total = 1, sub = 0, others = 0;

    last_rx_ms = now_ms;
    ui_status_link(true, now_ms);
    if (m->ping && !m->has_state && !m->has_pair) return;
    if (m->has_pair) ui_screen_pairing(m->pair);

    if (m->has_done)   done = m->done;
    if (m->has_total)  total = m->total;
    if (m->has_sub)    sub = m->sub;
    if (m->has_others) others = m->others;

    if (m->has_agent) ui_status_set_theme(m->agent);
    if (m->has_idle)  ui_status_set_idle_scene(m->idle);
<<<<<<< HEAD
    if (m->has_lang)  ui_status_set_language(m->lang);
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046

    ui_status_set_counters(sub, others);
    bool to_idle = m->has_state && ui_status_parse_state(m->state) == ST_IDLE &&
                   ui_status_get_state() != ST_IDLE;
    if (to_idle) {
        ui_status_park();
    } else if (m->has_state || m->has_title || m->has_step || m->has_done || m->has_total) {
        ui_status_apply(m->has_state ? ui_status_parse_state(m->state) : ui_status_get_state(),
                        m->has_title ? m->title : NULL,
                        m->has_step ? m->step : NULL,
                        done, total);
    }
    if (m->has_approve || m->has_state) ui_status_set_approve(m->has_approve && m->approve);
    ui_screen_on_state(ui_status_get_state(), true);
}

void protocol_tick(uint32_t now_ms)
{
    if (now_ms - last_rx_ms > PROTO_LINK_TIMEOUT_MS)
        ui_status_link(false, now_ms);
}

uint32_t protocol_last_rx_ms(void) { return last_rx_ms; }
