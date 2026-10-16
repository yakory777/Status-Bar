"""Общие помощники для адаптеров: состояние экрана и описание действий."""
import os

IDLE = {
    "state": "idle",
    "title": "Жду задачу",
    "step": "Отправьте задачу агенту",
    "done": 0,
    "total": 1,
}


def short(text, n):
    """Схлопывает пробелы и обрезает строку до n символов."""
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def start_task(state, prompt):
    state.update(
        state="start",
        title=short(prompt, 60) or "Новая задача",
        step="Думает…",
        done=0,
        total=1,
    )


def finish_task(state):
    state["state"] = "done"
    state["done"] = state["total"]
    state["step"] = "Задача выполнена"


def reset(state):
    state.update(IDLE)


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
    if name in ("Bash", "shell", "exec_command", "local_shell"):
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
    if name.startswith("mcp__"):
        return "Инструмент: " + short(name.split("__")[-1], 40)
    return short(name, 48) or "Работает"
