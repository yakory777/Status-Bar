"""Общие помощники для адаптеров: состояние экрана, план задачи, описание действий."""
import os
import re

IDLE = {
    "state": "idle",
    "title": "Жду задачу",
    "step": "Отправьте задачу агенту",
    "done": 0,
    "total": 1,
    "sub": 0,
}

# Состояния, в которых задача ещё идёт
ACTIVE = ("start", "work", "wait", "error", "compact")


def short(text, n):
    """Схлопывает пробелы и обрезает строку до n символов."""
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def start_task(state, ctx, prompt):
    state.update(
        state="start",
        title=short(prompt, 60) or "Новая задача",
        step="Думает…",
        done=0,
        total=1,
        sub=0,
    )
    ctx["plan_step"] = None
    ctx["sub"] = 0
    plan = ctx.get("tasks")
    if plan and all(t["status"] == "completed" for t in plan.values()):
        plan.clear()                      # прошлый план закрыт — начинаем с чистого листа
    if plan:
        sync_tasks(state, ctx)


def finish_task(state, ctx):
    state["state"] = "done"
    state["done"] = state["total"]
    state["step"] = "Задача выполнена"
    state["sub"] = 0
    ctx["sub"] = 0


def fail(state, step):
    state["state"] = "error"
    state["step"] = short(step, 60)


def reset(state, ctx):
    state.update(IDLE)
    ctx.clear()


def apply_plan(state, steps):
    """
    steps — список (текст, статус), статус: pending | in_progress | completed.
    Возвращает текст текущего шага или None.
    """
    if not steps:
        return None
    state["total"] = len(steps)
    state["done"] = sum(1 for _, st in steps if st == "completed")
    cur = next((text for text, st in steps if st == "in_progress"), None)
    return short(cur, 60) if cur else None


# ---------- план через задачи (TaskCreate / TaskUpdate / TaskCreated / TaskCompleted) ----------

def task_upsert(ctx, task_id, subject=None, active_form=None, status=None):
    tasks = ctx.setdefault("tasks", {})
    key = str(task_id) if task_id is not None else f"auto{len(tasks) + 1}"
    t = tasks.setdefault(key, {"subject": "", "active": "", "status": "pending"})
    if subject:
        t["subject"] = subject
    if active_form:
        t["active"] = active_form
    if status == "deleted":
        tasks.pop(key, None)
    elif status:
        t["status"] = status
    return key


def sync_tasks(state, ctx):
    """Переносит план из ctx["tasks"] на экран. Возвращает текущий шаг или None."""
    tasks = ctx.get("tasks") or {}
    steps = [(t["active"] or t["subject"], t["status"]) for t in tasks.values()]
    ctx["plan_step"] = apply_plan(state, steps)
    return ctx["plan_step"]


# ---------- субагенты ----------

def subagent(state, ctx, delta):
    ctx["sub"] = max(0, ctx.get("sub", 0) + delta)
    state["sub"] = ctx["sub"]


# ---------- описание действий ----------

def describe_tool(name, inp):
    """Человекочитаемое описание вызова инструмента."""
    inp = inp if isinstance(inp, dict) else {}
    name = name or ""
    path = inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or ""
    base = os.path.basename(str(path))

    if name in ("Edit", "MultiEdit", "apply_patch"):
        return f"Правит {base}" if base else "Правит файлы"
    if name == "Write":
        return f"Пишет {base}"
    if name in ("Read", "read_file"):
        return f"Читает {base}"
    if name in ("Bash", "shell", "exec_command", "local_shell", "PowerShell"):
        cmd = inp.get("command") or inp.get("cmd") or ""
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
        return "$ " + short(cmd, 48) if cmd else "Выполняет команду"
    if name in ("Grep", "Glob"):
        return "Ищет: " + short(inp.get("pattern", ""), 40)
    if name in ("WebSearch", "WebFetch", "web_search"):
        return "Ищет в интернете"
    if name in ("Task", "Agent"):
        return "Субагент: " + short(inp.get("description", ""), 40)
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate", "update_plan"):
        return "Обновляет план"
    if name.startswith("mcp__"):
        return "Инструмент: " + short(name.split("__")[-1], 40)
    return short(name, 48) or "Работает"


def describe_permission(name, inp):
    """Текст запроса разрешения: «Разрешить запись README.md?»."""
    inp = inp if isinstance(inp, dict) else {}
    name = name or ""
    base = os.path.basename(str(inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or ""))
    if name in ("Bash", "shell", "exec_command", "local_shell", "PowerShell"):
        cmd = inp.get("command") or inp.get("cmd") or ""
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
        return short(f"Разрешить: $ {cmd}" if cmd else "Разрешить команду?", 60)
    phrases = {
        "Write": "запись", "Edit": "правку", "MultiEdit": "правку", "apply_patch": "правку",
        "NotebookEdit": "правку", "Read": "чтение",
    }
    if name in phrases:
        return short(f"Разрешить {phrases[name]} {base}?" if base else f"Разрешить {phrases[name]}?", 60)
    if name in ("WebFetch", "WebSearch", "web_search"):
        return "Разрешить доступ в интернет?"
    if name.startswith("mcp__"):
        return short("Разрешить инструмент " + name.split("__")[-1] + "?", 60)
    return short(f"Разрешить {name}?" if name else "Нужно ваше подтверждение", 60)


_EXIT_RE = re.compile(r"exit(?:ed)?(?: with)?(?: code)?[:\s]+(-?\d+)", re.IGNORECASE)


def tool_failed(resp):
    """Похоже ли, что инструмент завершился с ошибкой (для агентов без отдельного события)."""
    if isinstance(resp, dict):
        for k in ("exit_code", "exitCode", "returncode", "status_code"):
            v = resp.get(k)
            if isinstance(v, int) and v != 0:
                return True
        if resp.get("success") is False or resp.get("is_error") is True:
            return True
        if resp.get("error"):
            return True
        for k in ("output", "stdout", "content"):
            if isinstance(resp.get(k), str) and tool_failed(resp[k]):
                return True
        return False
    if isinstance(resp, str):
        m = _EXIT_RE.search(resp[:400])
        return bool(m and int(m.group(1)) != 0)
    return False


STOP_FAILURE_TEXT = {
    "rate_limit": "Лимит запросов, пауза",
    "overloaded": "Сервер перегружен",
    "authentication_failed": "Ошибка входа",
    "oauth_org_not_allowed": "Нет доступа к организации",
    "account_on_hold": "Аккаунт приостановлен",
    "billing_error": "Проблема с оплатой",
    "invalid_request": "Некорректный запрос",
    "model_not_found": "Модель не найдена",
    "server_error": "Ошибка сервера",
    "max_output_tokens": "Слишком длинный ответ",
    "cloud_credential_error": "Ошибка облачного доступа",
}
