#pragma once
/*
 * Wi-Fi-режим платы.
 *
 *  • Сети. До NET_MAX_WIFI сетей в NVS; плата сканирует эфир и подключается к самой сильной
 *    из знакомых, при потере — переподключается. Сети добавляют и удаляют только по USB:
 *      {"wifi_add":{"ssid":"Дом","pass":"..."}}  {"wifi_remove":"Дом"}  {"wifi_list":1}
 *    После добавления/удаления плата перезагружается (Wi-Fi нужно поднять до выделения кадра).
 *  • Поиск. UDP-порт NET_PORT: на {"discover":"agent-status"} плата отвечает
 *      {"agent_status":"0.3.0","id":"a1b2c3","port":8766,"name":"..."} тому, кто спросил.
 *  • Данные. TCP-порт NET_PORT, одна строка JSON на сообщение — тот же протокол, что по USB.
 *    Одновременно один клиент; новый вытесняет старого.
 *  • Доверие. Первым сообщением компьютер шлёт {"hello":{"token":"...","name":"..."}}.
 *    По USB токен запоминается сразу (кабель = физический доступ) → {"welcome":{...}}.
 *    По сети незнакомому токену отвечаем {"pair_required":{"id":...}} и игнорируем статусы,
 *    пока он не пройдёт сопряжение: {"pair":"123456","pair_token":"...","name":"..."} →
 *    код на экране, короткое нажатие кнопки → {"paired":{"id":...}}, долгое или 60 с → {"pair":"cancelled"}.
 */
#include <stdbool.h>

#define NET_PORT     8766
#define NET_MAX_WIFI 5
#define NET_MAX_HOSTS 8

typedef enum { NET_SRC_USB, NET_SRC_NET } net_src_t;

/* Рано в app_main, после nvs_flash_init и до display_init: читает NVS, поднимает Wi-Fi, если есть сети. */
void net_init(void);

/* После создания интерфейса: замок UI и куда отдавать строки протокола (то же, что из USB). */
void net_start(void (*lock)(void), void (*unlock)(void), void (*on_line)(const char *line));

/* Строка от компьютера. true — это служебное сообщение (обработано) или его надо отбросить;
 * false — обычная строка протокола, отдайте её интерфейсу. */
bool net_filter_line(net_src_t src, const char *line);

/* Отправить строку JSON доверенному сетевому клиенту (если он есть). */
void net_send_line(const char *json);

/* -1 — не подключена, 0..3 — сила сигнала */
int net_wifi_level(void);

/* Ответ кнопкой на запрос сопряжения */
void net_pair_answer(bool accept);
