/*
 * Кнопки на плате: опрос каждые 10 мс с антидребезгом, события — в ui_input.c.
 * Пины задаются в menuconfig → Agent Status Bar.
 */
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"
#include "input_esp.h"
#include "ui_input.h"

#define DEBOUNCE_SAMPLES 3     /* 30 мс одинакового уровня */

static void (*lock_fn)(void), (*unlock_fn)(void);

static void config_pin(int gpio)
{
    if (gpio < 0) return;
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << gpio,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,   /* кнопки замыкают на землю */
    };
    gpio_config(&io);
}

static bool read_pressed(void)
{
    bool p = false;
#if CONFIG_ASB_BUTTON_GPIO >= 0
    p |= gpio_get_level(CONFIG_ASB_BUTTON_GPIO) == 0;
#endif
#if CONFIG_ASB_BUTTON2_GPIO >= 0
    p |= gpio_get_level(CONFIG_ASB_BUTTON2_GPIO) == 0;
#endif
    return p;
}

static void input_task(void *arg)
{
    (void)arg;
    bool stable = false;
    int same = 0;
    for (;;) {
        bool now = read_pressed();
        if (now != stable) {
            if (++same >= DEBOUNCE_SAMPLES) {
                stable = now;
                same = 0;
                lock_fn();
                ui_input_button(stable);
                unlock_fn();
            }
        } else {
            same = 0;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void input_esp_start(void (*lock)(void), void (*unlock)(void))
{
    lock_fn = lock;
    unlock_fn = unlock;
    config_pin(CONFIG_ASB_BUTTON_GPIO);
    config_pin(CONFIG_ASB_BUTTON2_GPIO);
    xTaskCreatePinnedToCore(input_task, "input", 3072, NULL, 3, NULL, 0);
}
