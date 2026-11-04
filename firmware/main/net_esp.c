/* Wi-Fi-режим: сети, поиск, TCP-приём, доверие и сопряжение. Описание протокола — в net_esp.h. */
#include "sdkconfig.h"
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "cJSON.h"
#include "driver/usb_serial_jtag.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "lwip/sockets.h"
#include "nvs.h"
#include "net_esp.h"
#include "ui_screen.h"
#include "version.h"

#ifndef CONFIG_ASB_WIFI
#define CONFIG_ASB_WIFI 0
#endif

static const char *TAG = "net";

typedef struct { char ssid[33]; char pass[65]; } wifi_net_t;

static wifi_net_t nets[NET_MAX_WIFI];
static int n_nets;
static char hosts[NET_MAX_HOSTS][33];        /* токены доверенных компьютеров */
static int n_hosts;
static char board_id[7];

static void (*ui_lock)(void), (*ui_unlock)(void);
static void (*deliver)(const char *line);

static SemaphoreHandle_t tx_mux;
static int client = -1;                       /* сокет TCP-клиента */
static volatile bool client_trusted;

static bool wifi_up;                          /* Wi-Fi инициализирован */
static esp_netif_t *sta_netif;
static EventGroupHandle_t wifi_ev;
#define EV_GOT_IP BIT0
#define EV_FAIL   BIT1
static volatile bool connected;
static char cur_ssid[33];
static volatile int level = -1;

/* Сопряжение */
static char pair_token[33];
static int pair_sock = -1;
static int64_t pair_deadline;
static volatile int pair_answer;              /* 0 — ждём, 1 — да, 2 — нет */

/* ---------- NVS ---------- */

static void nvs_load(void)
{
    nvs_handle_t h;
    if (nvs_open("asb", NVS_READONLY, &h) != ESP_OK) return;
    size_t sz = sizeof nets;
    if (nvs_get_blob(h, "nets", nets, &sz) == ESP_OK) n_nets = (int)(sz / sizeof nets[0]);
    sz = sizeof hosts;
    if (nvs_get_blob(h, "hosts", hosts, &sz) == ESP_OK) n_hosts = (int)(sz / sizeof hosts[0]);
    nvs_close(h);
}

static void nvs_save(void)
{
    nvs_handle_t h;
    if (nvs_open("asb", NVS_READWRITE, &h) != ESP_OK) return;
    if (n_nets) nvs_set_blob(h, "nets", nets, n_nets * sizeof nets[0]);
    else nvs_erase_key(h, "nets");
    if (n_hosts) nvs_set_blob(h, "hosts", hosts, n_hosts * sizeof hosts[0]);
    else nvs_erase_key(h, "hosts");
    nvs_commit(h);
    nvs_close(h);
}

static bool host_trusted(const char *token)
{
    if (!token || strlen(token) < 8) return false;
    for (int i = 0; i < n_hosts; i++)
        if (!strncmp(hosts[i], token, sizeof hosts[i] - 1)) return true;
    return false;
}

static void host_trust(const char *token)
{
    if (!token || strlen(token) < 8 || host_trusted(token)) return;
    if (n_hosts == NET_MAX_HOSTS) {                      /* самый старый уступает место */
        memmove(hosts[0], hosts[1], sizeof hosts[0] * (NET_MAX_HOSTS - 1));
        n_hosts--;
    }
    snprintf(hosts[n_hosts++], sizeof hosts[0], "%s", token);
    nvs_save();
    ESP_LOGI(TAG, "trusted computers: %d", n_hosts);
}

/* ---------- отправка ---------- */

static void usb_send(const char *json)
{
    usb_serial_jtag_write_bytes(json, strlen(json), pdMS_TO_TICKS(20));
    usb_serial_jtag_write_bytes("\n", 1, pdMS_TO_TICKS(20));
}

static void sock_send(int s, const char *json)
{
    if (s < 0) return;
    xSemaphoreTake(tx_mux, portMAX_DELAY);
    send(s, json, strlen(json), 0);
    send(s, "\n", 1, 0);
    xSemaphoreGive(tx_mux);
}

static void reply(net_src_t src, cJSON *obj)
{
    char *txt = cJSON_PrintUnformatted(obj);
    if (txt) {
        if (src == NET_SRC_USB) usb_send(txt);
        else sock_send(client, txt);
        cJSON_free(txt);
    }
    cJSON_Delete(obj);
}

void net_send_line(const char *json)
{
    if (client >= 0 && client_trusted) sock_send(client, json);
}

/* ---------- ответы ---------- */

static cJSON *wifi_status(void)
{
    cJSON *o = cJSON_CreateObject(), *w = cJSON_AddObjectToObject(o, "wifi");
    cJSON *arr = cJSON_AddArrayToObject(w, "saved");
    for (int i = 0; i < n_nets; i++) cJSON_AddItemToArray(arr, cJSON_CreateString(nets[i].ssid));
    cJSON_AddStringToObject(w, "id", board_id);
    if (connected) {
        cJSON_AddStringToObject(w, "connected", cur_ssid);
        esp_netif_ip_info_t ip;
        if (sta_netif && esp_netif_get_ip_info(sta_netif, &ip) == ESP_OK) {
            char buf[16];
            snprintf(buf, sizeof buf, IPSTR, IP2STR(&ip.ip));
            cJSON_AddStringToObject(w, "ip", buf);
        }
        wifi_ap_record_t ap;
        if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) cJSON_AddNumberToObject(w, "rssi", ap.rssi);
    } else {
        cJSON_AddNullToObject(w, "connected");
    }
    return o;
}

static void restart_cb(void *arg) { (void)arg; esp_restart(); }

static void restart_soon(void)
{
    static esp_timer_handle_t t;
    if (!t) {
        esp_timer_create_args_t a = { .callback = restart_cb, .name = "restart" };
        esp_timer_create(&a, &t);
    }
    esp_timer_start_once(t, 800 * 1000);
}

/* ---------- служебные сообщения ---------- */

static bool has_control_key(const char *line)
{
    return strstr(line, "\"hello\"") || strstr(line, "\"wifi_") || strstr(line, "\"pair_token\"");
}

bool net_filter_line(net_src_t src, const char *line)
{
    bool drop_untrusted = (src == NET_SRC_NET && !client_trusted);
    if (line[0] != '{' || !has_control_key(line)) return drop_untrusted;

    cJSON *j = cJSON_Parse(line);
    if (!j) return drop_untrusted;

    const cJSON *hello = cJSON_GetObjectItem(j, "hello");
    const cJSON *add = cJSON_GetObjectItem(j, "wifi_add");
    const cJSON *rem = cJSON_GetObjectItem(j, "wifi_remove");
    const cJSON *list = cJSON_GetObjectItem(j, "wifi_list");
    const cJSON *ptok = cJSON_GetObjectItem(j, "pair_token");
    bool handled = true;

    if (cJSON_IsObject(hello)) {
        const char *token = cJSON_GetStringValue(cJSON_GetObjectItem(hello, "token"));
        cJSON *o = cJSON_CreateObject();
        if (src == NET_SRC_USB) host_trust(token);       /* кабель — уже доверие */
        bool ok = (src == NET_SRC_USB) || host_trusted(token);
        if (src == NET_SRC_NET) client_trusted = ok;
        cJSON *body = cJSON_AddObjectToObject(o, ok ? "welcome" : "pair_required");
        cJSON_AddStringToObject(body, "id", board_id);
        cJSON_AddStringToObject(body, "fw", FW_VERSION);
        cJSON_AddBoolToObject(body, "trusted", ok);
        if (connected) cJSON_AddStringToObject(body, "wifi", cur_ssid);
        reply(src, o);
    } else if (cJSON_IsObject(add) && src == NET_SRC_USB) {
        const char *ssid = cJSON_GetStringValue(cJSON_GetObjectItem(add, "ssid"));
        const char *pass = cJSON_GetStringValue(cJSON_GetObjectItem(add, "pass"));
        if (ssid && *ssid && strlen(ssid) < sizeof nets[0].ssid && (!pass || strlen(pass) < sizeof nets[0].pass)) {
            int i;
            for (i = 0; i < n_nets && strcmp(nets[i].ssid, ssid); i++) {}
            if (i == n_nets) {                               /* новая сеть: самая старая уступает место */
                if (n_nets == NET_MAX_WIFI) { memmove(&nets[0], &nets[1], sizeof nets[0] * (NET_MAX_WIFI - 1)); n_nets--; }
                i = n_nets++;
            }
            snprintf(nets[i].ssid, sizeof nets[i].ssid, "%s", ssid);
            snprintf(nets[i].pass, sizeof nets[i].pass, "%s", pass ? pass : "");
            nvs_save();
            cJSON *o = wifi_status();
            cJSON_AddBoolToObject(cJSON_GetObjectItem(o, "wifi"), "rebooting", true);
            reply(src, o);
            restart_soon();
        } else {
            cJSON *o = cJSON_CreateObject();
            cJSON_AddStringToObject(cJSON_AddObjectToObject(o, "wifi"), "error", "bad ssid or password");
            reply(src, o);
        }
    } else if (cJSON_IsString(rem) && src == NET_SRC_USB) {
        int i;
        for (i = 0; i < n_nets && strcmp(nets[i].ssid, rem->valuestring); i++) {}
        bool found = i < n_nets;
        if (found) {
            memmove(&nets[i], &nets[i + 1], sizeof nets[0] * (n_nets - i - 1));
            n_nets--;
            nvs_save();
        }
        cJSON *o = wifi_status();
        cJSON_AddBoolToObject(cJSON_GetObjectItem(o, "wifi"), "removed", found);
        if (found) cJSON_AddBoolToObject(cJSON_GetObjectItem(o, "wifi"), "rebooting", true);
        reply(src, o);
        if (found) restart_soon();
    } else if (list && (src == NET_SRC_USB || client_trusted)) {
        reply(src, wifi_status());
    } else if (cJSON_IsString(ptok) && src == NET_SRC_NET) {
        const char *code = cJSON_GetStringValue(cJSON_GetObjectItem(j, "pair"));
        if (code && strlen(code) <= 6) {
            snprintf(pair_token, sizeof pair_token, "%s", ptok->valuestring);
            pair_sock = client;
            pair_answer = 0;
            pair_deadline = esp_timer_get_time() + 60 * 1000000LL;
            ui_lock();
            ui_screen_pairing(code);
            ui_unlock();
            ESP_LOGI(TAG, "pairing request, code shown");
        }
    } else {
        handled = false;                                     /* например, wifi_add по сети — нельзя */
    }
    cJSON_Delete(j);
    return handled || drop_untrusted;
}

void net_pair_answer(bool accept)
{
    if (pair_sock >= 0) pair_answer = accept ? 1 : 2;
}

static void pair_finish(bool accept, bool hide_screen)
{
    cJSON *o = cJSON_CreateObject();
    if (accept) {
        host_trust(pair_token);
        if (pair_sock == client) client_trusted = true;
        cJSON_AddStringToObject(cJSON_AddObjectToObject(o, "paired"), "id", board_id);
    } else {
        cJSON_AddStringToObject(o, "pair", "cancelled");
    }
    char *txt = cJSON_PrintUnformatted(o);
    if (txt) { sock_send(pair_sock, txt); cJSON_free(txt); }
    cJSON_Delete(o);
    if (hide_screen) { ui_lock(); ui_screen_pairing(""); ui_unlock(); }
    pair_sock = -1;
    pair_answer = 0;
    ESP_LOGI(TAG, "pairing %s", accept ? "confirmed" : "cancelled");
}

/* ---------- Wi-Fi ---------- */

int net_wifi_level(void) { return level; }
bool net_wifi_configured(void) { return n_nets > 0; }

static void on_wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg; (void)data;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        connected = false;
        level = -1;
        xEventGroupSetBits(wifi_ev, EV_FAIL);
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        connected = true;
        xEventGroupSetBits(wifi_ev, EV_GOT_IP);
    }
}

/* Скан, выбор самой сильной знакомой сети, подключение; при потере — заново */
static void wifi_task(void *arg)
{
    (void)arg;
    static wifi_ap_record_t recs[20];
    int backoff = 2;
    for (;;) {
        if (connected) {
            xEventGroupWaitBits(wifi_ev, EV_FAIL, pdTRUE, pdFALSE, portMAX_DELAY);
            ESP_LOGW(TAG, "Wi-Fi lost");
            continue;
        }
        uint16_t n = sizeof recs / sizeof recs[0];
        int best = -1, best_rssi = -127;
        if (esp_wifi_scan_start(NULL, true) == ESP_OK && esp_wifi_scan_get_ap_records(&n, recs) == ESP_OK) {
            for (int i = 0; i < n; i++)
                for (int k = 0; k < n_nets; k++)
                    if (!strcmp((const char *)recs[i].ssid, nets[k].ssid) && recs[i].rssi > best_rssi) {
                        best = k;
                        best_rssi = recs[i].rssi;
                    }
        }
        if (best < 0) {
            ESP_LOGI(TAG, "no known network in range, retry in %d s", backoff);
            vTaskDelay(pdMS_TO_TICKS(backoff * 1000));
            if (backoff < 30) backoff *= 2;
            continue;
        }
        wifi_config_t cfg = { 0 };
        snprintf((char *)cfg.sta.ssid, sizeof cfg.sta.ssid, "%s", nets[best].ssid);
        snprintf((char *)cfg.sta.password, sizeof cfg.sta.password, "%s", nets[best].pass);
        cfg.sta.threshold.authmode = nets[best].pass[0] ? WIFI_AUTH_WPA_PSK : WIFI_AUTH_OPEN;
        esp_wifi_set_config(WIFI_IF_STA, &cfg);
        xEventGroupClearBits(wifi_ev, EV_GOT_IP | EV_FAIL);
        ESP_LOGI(TAG, "connecting to \"%s\" (%d dBm)", nets[best].ssid, best_rssi);
        esp_wifi_connect();
        EventBits_t b = xEventGroupWaitBits(wifi_ev, EV_GOT_IP | EV_FAIL, pdTRUE, pdFALSE, pdMS_TO_TICKS(15000));
        if (b & EV_GOT_IP) {
            snprintf(cur_ssid, sizeof cur_ssid, "%s", nets[best].ssid);
            ESP_LOGI(TAG, "connected to \"%s\"", cur_ssid);
            backoff = 2;
        } else {
            ESP_LOGW(TAG, "could not connect to \"%s\"", nets[best].ssid);
            esp_wifi_disconnect();
            vTaskDelay(pdMS_TO_TICKS(backoff * 1000));
            if (backoff < 30) backoff *= 2;
        }
    }
}

/* ---------- сеть: поиск и TCP ---------- */

static int open_socket(int type)
{
    int s = socket(AF_INET, type, type == SOCK_DGRAM ? IPPROTO_UDP : IPPROTO_TCP);
    if (s < 0) return -1;
    int one = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_port = htons(NET_PORT), .sin_addr.s_addr = htonl(INADDR_ANY) };
    if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) { close(s); return -1; }
    if (type == SOCK_STREAM && listen(s, 2) < 0) { close(s); return -1; }
    return s;
}

static void drop_client(void)
{
    if (client < 0) return;
    if (pair_sock == client) pair_finish(false, true);
    xSemaphoreTake(tx_mux, portMAX_DELAY);
    close(client);
    client = -1;
    client_trusted = false;
    xSemaphoreGive(tx_mux);
}

static void net_task(void *arg)
{
    (void)arg;
    xEventGroupWaitBits(wifi_ev, EV_GOT_IP, pdFALSE, pdFALSE, portMAX_DELAY);
    int udp = open_socket(SOCK_DGRAM), srv = open_socket(SOCK_STREAM);
    if (udp < 0 || srv < 0) {
        ESP_LOGE(TAG, "cannot open port %d", NET_PORT);
        vTaskDelete(NULL);
        return;
    }
    ESP_LOGI(TAG, "listening on port %d, board id %s", NET_PORT, board_id);
    static char buf[1024];
    size_t len = 0;
    int64_t level_t = 0;

    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(udp, &rd);
        FD_SET(srv, &rd);
        int maxfd = udp > srv ? udp : srv;
        if (client >= 0) { FD_SET(client, &rd); if (client > maxfd) maxfd = client; }
        struct timeval tv = { .tv_sec = 0, .tv_usec = 200 * 1000 };
        int r = select(maxfd + 1, &rd, NULL, NULL, &tv);

        if (r > 0 && FD_ISSET(udp, &rd)) {                       /* кто-то ищет плату */
            char q[128];
            struct sockaddr_in from;
            socklen_t fl = sizeof from;
            int n = recvfrom(udp, q, sizeof q - 1, 0, (struct sockaddr *)&from, &fl);
            if (n > 0) {
                q[n] = 0;
                if (strstr(q, "\"discover\"")) {
                    char ans[160];
                    int k = snprintf(ans, sizeof ans,
                                     "{\"agent_status\":\"%s\",\"id\":\"%s\",\"port\":%d,\"name\":\"Agent Status Bar %s\"}",
                                     FW_VERSION, board_id, NET_PORT, board_id);
                    sendto(udp, ans, k, 0, (struct sockaddr *)&from, fl);
                }
            }
        }
        if (r > 0 && FD_ISSET(srv, &rd)) {                       /* новый компьютер вытесняет старого */
            int s = accept(srv, NULL, NULL);
            if (s >= 0) {
                drop_client();
                struct timeval to = { .tv_sec = 0, .tv_usec = 300 * 1000 };
                setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &to, sizeof to);
                int one = 1;
                setsockopt(s, SOL_SOCKET, SO_KEEPALIVE, &one, sizeof one);
                client = s;
                client_trusted = false;
                len = 0;
                ESP_LOGI(TAG, "computer connected");
            }
        }
        if (r > 0 && client >= 0 && FD_ISSET(client, &rd)) {
            int n = recv(client, buf + len, sizeof buf - 1 - len, 0);
            if (n <= 0) {
                ESP_LOGI(TAG, "computer disconnected");
                drop_client();
            } else {
                len += n;
                buf[len] = 0;
                char *start = buf, *nl;
                while ((nl = strchr(start, '\n'))) {
                    *nl = 0;
                    if (nl > start && nl[-1] == '\r') nl[-1] = 0;
                    if (*start && !net_filter_line(NET_SRC_NET, start) && deliver) deliver(start);
                    start = nl + 1;
                }
                len = strlen(start);
                memmove(buf, start, len + 1);
                if (len >= sizeof buf - 1) len = 0;          /* слишком длинная строка — выбрасываем */
            }
        }

        /* сопряжение: ответ кнопкой или таймаут */
        if (pair_sock >= 0) {
            if (pair_answer) pair_finish(pair_answer == 1, false);
            else if (esp_timer_get_time() > pair_deadline) pair_finish(false, true);
        }

        int64_t now = esp_timer_get_time();
        if (now - level_t > 2000000) {                       /* сила сигнала для значка */
            level_t = now;
            wifi_ap_record_t ap;
            if (connected && esp_wifi_sta_get_ap_info(&ap) == ESP_OK)
                level = ap.rssi > -60 ? 3 : ap.rssi > -70 ? 2 : ap.rssi > -80 ? 1 : 0;
            else
                level = -1;
        }
    }
}

/* ---------- запуск ---------- */

void net_init(void)
{
    uint8_t mac[6] = { 0 };
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    snprintf(board_id, sizeof board_id, "%02x%02x%02x", mac[3], mac[4], mac[5]);
    tx_mux = xSemaphoreCreateMutex();
    nvs_load();
    ESP_LOGI(TAG, "board id %s, %d saved network(s), %d trusted computer(s)", board_id, n_nets, n_hosts);
    if (!CONFIG_ASB_WIFI || n_nets == 0) return;

    wifi_ev = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    sta_netif = esp_netif_create_default_wifi_sta();
    char host[24];
    snprintf(host, sizeof host, "agent-status-%s", board_id);
    esp_netif_set_hostname(sta_netif, host);
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    if (esp_wifi_init(&cfg) != ESP_OK) {
        ESP_LOGE(TAG, "Wi-Fi init failed — working over USB only");
        return;
    }
    esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, on_wifi_event, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_wifi_event, NULL);
    esp_wifi_set_storage(WIFI_STORAGE_RAM);
    esp_wifi_set_mode(WIFI_MODE_STA);
    ESP_ERROR_CHECK(esp_wifi_start());
    esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
    wifi_up = true;
}

void net_start(void (*lock)(void), void (*unlock)(void), void (*on_line)(const char *line))
{
    ui_lock = lock;
    ui_unlock = unlock;
    deliver = on_line;
    if (!wifi_up) return;
    xTaskCreatePinnedToCore(wifi_task, "wifi", 4096, NULL, 3, NULL, 0);
    xTaskCreatePinnedToCore(net_task, "net", 6144, NULL, 4, NULL, 0);
}
