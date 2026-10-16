#pragma once

typedef enum {
    ST_IDLE,     /* серый: ждём задачу          */
    ST_START,    /* красный: задача только пришла */
    ST_WORK,     /* оранжевый: в процессе        */
    ST_WAIT,     /* жёлтый: нужно подтверждение  */
    ST_DONE      /* зелёный: готово              */
} status_state_t;

void ui_status_create(void);

/* title/step = NULL — оставить прежний текст */
void ui_status_apply(status_state_t st, const char *title, const char *step,
                     int done, int total);

status_state_t ui_status_parse_state(const char *s);
status_state_t ui_status_get_state(void);
