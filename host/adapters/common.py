"""Общие помощники для адаптеров: состояние экрана, план задачи, описание действий."""
import os
import re

from i18n import stop_reason, t

# Заголовок и шаг для ожидания не шлём: плата держит свою подпись на своём языке
IDLE = {
    "state": "idle",
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
        title=short(prompt, 60) or t("new_task"),
        step=t("thinking"),
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
<<<<<<< HEAD
    state["step"] = t("task_done")
=======
    state["step"] = "Задача выполнена"
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
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
        return t("edits", file=base) if base else t("edits_files")
    if name == "Write":
        return t("writes", file=base)
    if name in ("Read", "read_file"):
<<<<<<< HEAD
        return t("reads", file=base)
=======
        return f"Читает {base}"
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    if name in ("Bash", "shell", "exec_command", "local_shell", "PowerShell"):
        cmd = inp.get("command") or inp.get("cmd") or ""
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
        return "$ " + short(cmd, 48) if cmd else t("runs_command")
    if name in ("Grep", "Glob"):
        return t("searches", pattern=short(inp.get("pattern", ""), 40))
    if name in ("WebSearch", "WebFetch", "web_search"):
        return t("web")
    if name in ("Task", "Agent"):
<<<<<<< HEAD
        return t("subagent", what=short(inp.get("description", ""), 40))
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate", "update_plan"):
        return t("plan")
    if name.startswith("mcp__"):
        return t("tool", name=short(name.split("__")[-1], 40))
    return short(name, 48) or t("working")
=======
        return "Субагент: " + short(inp.get("description", ""), 40)
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate", "update_plan"):
        return "Обновляет план"
    if name.startswith("mcp__"):
        return "Инструмент: " + short(name.split("__")[-1], 40)
    return short(name, 48) or "Работает"
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046


def describe_permission(name, inp):
    """Текст запроса разрешения: «Разрешить запись README.md?»."""
    inp = inp if isinstance(inp, dict) else {}
    name = name or ""
    base = os.path.basename(str(inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or ""))
    if name in ("Bash", "shell", "exec_command", "local_shell", "PowerShell"):
        cmd = inp.get("command") or inp.get("cmd") or ""
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
<<<<<<< HEAD
        return short(t("allow_cmd", cmd=cmd) if cmd else t("allow_cmd_any"), 60)
    kinds = {
        "Write": "write", "Edit": "edit", "MultiEdit": "edit", "apply_patch": "edit",
        "NotebookEdit": "edit", "Read": "read",
    }
    if name in kinds:
        k = kinds[name]
        return short(t(f"allow_{k}", file=base) if base else t(f"allow_{k}_any"), 60)
    if name in ("WebFetch", "WebSearch", "web_search"):
        return t("allow_web")
    if name.startswith("mcp__"):
        return short(t("allow_tool", name=name.split("__")[-1]), 60)
    return short(t("allow_named", name=name) if name else t("needs_you"), 60)
=======
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
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046


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


<<<<<<< HEAD
def stop_failure_text(kind):
    """Причина StopFailure (rate_limit, overloaded, …) → текст на экран."""
    return stop_reason(kind)
=======
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
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
