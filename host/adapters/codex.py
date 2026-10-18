"""
Адаптер OpenAI Codex: события хуков → состояние экрана.

Codex ведёт план задачи через инструмент update_plan:
    {"plan": [{"step": "...", "status": "pending|in_progress|completed"}, ...]}
Отдельного события об ошибке инструмента у Codex нет — смотрим на tool_response в PostToolUse.
Если формат в вашей версии Codex отличается, поправьте _plan_steps() или common.tool_failed().
"""
from .common import (apply_plan, describe_permission, describe_tool, fail, finish_task, start_task, subagent,
                     tool_failed)
<<<<<<< HEAD
from i18n import t
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046

NAME = "codex"


def _plan_steps(inp):
    plan = inp.get("plan") if isinstance(inp, dict) else None
    if not isinstance(plan, list):
        return None
    steps = []
    for item in plan:
        if isinstance(item, dict):
            steps.append((item.get("step") or item.get("content") or "", item.get("status")))
    return steps


def handle(ev, state, ctx):
    name = ev.get("hook_event_name", "")

    if name == "UserPromptSubmit":
        start_task(state, ctx, ev.get("prompt"))
        return True

    if name in ("PreToolUse", "PostToolUse"):
        tool = ev.get("tool_name", "")
        inp = ev.get("tool_input") or {}
        if tool == "update_plan":
            steps = _plan_steps(inp)
            if steps:
                ctx["plan_step"] = apply_plan(state, steps)
        if name == "PostToolUse" and tool_failed(ev.get("tool_response")):
<<<<<<< HEAD
            fail(state, t("error_prefix", what=describe_tool(tool, inp)))
=======
            fail(state, "Ошибка: " + describe_tool(tool, inp))
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
            return True
        state["state"] = "work"
        state["step"] = ctx.get("plan_step") or describe_tool(tool, inp)
        return True

    if name == "PermissionRequest":
        state["state"] = "wait"
        state["step"] = describe_permission(ev.get("tool_name", ""), ev.get("tool_input") or {})
        return True

    if name == "SubagentStart":
        subagent(state, ctx, +1)
        return True

    if name == "SubagentStop":
        subagent(state, ctx, -1)
        return True

    if name == "PreCompact":
        state["state"] = "compact"
<<<<<<< HEAD
        state["step"] = t("compacting_auto" if ev.get("trigger") == "auto" else "compacting")
=======
        state["step"] = "Сжимаю контекст" + (" (авто)" if ev.get("trigger") == "auto" else "")
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        return True

    if name == "PostCompact":
        state["state"] = "work"
<<<<<<< HEAD
        state["step"] = ctx.get("plan_step") or t("compacted")
=======
        state["step"] = ctx.get("plan_step") or "Контекст сжат, продолжаю"
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        return True

    if name == "Stop":
        finish_task(state, ctx)
        return True

    return False
