"""Адаптер Claude Code: события хуков → состояние экрана."""
from .common import apply_plan, describe_tool, finish_task, reset, short, start_task

NAME = "claude"


def handle(ev, state, ctx):
    """Обновляет state по событию. Возвращает True, если экран нужно перерисовать."""
    name = ev.get("hook_event_name", "")

    if name == "UserPromptSubmit":
        ctx["plan_step"] = None
        start_task(state, ev.get("prompt"))
        return True

    if name in ("PreToolUse", "PostToolUse"):
        tool = ev.get("tool_name", "")
        inp = ev.get("tool_input") or {}
        if tool == "TodoWrite" and isinstance(inp.get("todos"), list):
            steps = [
                (t.get("activeForm") or t.get("content") or "", t.get("status"))
                for t in inp["todos"]
            ]
            ctx["plan_step"] = apply_plan(state, steps)
        state["state"] = "work"
        state["step"] = ctx.get("plan_step") or describe_tool(tool, inp)
        return True

    if name in ("Notification", "PermissionRequest"):
        state["state"] = "wait"
        state["step"] = short(ev.get("message") or "Нужно ваше подтверждение", 60)
        return True

    if name == "Stop":
        finish_task(state)
        return True

    if name == "SessionEnd":
        reset(state)
        return True

    return False
