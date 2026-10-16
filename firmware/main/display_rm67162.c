/*
 * Драйвер AMOLED RM67162 (QSPI) для LilyGO T-Display-S3 AMOLED + LVGL 9.
 * Протокол: команды 0x02 + адрес (reg << 8) по одной линии,
 *           пиксели 0x32 + 0x002C00, данные по четырём линиям.
 */
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "display_rm67162.h"

#define PIN_SCK   47
#define PIN_D0    18
#define PIN_D1    7
#define PIN_D2    48
#define PIN_D3    5
#define PIN_CS    6
#define PIN_RST   17
#define PIN_EN    38          /* питание панели на Touch-версии, на Basic — светодиод */

#define LCD_HOST  SPI2_HOST
#define LCD_FREQ  (75 * 1000 * 1000)   /* при артефактах снизьте до 40 МГц */

/* 0x60 — ландшафт. Если картинка зеркальная или вверх ногами, попробуйте 0xA0, 0x20 или 0xE0 */
#define LCD_MADCTL 0x60

/* Буфер LVGL: одна SPI-транзакция на S3 — максимум 32 КБ */
#define BUF_LINES 24
#define BUF_BYTES (LCD_W * BUF_LINES * 2)

static const char *TAG = "rm67162";
static spi_device_handle_t spi;

static void lcd_cmd(uint8_t cmd, const uint8_t *data, size_t len)
{
    spi_transaction_t t = {0};
    t.cmd  = 0x02;
    t.addr = (uint32_t)cmd << 8;
    if (len) {
        t.tx_buffer = data;
        t.length    = len * 8;
    }
    ESP_ERROR_CHECK(spi_device_polling_transmit(spi, &t));
}

static void lcd_cmd1(uint8_t cmd, uint8_t v) { lcd_cmd(cmd, &v, 1); }

static void lcd_set_window(int x1, int y1, int x2, int y2)
{
    uint8_t c[4] = { x1 >> 8, x1 & 0xFF, x2 >> 8, x2 & 0xFF };
    uint8_t r[4] = { y1 >> 8, y1 & 0xFF, y2 >> 8, y2 & 0xFF };
    lcd_cmd(0x2A, c, 4);
    lcd_cmd(0x2B, r, 4);
}

static void lcd_write_pixels(const void *px, size_t bytes)
{
    spi_transaction_t t = {0};
    t.flags     = SPI_TRANS_MODE_QIO;
    t.cmd       = 0x32;
    t.addr      = 0x002C00;
    t.tx_buffer = px;
    t.length    = bytes * 8;
    ESP_ERROR_CHECK(spi_device_transmit(spi, &t));
}

void display_set_brightness(uint8_t level)
{
    lcd_cmd1(0x51, level);
}

/* ---------- LVGL glue ---------- */

static void flush_cb(lv_display_t *disp, const lv_area_t *a, uint8_t *px)
{
    uint32_t n = lv_area_get_size(a);
    lv_draw_sw_rgb565_swap(px, n);            /* панель ждёт big-endian RGB565 */
    lcd_set_window(a->x1, a->y1, a->x2, a->y2);
    lcd_write_pixels(px, n * 2);
    lv_display_flush_ready(disp);
}

/* Контроллер AMOLED любит чётные координаты окна */
static void rounder_cb(lv_event_t *e)
{
    lv_area_t *a = lv_event_get_param(e);
    a->x1 &= ~1;
    a->y1 &= ~1;
    a->x2 |= 1;
    a->y2 |= 1;
}

static uint32_t tick_cb(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static void panel_hw_init(void)
{
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_RST) | (1ULL << PIN_EN),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io);
    gpio_set_level(PIN_EN, 1);

    spi_bus_config_t bus = {
        .sclk_io_num     = PIN_SCK,
        .data0_io_num    = PIN_D0,
        .data1_io_num    = PIN_D1,
        .data2_io_num    = PIN_D2,
        .data3_io_num    = PIN_D3,
        .max_transfer_sz = BUF_BYTES + 16,
        .flags           = SPICOMMON_BUSFLAG_MASTER | SPICOMMON_BUSFLAG_QUAD,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(LCD_HOST, &bus, SPI_DMA_CH_AUTO));

    spi_device_interface_config_t dev = {
        .command_bits   = 8,
        .address_bits   = 24,
        .mode           = 0,
        .clock_speed_hz = LCD_FREQ,
        .spics_io_num   = PIN_CS,
        .flags          = SPI_DEVICE_HALFDUPLEX,
        .queue_size     = 4,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(LCD_HOST, &dev, &spi));

    /* Аппаратный сброс */
    gpio_set_level(PIN_RST, 1); vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PIN_RST, 0); vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(PIN_RST, 1); vTaskDelay(pdMS_TO_TICKS(120));

    lcd_cmd(0x11, NULL, 0);                 /* sleep out */
    vTaskDelay(pdMS_TO_TICKS(120));
    lcd_cmd1(0x36, LCD_MADCTL);             /* ориентация */
    lcd_cmd1(0x3A, 0x55);                   /* 16 бит на пиксель */
    lcd_cmd1(0x51, 0x00);                   /* яркость 0, пока чистим экран */
}

static void panel_clear(uint8_t *buf)
{
    memset(buf, 0, BUF_BYTES);
    for (int y = 0; y < LCD_H; y += BUF_LINES) {
        int h = (y + BUF_LINES > LCD_H) ? LCD_H - y : BUF_LINES;
        lcd_set_window(0, y, LCD_W - 1, y + h - 1);
        lcd_write_pixels(buf, LCD_W * h * 2);
    }
}

lv_display_t *display_init(void)
{
    panel_hw_init();

    uint8_t *buf1 = heap_caps_malloc(BUF_BYTES, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    uint8_t *buf2 = heap_caps_malloc(BUF_BYTES, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    assert(buf1 && buf2);

    panel_clear(buf1);
    lcd_cmd(0x29, NULL, 0);                 /* display on */
    vTaskDelay(pdMS_TO_TICKS(20));
    display_set_brightness(0xD0);

    lv_init();
    lv_tick_set_cb(tick_cb);

    lv_display_t *disp = lv_display_create(LCD_W, LCD_H);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(disp, buf1, buf2, BUF_BYTES, LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(disp, flush_cb);
    lv_display_add_event_cb(disp, rounder_cb, LV_EVENT_INVALIDATE_AREA, NULL);

    ESP_LOGI(TAG, "display ready %dx%d", LCD_W, LCD_H);
    return disp;
}
