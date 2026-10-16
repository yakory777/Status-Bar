# Agent Status Bar

[English](README.md) · **Русский**

Физический индикатор прогресса для задач [Claude Code](https://claude.com/claude-code) и [OpenAI Codex](https://developers.openai.com/codex) на ESP32-S3 с AMOLED-дисплеем. Пока агент работает, на столе видно, чем он занят, сколько пунктов плана выполнено и не ждёт ли он вашего подтверждения.

<table align="center">
  <tr>
    <th></th>
    <th>Агент работает</th>
    <th>Ждёт задачу</th>
  </tr>
  <tr>
    <td><b>Claude</b></td>
    <td><img src="docs/claude_task.gif" width="400" alt="Тема Claude: экран задачи от старта до завершения"></td>
    <td><img src="docs/claude_idle_robot.gif" width="400" alt="Тема Claude: пиксельный робот скачет по буквам Ready to work"></td>
  </tr>
  <tr>
    <td><b>Codex</b></td>
    <td><img src="docs/codex_task.gif" width="400" alt="Тема Codex: экран задачи в стиле терминала"></td>
    <td><img src="docs/codex_idle_cursor.gif" width="400" alt="Тема Codex: живой курсор печатает Ready to work"></td>
  </tr>
</table>

## Что показывает экран

Пока идёт задача, на экране видно текст вашего запроса, текущий шаг («Правит auth.ts», «$ npm test»), сегментированную полосу прогресса по плану агента (до 12 пунктов), счётчик «3/7» с процентом и время с начала задачи. Пилюля статуса и полоса меняют цвет по состоянию:

| Состояние | Тема Claude | Тема Codex | Когда |
|---|---|---|---|
| Старт | 🔴 Красный | ⚪ Белый | Вы отправили задачу, агент думает |
| В работе | 🟠 Оранжевый | 🟢 Зелёный ChatGPT | Агент вызывает инструменты: правит файлы, запускает команды |
| Ждёт вас | 🟡 Жёлтый | 🟡 Янтарный | Агент просит разрешение на действие |
| Готово | 🟢 Зелёный | 🟢 Светлый мятный | Задача завершена |
| Ожидание | ⚪ Серый | ⚪ Серый | Задачи нет, играет сцена ожидания |

Анимации сделаны на LVGL: плавная смена цвета, заливка сегментов, пульсация текущего шага (быстрее, когда агент ждёт вас) и волна слева направо при завершении. Через 3 минуты простоя экран приглушается, чтобы AMOLED не выгорал.

### Темы

Экран переключается на тему того агента, который прислал событие последним.

- **Claude** — тёплые оранжевые акценты, антиква Lora в сценах ожидания, DejaVu Sans на экране задачи.
- **Codex** — чёрный, белый и фирменный зелёный ChatGPT `#10A37F`, моноширинный шрифт как в терминале.

Маскоты — оригинальные пиксельные персонажи, нарисованные для этого проекта; логотипы и фирменные персонажи не используются.

### Сцены ожидания — на выбор

У каждой темы по две сцены ожидания. Каждая заканчивается тем, что маскот прыгает в камеру и растворяется в цвете темы, после чего сцена бесшовно начинается заново.

<table align="center">
  <tr>
    <td align="center"><img src="docs/claude_idle_robot.gif" width="400" alt="Сцена «робот»"><br><b>Claude · <code>robot</code></b> (по умолчанию)<br>Пиксельный робот падает на надпись и скачет по буквам: каждая проседает под ним и загорается.</td>
    <td align="center"><img src="docs/claude_idle_cursor.gif" width="400" alt="Сцена «курсор», тема Claude"><br><b>Claude · <code>cursor</code></b><br>Оранжевый курсор просыпается, открывает глаза и печатает строку, оставляя за собой буквы.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/codex_idle_cursor.gif" width="400" alt="Сцена «курсор», тема Codex"><br><b>Codex · <code>cursor</code></b> (по умолчанию)<br>Курсор терминала оживает и печатает команду, а когда мигает, его глаза остаются висеть в воздухе.</td>
    <td align="center"><img src="docs/codex_idle_typist.gif" width="400" alt="Сцена «машинистка»"><br><b>Codex · <code>typist</code></b><br>Слайм сидит за пиксельной клавиатурой, стучит по клавишам короткими лапками и с размаху бьёт по Enter.</td>
  </tr>
</table>

Сцена для каждой темы выбирается переменными окружения демона:

```bash
AGENT_STATUS_IDLE_CLAUDE=cursor     # robot | cursor
AGENT_STATUS_IDLE_CODEX=typist      # cursor | typist
```

### Wi-Fi и батарея

Для автономной версии на аккумуляторе в правом верхнем углу показываются сигнал Wi-Fi (пиксельный «веер», который бегает при подключении) и заряд батареи: зелёный выше 50%, оранжевый от 21 до 50%, красный 20% и ниже.

<p align="center">
  <img src="docs/status_icons.png" width="536" alt="Экран задачи с индикаторами Wi-Fi и батареи"><br>
  <img src="docs/battery_states.png" width="536" alt="Батарея на 78, 35 и 12 процентах">
</p>

> **Превью дизайна.** Тема Codex, сцены ожидания и индикаторы нарисованы скриптами из [`tools/`](tools/) — это эталон таймингов, кривых и спрайтов. Прошивка сейчас рисует экран задачи в теме Claude; перенос тем и сцен в LVGL — следующий шаг.

## Как это работает

```
Claude Code ─┐
             ├─ хук ─▶ hooks/forward.py ─ HTTP ─▶ host/daemon.py ─ USB ─▶ ESP32-S3
Codex ───────┘                                     └ adapters/claude.py, codex.py
```

1. Хуки плагина вызывают `hooks/forward.py` на каждое событие агента.
2. Хук пересылает событие локальному демону на `127.0.0.1:8765` и сразу завершается, поэтому агент не тормозит. Если демон не запущен, хук сам его поднимает.
3. Демон переводит событие в состояние экрана через адаптер конкретного агента и отправляет плате строку JSON по USB.
4. Прошивка не знает внутренностей агентов: она рисует `state`, `title`, `step`, `done` и `total`, а тему и сцену ожидания берёт из полей `agent` и `idle`.

## Железо

- [LilyGO T-Display-S3 AMOLED](https://github.com/Xinyuan-LilyGO/T-Display-S3-AMOLED): ESP32-S3R8, 8 МБ PSRAM, 1,91″ AMOLED 536×240 (RM67162 по QSPI).
- USB-C кабель с передачей данных.

Паять ничего не нужно.

## Установка

### 1. Прошивка

Нужен [ESP-IDF](https://docs.espressif.com/projects/esp-idf/) 5.1 или новее. LVGL 9.2 скачается автоматически через менеджер компонентов.

```bash
cd firmware
idf.py set-target esp32s3
idf.py build flash
```

Если плата не прошивается, зажмите BOOT, нажмите RST и отпустите BOOT.

### 2. Зависимость Python

```bash
pip install pyserial
```

### 3. Плагин

**Claude Code**

```
/plugin marketplace add YOUR_GITHUB_USERNAME/agent-status-bar
/plugin install agent-status-bar@agent-status-bar
```

**Codex**

```bash
codex plugin marketplace add YOUR_GITHUB_USERNAME/agent-status-bar
```

Затем установите **Agent Status Bar** из списка плагинов. Codex не доверяет хукам плагинов автоматически: просмотрите и включите их, когда Codex попросит.

Всё. Первое же событие агента запустит демон, а он найдёт плату по USB VID Espressif.

На Windows в командах хуков указан `python3`. Если Python у вас доступен только как `python`, поправьте команды в `hooks/hooks.json` и `hooks/codex-hooks.json`.

## Попробовать без платы

Откройте [`docs/emulator.html`](docs/emulator.html) в браузере. Это копия интерфейса на JavaScript с теми же цветами, размерами и таймингами, кнопки изображают события хуков.

Демон можно запустить в демо-режиме или проверить через curl:

```bash
python host/daemon.py --demo
curl -X POST "http://127.0.0.1:8765/?agent=claude" -d '{"hook_event_name":"UserPromptSubmit","prompt":"Тест"}'
curl -X POST "http://127.0.0.1:8765/?agent=claude" -d '{"hook_event_name":"Stop"}'
curl http://127.0.0.1:8765/   # текущее состояние
```

## Протокол

Демон шлёт на плату по одной строке JSON на обновление:

```json
{"state":"work","title":"Отрефактори модуль авторизации","step":"Пишу тесты","done":3,"total":5,"agent":"claude","idle":"robot"}
```

`state` принимает значения `idle`, `start`, `work`, `wait` или `done`. Поля `title` и `step` можно не передавать, тогда на экране останется прежний текст. Поле `agent` (`claude` или `codex`) выбирает тему, `idle` — сцену ожидания; оба необязательны. Управлять дисплеем может всё, что умеет писать в последовательный порт, не только агенты.

## Как добавить другого агента

Создайте `host/adapters/<имя>.py` со строкой `NAME` и функцией `handle(event, state, ctx)`, которая обновляет `state` и возвращает `True`, если экран нужно перерисовать. Зарегистрируйте модуль в `host/adapters/__init__.py` и направьте хуки агента на `hooks/forward.py <имя>`.

## Настройка

| Что | Где |
|---|---|
| Цвета состояний | `state_hex()` в `firmware/main/ui_status.c` |
| Подписи состояний | `state_text()` в `firmware/main/ui_status.c` |
| Время до приглушения и яркость | `DIM_AFTER_MS`, `BRIGHT_ON`, `BRIGHT_DIM` в `firmware/main/main.c` |
| Картинка зеркальная или перевёрнута | `LCD_MADCTL` в `firmware/main/display_rm67162.c`: `0x60`, `0xA0`, `0x20`, `0xE0` |
| Полосы или артефакты | снизьте `LCD_FREQ` до 40 МГц там же |
| Шрифт | замените TTF в `firmware/main/fonts/` (имена те же) |
| Порт демона | переменная окружения `AGENT_STATUS_PORT` |
| Последовательный порт | переменная `AGENT_STATUS_SERIAL`, например `COM5` |
| Отключить автозапуск демона | `AGENT_STATUS_AUTOSTART=0` |
| Сцена ожидания, тема Claude | `AGENT_STATUS_IDLE_CLAUDE`: `robot` (по умолчанию) или `cursor` |
| Сцена ожидания, тема Codex | `AGENT_STATUS_IDLE_CODEX`: `cursor` (по умолчанию) или `typist` |

## Как перерисовать превью

```bash
pip install pillow
python tools/render_task.py --theme claude        # docs/claude_task.gif
python tools/render_task.py --theme codex         # docs/codex_task.gif
python tools/render_idle_robot.py                 # docs/claude_idle_robot.gif
python tools/render_idle_cursor.py --theme claude # docs/claude_idle_cursor.gif
python tools/render_idle_cursor.py --theme codex  # docs/codex_idle_cursor.gif
python tools/render_idle_typist.py                # docs/codex_idle_typist.gif
```

Шрифты для скриптов лежат в `tools/fonts/` вместе с лицензиями (Lora — SIL OFL 1.1, DejaVu — лицензия Bitstream Vera).

## Структура

```
.claude-plugin/        манифесты плагина и маркетплейса Claude Code
.codex-plugin/         манифест плагина Codex
.agents/plugins/       манифест маркетплейса Codex
hooks/                 описание хуков и forward.py
host/                  daemon.py и адаптеры агентов
firmware/              проект ESP-IDF (LVGL 9, драйвер RM67162)
docs/                  гифки обеих тем и всех сцен ожидания, эмулятор в браузере
tools/                 скрипты, рисующие все гифки, — эталон для переноса в прошивку
```

## Статус

Демон, адаптеры, выбор сцены ожидания и эмулятор проверены. Прошивка написана по распиновке и протоколу RM67162 из примеров LilyGO и ESPHome, но на реальной плате ещё не запускалась, поэтому при первой сборке могут понадобиться настройки из таблицы выше. Адаптер Codex рассчитан на формат инструмента `update_plan`; если в вашей версии Codex он другой, поправьте `_plan_steps()` в `host/adapters/codex.py`.

Будем рады issue с текстом ошибки или фото экрана.

## Лицензия

[MIT](LICENSE)
