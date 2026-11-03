/*
 * LilyGO T-Display-S3 (LCD 1.9″, ST7789, 170×320, 8-битная параллельная шина) + LVGL 9.
 *
 * Интерфейс рисуется в 536×240 — как на AMOLED-версии — в кадр в PSRAM (режим DIRECT),
 * а при выводе изменённая часть уменьшается до 320×143 с усреднением (display_scale.c)
 * и ставится по центру экрана 320×170. Физически экраны почти одного размера, поэтому
 * всё выглядит так же, просто точки крупнее.
 *
 * Выводы — из pin_config.h LilyGO: D0–D7 = 39,40,41,42,45,46,47,48; WR 8, RD 9, DC 7, CS 6,
 * RST 5; подсветка 38; GPIO15 — питание экрана и подсветки от аккумулятора.
 */
#include "sdkconfig.h"
#if CONFIG_ASB_BOARD_TDISPLAY_S3
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "display.h"
#include "display_scale.h"

#define PIN_D0  39
#define PIN_D1  40
#define PIN_D2  41
#define PIN_D3  42
#define PIN_D4  45
#define PIN_D5  46
#define PIN_D6  47
#define PIN_D7  48
#define PIN_WR  8
#define PIN_RD  9
#define PIN_DC  7
#define PIN_CS  6
#define PIN_RST 5
#define PIN_BL  38
#define PIN_PWR 15

#define PANEL_W 320                 /* после поворота: ландшафт */
#define PANEL_H 170
#define PANEL_GAP 35                /* у этой панели 170 видимых строк из 240 — сдвиг 35 */
#define PCLK_HZ (10 * 1000 * 1000)  /* 10 МГц: полный кадр ~11 мс */

#define SRC_W 536                   /* размер, в котором рисует интерфейс */
#define SRC_H 240
#define OUT_W PANEL_W
#define OUT_H 143                   /* 240 × 320 / 536 — пропорции сохраняются */
#define OUT_Y ((PANEL_H - OUT_H) / 2)

#define CHUNK_ROWS 24               /* сколько строк результата за одну передачу */

static const char *TAG = "st7789";
static esp_lcd_panel_handle_t panel;
static SemaphoreHandle_t done_sem;
static uint16_t *out_buf;           /* DMA-память для одной порции строк */

static uint16_t xs[OUT_W + 1], ys[OUT_H + 1], cell_x[SRC_W], cell_y[SRC_H];
static scale_t sc = { SRC_W, SRC_H, OUT_W, OUT_H, xs, ys, cell_x, cell_y };

static bool trans_done_cb(esp_lcd_panel_io_handle_t io, esp_lcd_panel_io_event_data_t *e, void *ctx)
{
    (void)io; (void)e; (void)ctx;
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(done_sem, &woken);
    return woken == pdTRUE;
}

/* Отправить прямоугольник и дождаться конца DMA, чтобы буфер можно было переиспользовать */
static void draw_wait(int x1, int y1, int x2_excl, int y2_excl, const void *px)
{
    esp_lcd_panel_draw_bitmap(panel, x1, y1, x2_excl, y2_excl, px);
    xSemaphoreTake(done_sem, portMAX_DELAY);
}

void display_set_brightness(uint8_t level)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, level);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static void backlight_init(void)
{
    ledc_timer_config_t t = { .speed_mode = LEDC_LOW_SPEED_MODE, .timer_num = LEDC_TIMER_0,
                              .duty_resolution = LEDC_TIMER_8_BIT, .freq_hz = 10000,
                              .clk_cfg = LEDC_AUTO_CLK };
    ESP_ERROR_CHECK(ledc_timer_config(&t));
    ledc_channel_config_t c = { .gpio_num = PIN_BL, .speed_mode = LEDC_LOW_SPEED_MODE,
                                .channel = LEDC_CHANNEL_0, .timer_sel = LEDC_TIMER_0, .duty = 0 };
    ESP_ERROR_CHECK(ledc_channel_config(&c));
}

static void panel_fill(uint16_t rgb565)
{
    uint16_t v = (uint16_t)(rgb565 >> 8 | rgb565 << 8);
    for (int i = 0; i < PANEL_W * CHUNK_ROWS; i++) out_buf[i] = v;
    for (int y = 0; y < PANEL_H; y += CHUNK_ROWS) {
        int h = (y + CHUNK_ROWS > PANEL_H) ? PANEL_H - y : CHUNK_ROWS;
        draw_wait(0, y, PANEL_W, y + h, out_buf);
    }
}

static void flush_cb(lv_display_t *disp, const lv_area_t *a, uint8_t *px)
{
    /* DIRECT: px — весь кадр 536×240, a — что в нём изменилось */
    int ox1, oy1, ox2, oy2;
    scale_area(&sc, a->x1, a->y1, a->x2, a->y2, &ox1, &oy1, &ox2, &oy2);
    int w = ox2 - ox1 + 1;
    int chunk = (PANEL_W * CHUNK_ROWS) / w;          /* узкая область — больше строк за раз */
    for (int oy = oy1; oy <= oy2; oy += chunk) {
        int rows = (oy + chunk > oy2 + 1) ? oy2 + 1 - oy : chunk;
        scale_rows(&sc, (const uint16_t *)px, ox1, ox2, oy, rows, out_buf, 1);
        draw_wait(ox1, OUT_Y + oy, ox2 + 1, OUT_Y + oy + rows, out_buf);
    }
    lv_display_flush_ready(disp);
}

static uint32_t tick_cb(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

lv_display_t *display_init(void)
{
    /* питание экрана (нужно при работе от аккумулятора) и неиспользуемый строб чтения */
    gpio_config_t io = { .pin_bit_mask = (1ULL << PIN_PWR) | (1ULL << PIN_RD), .mode = GPIO_MODE_OUTPUT };
    gpio_config(&io);
    gpio_set_level(PIN_PWR, 1);
    gpio_set_level(PIN_RD, 1);
    backlight_init();                                 /* подсветка выключена, пока экран не очищен */
    ESP_LOGI(TAG, "power on (GPIO%d), backlight GPIO%d", PIN_PWR, PIN_BL);

    done_sem = xSemaphoreCreateBinary();
    out_buf = heap_caps_malloc(PANEL_W * CHUNK_ROWS * 2, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    assert(out_buf);

    esp_lcd_i80_bus_handle_t bus;
    esp_lcd_i80_bus_config_t bus_cfg = {
        .clk_src = LCD_CLK_SRC_DEFAULT,
        .dc_gpio_num = PIN_DC,
        .wr_gpio_num = PIN_WR,
        .data_gpio_nums = { PIN_D0, PIN_D1, PIN_D2, PIN_D3, PIN_D4, PIN_D5, PIN_D6, PIN_D7 },
        .bus_width = 8,
        .max_transfer_bytes = PANEL_W * CHUNK_ROWS * 2,
    };
    ESP_ERROR_CHECK(esp_lcd_new_i80_bus(&bus_cfg, &bus));

    esp_lcd_panel_io_handle_t io_handle;
    esp_lcd_panel_io_i80_config_t io_cfg = {
        .cs_gpio_num = PIN_CS,
        .pclk_hz = PCLK_HZ,
        .trans_queue_depth = 4,
        .on_color_trans_done = trans_done_cb,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
        .dc_levels = { .dc_idle_level = 0, .dc_cmd_level = 0, .dc_dummy_level = 0, .dc_data_level = 1 },
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_i80(bus, &io_cfg, &io_handle));

    esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = PIN_RST,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(io_handle, &panel_cfg, &panel));
    ESP_ERROR_CHECK(esp_lcd_panel_reset(panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
    esp_lcd_panel_invert_color(panel, true);           /* у этой IPS-панели цвета инвертированы */
    esp_lcd_panel_swap_xy(panel, true);                /* ландшафт */
#if CONFIG_ASB_DISPLAY_FLIP
    esp_lcd_panel_mirror(panel, true, false);
#else
    esp_lcd_panel_mirror(panel, false, true);
#endif
    esp_lcd_panel_set_gap(panel, 0, PANEL_GAP);
    esp_lcd_panel_disp_on_off(panel, true);

    panel_fill(0x0000);
    display_set_brightness(0xFF);
    ESP_LOGI(TAG, "panel on");

#if CONFIG_ASB_DISPLAY_SELFTEST
    static const uint16_t test[] = { 0xF800, 0x07E0, 0x001F, 0x0000 };
    for (int i = 0; i < 4; i++) {
        panel_fill(test[i]);
        ESP_LOGI(TAG, "self-test color %d", i);
        vTaskDelay(pdMS_TO_TICKS(700));
    }
#endif
    display_set_brightness(0xD0);

    scale_init(&sc);
    size_t fb_size = SRC_W * SRC_H * 2;
    void *fb = heap_caps_malloc(fb_size, MALLOC_CAP_SPIRAM);
    assert(fb);

    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t *disp = lv_display_create(SRC_W, SRC_H);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(disp, fb, NULL, fb_size, LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(disp, flush_cb);

    ESP_LOGI(TAG, "display ready: UI %dx%d -> panel %dx%d", SRC_W, SRC_H, PANEL_W, PANEL_H);
    return disp;
}

#endif /* CONFIG_ASB_BOARD_TDISPLAY_S3 */
