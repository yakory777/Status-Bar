"""
Тексты, которые хост отправляет на экран (шаг, заголовок, причины ошибок), на двух языках.

Язык выбирается один раз при старте демона: language = "en" | "ru" в конфиге,
AGENT_STATUS_LANG или по системной локали (см. config.py). Подписи самой платы
(«В работе», «Ждёт вас») переводит прошивка — ей уходит поле "lang".
"""
LANGS = ("en", "ru")

TEXT = {
    "new_task":        {"en": "New task",                    "ru": "Новая задача"},
    "thinking":        {"en": "Thinking…",                   "ru": "Думает…"},
    "task_done":       {"en": "Task complete",               "ru": "Задача выполнена"},
    "task_stopped":    {"en": "Task interrupted",            "ru": "Задача прервана"},
    "error_prefix":    {"en": "Error: {what}",               "ru": "Ошибка: {what}"},
    "needs_you":       {"en": "Needs your confirmation",     "ru": "Нужно ваше подтверждение"},
    "compacting":      {"en": "Compacting context",          "ru": "Сжимаю контекст"},
    "compacting_auto": {"en": "Compacting context (auto)",   "ru": "Сжимаю контекст (авто)"},
    "compacted":       {"en": "Context compacted, going on", "ru": "Контекст сжат, продолжаю"},
    "denied_by_button": {"en": "Denied with the status bar button",
                         "ru": "Отклонено кнопкой на статус-баре"},

    # что делает агент
    "edits":           {"en": "Editing {file}",              "ru": "Правит {file}"},
    "edits_files":     {"en": "Editing files",               "ru": "Правит файлы"},
    "writes":          {"en": "Writing {file}",              "ru": "Пишет {file}"},
    "reads":           {"en": "Reading {file}",              "ru": "Читает {file}"},
    "runs_command":    {"en": "Running a command",           "ru": "Выполняет команду"},
    "searches":        {"en": "Searching: {pattern}",        "ru": "Ищет: {pattern}"},
    "web":             {"en": "Searching the web",           "ru": "Ищет в интернете"},
    "subagent":        {"en": "Subagent: {what}",            "ru": "Субагент: {what}"},
    "plan":            {"en": "Updating the plan",           "ru": "Обновляет план"},
    "tool":            {"en": "Tool: {name}",                "ru": "Инструмент: {name}"},
    "working":         {"en": "Working",                     "ru": "Работает"},

    # запросы разрешения
    "allow_cmd":       {"en": "Allow: $ {cmd}",              "ru": "Разрешить: $ {cmd}"},
    "allow_cmd_any":   {"en": "Allow a command?",            "ru": "Разрешить команду?"},
    "allow_write":     {"en": "Allow writing {file}?",       "ru": "Разрешить запись {file}?"},
    "allow_write_any": {"en": "Allow writing?",              "ru": "Разрешить запись?"},
    "allow_edit":      {"en": "Allow editing {file}?",       "ru": "Разрешить правку {file}?"},
    "allow_edit_any":  {"en": "Allow editing?",              "ru": "Разрешить правку?"},
    "allow_read":      {"en": "Allow reading {file}?",       "ru": "Разрешить чтение {file}?"},
    "allow_read_any":  {"en": "Allow reading?",              "ru": "Разрешить чтение?"},
    "allow_web":       {"en": "Allow web access?",           "ru": "Разрешить доступ в интернет?"},
    "allow_tool":      {"en": "Allow tool {name}?",          "ru": "Разрешить инструмент {name}?"},
    "allow_named":     {"en": "Allow {name}?",               "ru": "Разрешить {name}?"},

    # почему задача остановилась (StopFailure)
    "stop_rate_limit":            {"en": "Rate limited, pausing",     "ru": "Лимит запросов, пауза"},
    "stop_overloaded":            {"en": "Server overloaded",         "ru": "Сервер перегружен"},
    "stop_authentication_failed": {"en": "Sign-in failed",            "ru": "Ошибка входа"},
    "stop_oauth_org_not_allowed": {"en": "No access to organization", "ru": "Нет доступа к организации"},
    "stop_account_on_hold":       {"en": "Account on hold",           "ru": "Аккаунт приостановлен"},
    "stop_billing_error":         {"en": "Billing problem",           "ru": "Проблема с оплатой"},
    "stop_invalid_request":       {"en": "Invalid request",           "ru": "Некорректный запрос"},
    "stop_model_not_found":       {"en": "Model not found",           "ru": "Модель не найдена"},
    "stop_server_error":          {"en": "Server error",              "ru": "Ошибка сервера"},
    "stop_max_output_tokens":     {"en": "Response too long",         "ru": "Слишком длинный ответ"},
    "stop_cloud_credential_error": {"en": "Cloud credentials error",  "ru": "Ошибка облачного доступа"},

    # демо (python host/daemon.py --demo)
    "demo_prompt":     {"en": "Refactor the auth module",    "ru": "Отрефактори модуль авторизации"},
    "demo_steps":      {"en": "Exploring the project|Editing the auth module|Updating token logic|Writing tests|Running tests",
                        "ru": "Изучаю структуру проекта|Правлю модуль авторизации|Обновляю логику токенов|Пишу тесты|Запускаю тесты"},
    "demo_permission": {"en": "Allow running npm test?",     "ru": "Разрешить запуск npm test?"},
}

_lang = "en"


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGS else "en"


def language():
    return _lang


def t(key, **kw):
    s = TEXT[key].get(_lang) or TEXT[key]["en"]
    return s.format(**kw) if kw else s


def stop_reason(kind):
    """Причина StopFailure → текст; неизвестная — «Задача прервана»."""
    key = f"stop_{kind}"
    return t(key) if key in TEXT else t("task_stopped")
