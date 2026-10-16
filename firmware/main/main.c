/*
 * Agent status bar — ESP-IDF 5.x, LilyGO T-Display-S3 AMOLED.
 * Принимает строки JSON по USB от host/daemon.py:
 *   {"state":"work","title":"...","step":"...","done":2,"total":5}
 * state: idle | start | work | wait | done
 */
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/usb_serial_jtag.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "cJSON.h"
#include "lvgl.h"
#include "display_rm67162.h"
#include "ui_status.h"

#define BRIGHT_ON      0xD0
#define BRIGHT_DIM     0x18
#define DIM_AFTER_MS   (3 * 60 * 1000)   /* беречь AMOLED от выгорания */

static const char *TAG = "agent";
static SemaphoreHandle_t ui_mux;
static volatile int64_t last_event_ms;
static bool dimmed;

static inline int64_t now_ms(void) { return esp_timer_get_time() / 1000; }

static void ui_lock(void)   { xSemaphoreTakeRecursive(ui_mux, portMAX_DELAY); }
static void ui_unlock(void) { xSemaphoreGiveRecursive(ui_mux); }

/* ---------- LVGL ---------- */

static void lvgl_task(void *arg)
{
    (void)arg;
    for (;;) {
        ui_lock();
        uint32_t wait = lv_timer_handler();

        /* Приглушаем экран, если давно ничего не происходит и задача не идёт */
        status_state_t st = ui_status_get_state();
        bool idle = (st == ST_IDLE || st == ST_DONE);
        if (idle && !dimmed && now_ms() - last_event_ms > DIM_AFTER_MS) {
            display_set_brightness(BRIGHT_DIM);
            dimmed = true;
        }
        ui_unlock();

        if (wait < 5)  wait = 5;
        if (wait > 30) wait = 30;
        vTaskDelay(pdMS_TO_TICKS(wait));
    }
}

/* ---------- приём данных ---------- */

static void apply_json(const char *line)
{
    cJSON *j = cJSON_Parse(line);
    if (!j) {
        ESP_LOGW(TAG, "bad json: %.60s", line);
        return;
    }

    static int done = 0, total = 1;
    const cJSON *jd = cJSON_GetObjectItem(j, "done");
    const cJSON *jt = cJSON_GetObjectItem(j, "total");
    if (cJSON_IsNumber(jd)) done  = jd->valueint;
    if (cJSON_IsNumber(jt)) total = jt->valueint;

    const char *state = cJSON_GetStringValue(cJSON_GetObjectItem(j, "state"));
    const char *title = cJSON_GetStringValue(cJSON_GetObjectItem(j, "title"));
    const char *step  = cJSON_GetStringValue(cJSON_GetObjectItem(j, "step"));

    ui_lock();
    last_event_ms = now_ms();
    if (dimmed) {
        display_set_brightness(BRIGHT_ON);
        dimmed = false;
    }
    ui_status_apply(ui_status_parse_state(state), title, step, done, total);
    ui_unlock();

    cJSON_Delete(j);
}

static void usb_rx_task(void *arg)
{
    (void)arg;
    static char line[1024];
    size_t len = 0;
    uint8_t buf[128];

    for (;;) {
        int n = usb_serial_jtag_read_bytes(buf, sizeof(buf), pdMS_TO_TICKS(50));
        for (int i = 0; i < n; i++) {
            char c = (char)buf[i];
            if (c == '\n' || c == '\r') {
                if (len) {
                    line[len] = '\0';
                    apply_json(line);
                    len = 0;
                }
            } else if (len < sizeof(line) - 1) {
                line[len++] = c;
            }
        }
    }
}

void app_main(void)
{
    ui_mux = xSemaphoreCreateRecursiveMutex();

    usb_serial_jtag_driver_config_t usb_cfg = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb_cfg));

    display_init();

    ui_lock();
    ui_status_create();
    ui_unlock();
    last_event_ms = now_ms();

    xTaskCreatePinnedToCore(lvgl_task,   "lvgl",   8192, NULL, 4, NULL, 1);
    xTaskCreatePinnedToCore(usb_rx_task, "usb_rx", 6144, NULL, 5, NULL, 0);

    const char *hello = "{\"hello\":\"agent-status\"}\n";
    usb_serial_jtag_write_bytes(hello, strlen(hello), pdMS_TO_TICKS(100));
    ESP_LOGI(TAG, "ready");
}
