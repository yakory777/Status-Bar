# Agent Status Bar

[English](README.md) · **Русский**

Физический индикатор прогресса для задач [Claude Code](https://claude.com/claude-code) и [OpenAI Codex](https://developers.openai.com/codex) на ESP32-S3 с AMOLED-дисплеем. Пока агент работает, на столе видно, чем он занят, сколько пунктов плана выполнено и не ждёт ли он вашего подтверждения.

<table align="center">
  <tr>
    <th></th>
    <th>Работа над задачей</th>
    <th>Готов к работе</th>
  </tr>
  <tr>
    <td><b>Claude</b></td>
    <td><img src="docs/firmware/claude/task.gif" width="400" alt="Claude: Работа над задачей"></td>
    <td><img src="docs/firmware/claude/idle_robot.gif" width="400" alt="Claude: Готов к работе"></td>
  </tr>
  <tr>
    <td><b>Codex</b></td>
    <td><img src="docs/firmware/codex/task.gif" width="400" alt="Codex: Работа над задачей"></td>
    <td><img src="docs/firmware/codex/idle_cursor.gif" width="400" alt="Codex: Готов к работе"></td>
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
| Ошибка | 🩷 Розово-красный | 🔴 Красный | Упал инструмент или задача прервалась (лимит запросов, ошибка сервера) |
| Сжатие | 🩵 Голубой | 🔵 Синий | Агент сжимает контекст |
| Ожидание | ⚪ Серый | ⚪ Серый | Задачи нет, играет сцена ожидания |

Анимации сделаны на LVGL: плавная смена цвета, заливка сегментов, пульсация текущего шага (быстрее, когда агент ждёт вас) и волна слева направо при завершении. Через 10 минут простоя маскот засыпает и экран тускнеет, через 30 — гаснет, чтобы AMOLED не выгорал.

### Все экраны в обеих темах

Все гифки здесь отрисованы **настоящим кодом экрана прошивки** в [симуляторе](#симулятор-прошивки), а не нарисованы отдельно — каждый сценарий в обеих темах. Пересобрать все: `python tools/sim/render_docs.py`.

<table align="center">
  <tr>
    <th width="50%">Claude</th>
    <th width="50%">Codex</th>
  </tr>
  <tr>
    <td colspan="2"><b>Задача от старта до финиша</b> — Красный старт, пока агент думает, потом работа: меняется текст шага, заполняются сегменты плана, текущий пульсирует. Запрос разрешения красит всё в жёлтый; на «Готово» полоса заливается волной, пилюля подпрыгивает и летят конфетти.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/task.gif" width="400" alt="Задача от старта до финиша, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/task.gif" width="400" alt="Задача от старта до финиша, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Ошибки</b> — Упавший инструмент трясёт пилюлю статуса и красит шаг в красный; следующий вызов возвращает в работу. Если задача остановилась на лимите запросов или ошибке сервера, экран остаётся красным с причиной.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/error.gif" width="400" alt="Ошибки, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/error.gif" width="400" alt="Ошибки, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Субагенты и сжатие</b> — Бейдж считает запущенных субагентов (×3). Пока контекст сжимается, полоса прогресса «утрамбовывается».</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/compact.gif" width="400" alt="Субагенты и сжатие, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/compact.gif" width="400" alt="Субагенты и сжатие, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Долгое ожидание</b> — Через минуту без ответа в подписи появляется, сколько агент ждёт, а край экрана начинает мигать.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/wait.gif" width="400" alt="Долгое ожидание, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/wait.gif" width="400" alt="Долгое ожидание, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Кнопка: разрешить, отклонить, сцена, звук</b> — Удержали — разрешено, нажали — отклонено (Claude Code, по желанию). Двойное нажатие меняет сцену ожидания, долгое выключает звук — перечёркнутый динамик остаётся в углу.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/button.gif" width="400" alt="Кнопка: разрешить, отклонить, сцена, звук, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/button.gif" width="400" alt="Кнопка: разрешить, отклонить, сцена, звук, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Батарея, зарядка и Wi-Fi</b> — Зелёная выше 50%, оранжевая 21–50%, красная 20% и ниже; при зарядке появляется молния и заливка бежит до полной. Веер Wi-Fi показывает уровень сигнала.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/battery.gif" width="400" alt="Батарея, зарядка и Wi-Fi, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/battery.gif" width="400" alt="Батарея, зарядка и Wi-Fi, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Нет связи</b> — Демон пингует каждые 5 с. После 15 с тишины (ноутбук уснул, кабель выдернут) экран тускнеет и говорит об этом по центру, а не показывает устаревший статус как текущий.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/link_lost.gif" width="400" alt="Нет связи, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/link_lost.gif" width="400" alt="Нет связи, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>В работу и обратно</b> — Пришла задача: маскот выпрыгивает из кадра, выезжает экран задачи. После «Готово» или когда сессия закрылась, экран задачи гаснет и сцена ожидания начинается заново.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/transitions.gif" width="400" alt="В работу и обратно, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/transitions.gif" width="400" alt="В работу и обратно, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Сон</b> — Через 10 минут без событий маскот засыпает, всплывают «z z z», экран тускнеет. Через 30 минут экран гаснет совсем, чтобы AMOLED не выгорал. Любое событие будит.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/sleep.gif" width="400" alt="Сон, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/sleep.gif" width="400" alt="Сон, Codex"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Экран сопряжения</b> — Шестизначный код поверх всего, когда хост присылает <code>{"pair":"482913"}</code>. Готов для режима Wi-Fi, а сам Wi-Fi-транспорт пока не реализован.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/claude/pairing.png" width="400" alt="Экран сопряжения, Claude"></td>
    <td align="center"><img src="docs/firmware/codex/pairing.png" width="400" alt="Экран сопряжения, Codex"></td>
  </tr>
  <tr>
    <td align="center" valign="top"><img src="docs/firmware/sessions.gif" width="400" alt="Несколько сессий"><br><b>Несколько сессий</b><br>Codex работает в одном терминале, Claude спрашивает разрешение в другом: на экране то, что требует вас, остальное — бейдж «+1 сессия», тема следует за сессией на экране.</td>
    <td align="center" valign="top"><img src="docs/firmware/splash.gif" width="400" alt="Заставка"><br><b>Заставка</b><br>Оба маскота падают и пружинят, затем проявляются название и версия. Батарея и Wi-Fi уже в углу.</td>
  </tr>
</table>

### Темы

Экран переключается на тему того агента, который прислал событие последним.

- **Claude** — тёплые оранжевые акценты, антиква Lora в сценах ожидания, DejaVu Sans на экране задачи.
- **Codex** — чёрный, белый и фирменный зелёный ChatGPT `#10A37F`, моноширинный шрифт как в терминале.

> Прошивка переключает по теме цвета, маскотов и сцены ожидания. Моноширинный шрифт для экрана задачи Codex запланирован; пока оба экрана задачи рисуются шрифтом DejaVu Sans.

Маскоты — оригинальные пиксельные персонажи, нарисованные для этого проекта; логотипы и фирменные персонажи не используются.

### Сцены ожидания — на выбор

У каждой темы по две сцены ожидания. Каждая заканчивается тем, что маскот прыгает в камеру и растворяется в цвете темы, после чего сцена бесшовно начинается заново. Гифки записаны с прошивки в симуляторе.

<table align="center">
  <tr>
    <td align="center"><img src="docs/firmware/claude/idle_robot.gif" width="400" alt="Claude · robot"><br><b>Claude · <code>robot</code></b> (по умолчанию)<br>Пиксельный робот падает на текст и скачет по буквам; каждая буква проседает под ним и загорается.</td>
    <td align="center"><img src="docs/firmware/claude/idle_cursor.gif" width="400" alt="Claude · cursor"><br><b>Claude · <code>cursor</code></b><br>Оранжевый курсор просыпается, открывает глаза и печатает строку, оставляя за собой буквы.</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/firmware/codex/idle_cursor.gif" width="400" alt="Codex · cursor"><br><b>Codex · <code>cursor</code></b> (по умолчанию)<br>Курсор терминала оживает и печатает команду; когда он мигает, глаза остаются висеть в воздухе.</td>
    <td align="center"><img src="docs/firmware/codex/idle_typist.gif" width="400" alt="Codex · typist"><br><b>Codex · <code>typist</code></b><br>Слайм сидит за пиксельной клавиатурой, стучит по клавишам двумя лапками и бьёт по Enter.</td>
  </tr>
</table>

Сцена для каждой темы выбирается переменными окружения демона:

```bash
AGENT_STATUS_IDLE_CLAUDE=cursor     # robot | cursor
AGENT_STATUS_IDLE_CODEX=typist      # cursor | typist
```

### Батарея и Wi-Fi

Правый верхний угол одинаковый на всех экранах — на заставке, в сценах ожидания, на экране задачи и при сопряжении. Батарея: зелёная выше 50%, оранжевая от 21 до 50%, красная 20% и ниже; при зарядке рядом появляется молния, а заливка бежит до полной; без аккумулятора корпус пустой с подписью «USB». Wi-Fi: точка и три дуги по уровню сигнала; пока плата работает по USB (режим Wi-Fi ещё не реализован), веер тусклый и перечёркнут. Перечёркнутый динамик — звук выключен. В финале сцены ожидания, когда экран заливается цветом, индикаторы на секунду уступают.

Напряжение меряется на GPIO4 через делитель 1:2 на плате и переводится в проценты по кривой разряда Li-ion (`firmware/main/platform_esp.c`).

### Кнопка и звук

Кнопка BOOT на плате (GPIO0) работает без пайки:

| Нажатие | Что делает |
|---|---|
| Короткое | Переключает между сценой ожидания и последней задачей |
| Двойное | Следующая сцена ожидания для текущей темы; выбор уходит демону и запоминается |
| Долгое (1,2 с) | Выключает и включает звук |
| Любое, пока экран спит | Будит его |

**Разрешение с платы (Claude Code, по желанию).** Задайте `AGENT_STATUS_BUTTON_APPROVE=1`, и когда Claude спросит разрешение, на экране появится «Удержать — разрешить · нажать — отклонить» с полосой заполнения. Удержали — разрешено, нажали — отклонено. Если за `AGENT_STATUS_APPROVE_WAIT` секунд (по умолчанию 20) никто не нажал, хук уступает, и Claude Code показывает свой обычный запрос — то есть на это время запрос в терминале появляется чуть позже. Хуки Codex не умеют отвечать на запросы разрешения, поэтому там экран только показывает, что агент ждёт.

Пищалка не обязательна: пассивный зуммер через резистор ~100 Ом между свободным GPIO (например, 43 или 44) и GND, затем *Buzzer GPIO* в `idf.py menuconfig → Agent Status Bar`. Плата пищит на «ждёт вас», «готово» и «ошибка», повторяет напоминание каждую минуту, пока вас нет, и щёлкает на нажатиях. Там же можно задать пин второй кнопки.

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

### Корпус

В `hardware/case/` — корпус из трёх деталей для 3D-печати: лоток с местом под небольшой Li-ion аккумулятор под платой и вырезами для USB-C и боковых кнопок, рамка экрана на защёлке и подставка с наклоном 22°. STL готовы к слайсеру (PLA, слой 0,2 мм, без поддержек; рамку печатать лицом вниз). В сборе — около 65 × 30 × 19 мм.

<p align="center">
  <img src="hardware/case/preview.png" width="720" alt="Лоток, рамка и подставка">
</p>

Размеры взяты из характеристик платы (60 × 25,5 × 10 мм), а не с чертежа — измерьте свою плату и поправьте `PARAMS` в `hardware/case/case.py` (или переменные в `case.scad` для OpenSCAD), затем `python hardware/case/case.py` (нужны `numpy` и `matplotlib`) пересоберёт STL. Официальная модель корпуса от LilyGO есть в [репозитории платы](https://github.com/Xinyuan-LilyGO/T-Display-S3-AMOLED) (`shell/`).

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

### Симулятор прошивки

`tools/sim/` собирает код интерфейса прошивки (`firmware/main/ui_*.c`, `protocol.c`) вместе с LVGL 9.2 прямо на компьютере, проигрывает сценарий и сохраняет гифку. Ни платы, ни ESP-IDF не нужно:

```bash
pip install pillow                     # плюс cmake и компилятор C
python tools/sim/render.py tools/sim/scenarios/error.txt error.gif
python tools/sim/render.py tools/sim/scenarios/wait_escalation.txt wait.gif --clip 57-68
```

Сценарий — текстовый файл из строк `<время_мс> <JSON>`, ровно то, что демон шлёт плате. CI прогоняет все сценарии из `tools/sim/scenarios/`, так что правка, ломающая код экрана, не пройдёт сборку.

### Эмулятор в браузере

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
{"state":"work","title":"Отрефактори модуль авторизации","step":"Пишу тесты","done":3,"total":5,"sub":2,"others":1,"agent":"claude","idle":"robot"}
{"ping":1}
```

| Поле | Значение |
|---|---|
| `state` | `idle`, `start`, `work`, `wait`, `done`, `error`, `compact` |
| `title`, `step` | Запрос и текущий шаг; не передали — остаётся прежний текст |
| `done`, `total` | Прогресс по плану, `total` ограничен 1–12 |
| `sub` | Работающие субагенты (бейдж скрыт при 0) |
| `others` | Другие активные сессии (бейдж скрыт при 0) |
| `agent` | Тема: `claude` или `codex` |
| `idle` | Сцена ожидания для темы |
| `ping` | Признак жизни, каждые 5 с; 15 с тишины — «Нет связи» |
| `pair` | Шестизначный код сопряжения; `""` скрывает экран сопряжения |
| `approve` | `true` — плата предлагает «удержать — разрешить / нажать — отклонить» для текущего ожидания |

Обратно плата присылает строки на нажатия: `{"button":"approve"}`, `{"button":"deny"}`, `{"button":"scene_next","scene":"cursor"}`.

Все поля необязательны, плата помнит последнее значение. Управлять дисплеем может всё, что умеет писать в последовательный порт, не только агенты.

### Какие события слушает демон

| На экране | Claude Code | Codex |
|---|---|---|
| Старт | `UserPromptSubmit` | `UserPromptSubmit` |
| Работа, текущий шаг | `PreToolUse`, `PostToolUse` | `PreToolUse`, `PostToolUse` |
| Прогресс по плану | `TaskCreated`, `TaskCompleted`, `TaskUpdate`, старый `TodoWrite` | `update_plan` |
| Ждёт вас | `PermissionRequest`, `Notification` (запрос разрешения или ввода) | `PermissionRequest` |
| Ошибка | `PostToolUseFailure`, `StopFailure` | ненулевой код выхода в `PostToolUse` |
| Субагенты | `SubagentStart`, `SubagentStop` | `SubagentStart`, `SubagentStop` |
| Сжатие | `PreCompact`, `PostCompact` | `PreCompact`, `PostCompact` |
| Готово | `Stop` | `Stop` |
| Сессия закрыта | `SessionEnd` | — |

## Как добавить другого агента

Создайте `host/adapters/<имя>.py` со строкой `NAME` и функцией `handle(event, state, ctx)`, которая обновляет `state` и возвращает `True`, если экран нужно перерисовать. Зарегистрируйте модуль в `host/adapters/__init__.py` и направьте хуки агента на `hooks/forward.py <имя>`.

## Настройка

| Что | Где |
|---|---|
| Цвета состояний по темам | `THEMES` в `firmware/main/ui_status.c` |
| Подписи состояний | `STATE_TEXT` в `firmware/main/ui_status.c` |
| Когда ожидание начинает напоминать | `UI_WAIT_ESCALATE_MS` в `firmware/main/ui_status.h` (60 с) |
| Через сколько тишины «Нет связи» | `PROTO_LINK_TIMEOUT_MS` в `firmware/main/protocol.h` (15 с) |
| Сколько висит «Готово» до сцены ожидания | `UI_DONE_TO_IDLE_MS` в `firmware/main/ui_screen.h` (90 с) |
| Маскот засыпает, экран тускнеет | `UI_SLEEP_AFTER_MS`, `UI_BRIGHT_SLEEP` там же (10 мин) |
| Экран гаснет | `UI_OFF_AFTER_MS` там же (30 мин) |
| Пин батареи и пороги | `BAT_ADC_CHANNEL`, `BAT_NO_BATTERY_MV`, `BAT_USB_MV` в `firmware/main/platform_esp.c` |
| Обычная яркость | `UI_BRIGHT_ON` в `firmware/main/ui_screen.h` |
| Картинка зеркальная или перевёрнута | `LCD_MADCTL` в `firmware/main/display_rm67162.c`: `0x60`, `0xA0`, `0x20`, `0xE0` |
| Полосы или артефакты | снизьте `LCD_FREQ` до 40 МГц там же |
| Шрифт | замените TTF в `firmware/main/fonts/` (имена те же) |
| Порт демона | переменная окружения `AGENT_STATUS_PORT` |
| Последовательный порт | переменная `AGENT_STATUS_SERIAL`, например `COM5` |
| Отключить автозапуск демона | `AGENT_STATUS_AUTOSTART=0` |
| Сцена ожидания, тема Claude | `AGENT_STATUS_IDLE_CLAUDE`: `robot` (по умолчанию) или `cursor` |
| Сцена ожидания, тема Codex | `AGENT_STATUS_IDLE_CODEX`: `cursor` (по умолчанию) или `typist` |
| Разрешение с платы | `AGENT_STATUS_BUTTON_APPROVE=1` (только Claude Code) |
| Сколько хук ждёт кнопку | `AGENT_STATUS_APPROVE_WAIT`, секунды (20, максимум 120) |
| Пины кнопки, второй кнопки, пищалки | `idf.py menuconfig → Agent Status Bar` |
| Время долгого и двойного нажатия | `UI_LONG_PRESS_MS`, `UI_DOUBLE_CLICK_MS` в `firmware/main/ui_input.h` |

## Как перерисовать превью

Гифки прошивки (всё в `docs/firmware/`, обе темы) делает симулятор:

```bash
pip install pillow
python tools/sim/render_docs.py                   # все, ~1,5 мин
python tools/sim/render_docs.py task button       # только эти
```

Исходные превью дизайна на Python:

```bash
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
host/                  daemon.py, sessions.py (несколько сессий сразу) и адаптеры агентов
firmware/main/         проект ESP-IDF, LVGL 9:
  ui_status.c            экран задачи, темы, состояния сценариев
  ui_scene_*.c           сцены ожидания (robot, cursor, typist), ui_scene.c их запускает
  ui_screen.c            заставка, переходы, конфетти, сон, сопряжение
  ui_icons.c             индикаторы батареи и Wi-Fi
  protocol.c             строки JSON от хоста (общий с симулятором)
  ui_input.c, ui_sound.c действия кнопки и мелодии
  platform_esp.c         яркость, АЦП батареи, пищалка; input_esp.c — кнопки; display_rm67162.c — драйвер панели
hardware/case/         корпус для 3D-печати: case.py (генератор), case.scad, STL, превью
docs/firmware/         гифки прошивки: claude/ и codex/ — каждый экран в обеих темах; эмулятор в браузере в docs/
tools/                 скрипты превью дизайна
tools/sim/             симулятор прошивки: настоящий код экрана + LVGL на ПК, сценарии, экспорт в GIF
```

## Статус

Демон, адаптеры, учёт сессий и выбор сцены ожидания покрыты тестами. Все экраны, сцены и анимации прогоняются в симуляторе прошивки и в CI. Драйвер дисплея написан по распиновке и протоколу RM67162 из примеров LilyGO и ESPHome, но на реальной плате ещё не запускалась, поэтому при первой сборке могут понадобиться настройки из таблицы выше. Адаптер Codex рассчитан на формат инструмента `update_plan`; если в вашей версии Codex он другой, поправьте `_plan_steps()` в `host/adapters/codex.py`.

Будем рады issue с текстом ошибки или фото экрана.

## Лицензия

[MIT](LICENSE)
