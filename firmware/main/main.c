/*
 * Agent status bar — ESP-IDF 5.x, LilyGO T-Display-S3 AMOLED.
 * Принимает строки JSON по USB от host/daemon.py:
 *   {"state":"work","title":"...","step":"...","done":2,"total":5}
 * state: idle | start | work | wait | done | error | compact
 * Плюс {"ping":1} каждые 5 с — признак, что хост жив.
 */
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/usb_serial_jtag.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "lvgl.h"
#include "display_rm67162.h"
#include "ui_status.h"
#include "protocol.h"
#include "ui_screen.h"
#include "ui_input.h"
#include "ui_sound.h"
#include "input_esp.h"

static const char *TAG = "agent";
static SemaphoreHandle_t ui_mux;

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
        protocol_tick((uint32_t)now_ms());          /* хост молчит 15 с — «Нет связи» */
        ui_unlock();

        if (wait < 5)  wait = 5;
        if (wait > 30) wait = 30;
        vTaskDelay(pdMS_TO_TICKS(wait));
    }
}

/* ---------- приём данных ---------- */

static void apply_json(const char *line)
{
    proto_msg_t msg;
    if (!protocol_parse(line, &msg)) {
        ESP_LOGW(TAG, "bad json: %.60s", line);
        return;
    }
    ui_lock();
    protocol_apply(&msg, (uint32_t)now_ms());     /* яркость, сон и пробуждение — в ui_screen.c */
    ui_unlock();
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
    ui_screen_init();                             /* заставка → сцена ожидания */
    ui_input_init();
    ui_sound_init();
    ui_unlock();
    input_esp_start(ui_lock, ui_unlock);          /* кнопки: нажать, удерживать, дважды */

    xTaskCreatePinnedToCore(lvgl_task,   "lvgl",   8192, NULL, 4, NULL, 1);
    xTaskCreatePinnedToCore(usb_rx_task, "usb_rx", 6144, NULL, 5, NULL, 0);

    const char *hello = "{\"hello\":\"agent-status\"}\n";
    usb_serial_jtag_write_bytes(hello, strlen(hello), pdMS_TO_TICKS(100));
    ESP_LOGI(TAG, "ready");
}
