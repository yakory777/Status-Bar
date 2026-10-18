"""Адаптер Claude Code: события хуков → состояние экрана."""
from .common import (stop_failure_text, apply_plan, describe_permission, describe_tool, fail, finish_task, reset,
                     short, start_task, subagent, sync_tasks, task_upsert)
from i18n import t

NAME = "claude"

# Уведомления, которые значат «нужен человек»
WAIT_NOTIFICATIONS = {"permission_prompt", "elicitation_dialog", "elicitation_url_dialog",
                      "agent_needs_input"}


def _plan_from_tools(tool, inp, resp, ctx):
    """План задачи: старый TodoWrite или новые TaskCreate/TaskUpdate. True — план изменился."""
    if tool == "TodoWrite" and isinstance(inp.get("todos"), list):
        ctx["tasks"] = {}
        for i, t in enumerate(inp["todos"]):
            task_upsert(ctx, i, t.get("content"), t.get("activeForm"), t.get("status"))
        return True
    if tool == "TaskCreate":
        tid = None
        if isinstance(resp, dict):
            tid = resp.get("taskId") or resp.get("task_id") or resp.get("id")
        if tid is None:
            return False                  # id появится в событии TaskCreated
        task_upsert(ctx, tid, inp.get("subject"), inp.get("activeForm"))
        return True
    if tool == "TaskUpdate" and inp.get("taskId") is not None:
        task_upsert(ctx, inp["taskId"], inp.get("subject"), inp.get("activeForm"), inp.get("status"))
        return True
    return False


def handle(ev, state, ctx):
    """Обновляет state по событию. Возвращает True, если экран нужно перерисовать."""
    name = ev.get("hook_event_name", "")

    if name == "UserPromptSubmit":
        start_task(state, ctx, ev.get("prompt"))
        return True

    if name in ("PreToolUse", "PostToolUse"):
        tool = ev.get("tool_name", "")
        inp = ev.get("tool_input") or {}
        if _plan_from_tools(tool, inp, ev.get("tool_response"), ctx):
            sync_tasks(state, ctx)
        state["state"] = "work"
        state["step"] = ctx.get("plan_step") or describe_tool(tool, inp)
        return True

    if name == "PostToolUseFailure":
        what = describe_tool(ev.get("tool_name", ""), ev.get("tool_input") or {})
        fail(state, t("error_prefix", what=what))
        return True

    if name in ("TaskCreated", "TaskCompleted"):
        task_upsert(ctx, ev.get("task_id"), ev.get("task_subject"),
                    status="completed" if name == "TaskCompleted" else None)
        step = sync_tasks(state, ctx)
        if step and state["state"] in ("work", "start"):
            state["step"] = step
        return True

    if name == "Notification":
        kind = ev.get("notification_type") or ev.get("type")
        if kind and kind not in WAIT_NOTIFICATIONS:
            return False                  # idle_prompt, auth_success и прочее — не повод будить
        state["state"] = "wait"
        state["step"] = short(ev.get("message") or t("needs_you"), 60)
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
        state["step"] = t("compacting_auto" if ev.get("trigger") == "auto" else "compacting")
        return True

    if name == "PostCompact" or (name == "SessionStart" and ev.get("source") == "compact"):
        state["state"] = "work"
        state["step"] = ctx.get("plan_step") or t("compacted")
        return True

    if name == "Stop":
        finish_task(state, ctx)
        return True

    if name == "StopFailure":
        kind = ev.get("error_type") or ev.get("reason") or ev.get("error") or ev.get("matcher")
        fail(state, stop_failure_text(kind))
        state["sub"] = 0
        ctx["sub"] = 0
        return True

    if name == "SessionEnd":
        reset(state, ctx)
        return True

    return False


# совместимость со старым импортом
__all__ = ["NAME", "handle", "apply_plan"]
