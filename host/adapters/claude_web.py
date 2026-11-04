"""Адаптер чата claude.ai в браузере: события расширения browser/ → состояние экрана.

Хуков в чате нет, поэтому расширение само смотрит на страницу и присылает простые события
(POST /?agent=claude-web, session_id — вкладка браузера):

  WebPrompt   {"prompt": "...", "title": "..."}   отправлен новый вопрос
  WebBusy     {"phase": "thinking"|"writing"|"tool", "tool": "..."}   Claude думает, пишет или что-то делает
  WebWait     {"message": "..."}                  ждёт разрешения (окно «Разрешить» для инструмента)
  WebDone     {}                                  ответ готов
  WebError    {"message": "..."}                  ответ оборвался
  SessionEnd  {}                                  вкладку закрыли

Плана в чате нет, поэтому прогресс — 0/1 → 1/1.
"""
from .common import fail, finish_task, reset, short, start_task
from i18n import t

NAME = "claude-web"
THEME = "claude"            # тема и сцена ожидания — как у Claude Code


def _title(ev):
    """Название чата, если оно уже есть, иначе — сам вопрос."""
    title = short(ev.get("title"), 60)
    return title if title else ev.get("prompt")


def handle(ev, state, ctx):
    name = ev.get("hook_event_name", "")

    if name == "WebPrompt":
        start_task(state, ctx, _title(ev))
        return True

    if name == "WebBusy":
        if state["state"] in ("idle", "done"):            # демон перезапустился посреди ответа
            start_task(state, ctx, _title(ev))
        phase = ev.get("phase")
        if phase == "tool" and ev.get("tool"):
            step = short(ev["tool"], 60)
        else:
            step = t("writing" if phase == "writing" else "thinking")
        if ev.get("title") and state.get("title") != short(ev["title"], 60):
            state["title"] = short(ev["title"], 60)        # название чата появляется после первого ответа
        state["state"] = "work"
        state["step"] = step
        return True

    if name == "WebWait":
        state["state"] = "wait"
        state["step"] = short(ev.get("message") or t("needs_you"), 60)
        return True

    if name == "WebDone":
        if state["state"] == "idle":
            return False
        finish_task(state, ctx)
        state["step"] = t("answer_ready")
        return True

    if name == "WebError":
        fail(state, ev.get("message") or t("task_stopped"))
        return True

    if name == "SessionEnd":
        reset(state, ctx)
        return True

    return False
