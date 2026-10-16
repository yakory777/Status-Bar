"""
Адаптер OpenAI Codex: события хуков → состояние экрана.

Codex ведёт план задачи через инструмент update_plan:
    {"plan": [{"step": "...", "status": "pending|in_progress|completed"}, ...]}
Если формат в вашей версии Codex отличается, поправьте _plan_steps().
"""
from .common import apply_plan, describe_tool, finish_task, short, start_task

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
        ctx["plan_step"] = None
        start_task(state, ev.get("prompt"))
        return True

    if name in ("PreToolUse", "PostToolUse"):
        tool = ev.get("tool_name", "")
        inp = ev.get("tool_input") or {}
        if tool == "update_plan":
            steps = _plan_steps(inp)
            if steps:
                ctx["plan_step"] = apply_plan(state, steps)
        state["state"] = "work"
        state["step"] = ctx.get("plan_step") or describe_tool(tool, inp)
        return True

    if name == "PermissionRequest":
        state["state"] = "wait"
        inp = ev.get("tool_input") or {}
        what = describe_tool(ev.get("tool_name", ""), inp)
        state["step"] = short("Разрешить: " + what, 60)
        return True

    if name == "Stop":
        finish_task(state)
        return True

    return False
