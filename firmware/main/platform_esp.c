/*
 * Платформа на плате LilyGO T-Display-S3 AMOLED.
 *   яркость  — команда 0x51 контроллера RM67162;
 *   батарея  — АЦП на GPIO4 через делитель 1:2 (как в библиотеке LilyGO);
 *   Wi-Fi    — пока не используется (плата работает по USB), возвращаем -1;
 *   пищалка  — LEDC на CONFIG_ASB_BUZZER_GPIO (menuconfig → Agent Status Bar);
 *   связь    — строки JSON хосту по USB Serial/JTAG.
 */
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "driver/ledc.h"
#include "driver/usb_serial_jtag.h"
#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "display_rm67162.h"
#include "platform.h"

#define BAT_ADC_UNIT    ADC_UNIT_1
#define BAT_ADC_CHANNEL ADC_CHANNEL_3          /* GPIO4 на ESP32-S3 */
#define BAT_DIVIDER     2
#define BAT_NO_BATTERY_MV 2800                  /* ниже — аккумулятора нет */
#define BAT_USB_MV       4300                   /* выше — питание от USB, идёт зарядка */

#include "sdkconfig.h"
#ifdef CONFIG_ASB_BUZZER_GPIO
#define BUZZER_GPIO CONFIG_ASB_BUZZER_GPIO
#else
#define BUZZER_GPIO -1
#endif

static const char *TAG = "platform";
static adc_oneshot_unit_handle_t adc;
static adc_cali_handle_t cali;
static bool adc_ok, cali_ok;
static int filtered_mv;

void platform_set_brightness(uint8_t level) { display_set_brightness(level); }

static void adc_init(void)
{
    adc_oneshot_unit_init_cfg_t ucfg = { .unit_id = BAT_ADC_UNIT };
    if (adc_oneshot_new_unit(&ucfg, &adc) != ESP_OK) return;
    adc_oneshot_chan_cfg_t ccfg = { .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT };
    if (adc_oneshot_config_channel(adc, BAT_ADC_CHANNEL, &ccfg) != ESP_OK) return;
    adc_ok = true;
    adc_cali_curve_fitting_config_t cal = {
        .unit_id = BAT_ADC_UNIT, .chan = BAT_ADC_CHANNEL,
        .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    cali_ok = adc_cali_create_scheme_curve_fitting(&cal, &cali) == ESP_OK;
    ESP_LOGI(TAG, "battery ADC ready, calibration %s", cali_ok ? "on" : "off");
}

/* Кривая разряда Li-ion: напряжение под небольшой нагрузкой → проценты */
static int li_ion_pct(int mv)
{
    static const int table[][2] = {
        { 4150, 100 }, { 4050, 90 }, { 3970, 80 }, { 3900, 70 }, { 3840, 60 }, { 3790, 50 },
        { 3750, 40 }, { 3710, 30 }, { 3670, 20 }, { 3600, 10 }, { 3450, 5 }, { 3300, 0 },
    };
    if (mv >= table[0][0]) return 100;
    for (unsigned i = 1; i < sizeof table / sizeof table[0]; i++)
        if (mv >= table[i][0]) {
            int v0 = table[i][0], v1 = table[i - 1][0], p0 = table[i][1], p1 = table[i - 1][1];
            return p0 + (mv - v0) * (p1 - p0) / (v1 - v0);
        }
    return 0;
}

platform_battery_t platform_battery(void)
{
    static bool inited;
    if (!inited) { inited = true; adc_init(); }
    platform_battery_t b = { 0 };
    if (!adc_ok) return b;
    int sum = 0, n = 0;
    for (int i = 0; i < 8; i++) {
        int raw, mv;
        if (adc_oneshot_read(adc, BAT_ADC_CHANNEL, &raw) != ESP_OK) continue;
        if (cali_ok) adc_cali_raw_to_voltage(cali, raw, &mv);
        else mv = raw * 3300 / 4095;
        sum += mv * BAT_DIVIDER;
        n++;
    }
    if (!n) return b;
    int mv = sum / n;
    filtered_mv = filtered_mv ? (filtered_mv * 7 + mv) / 8 : mv;   /* сглаживаем скачки */
    b.mv = filtered_mv;
    b.present = filtered_mv > BAT_NO_BATTERY_MV;
    b.charging = filtered_mv > BAT_USB_MV;
    b.pct = b.charging ? 100 : li_ion_pct(filtered_mv);
    return b;
}

int platform_wifi_level(void) { return -1; }

void platform_tone(uint16_t hz)
{
#if BUZZER_GPIO >= 0
    static bool inited;
    if (!inited) {
        inited = true;
        ledc_timer_config_t tcfg = { .speed_mode = LEDC_LOW_SPEED_MODE, .timer_num = LEDC_TIMER_1,
                                     .duty_resolution = LEDC_TIMER_10_BIT, .freq_hz = 2000,
                                     .clk_cfg = LEDC_AUTO_CLK };
        ledc_timer_config(&tcfg);
        ledc_channel_config_t ccfg = { .gpio_num = BUZZER_GPIO, .speed_mode = LEDC_LOW_SPEED_MODE,
                                       .channel = LEDC_CHANNEL_1, .timer_sel = LEDC_TIMER_1, .duty = 0 };
        ledc_channel_config(&ccfg);
    }
    if (hz) ledc_set_freq(LEDC_LOW_SPEED_MODE, LEDC_TIMER_1, hz);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, hz ? 512 : 0);   /* меандр 50 % */
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
#else
    (void)hz;
#endif
}

void platform_send_line(const char *json)
{
    usb_serial_jtag_write_bytes(json, strlen(json), pdMS_TO_TICKS(20));
    usb_serial_jtag_write_bytes("\n", 1, pdMS_TO_TICKS(20));
}
