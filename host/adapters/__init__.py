"""Адаптеры агентов. Чтобы добавить новый агент, создайте модуль с NAME и handle()."""
from . import claude, claude_web, codex

ADAPTERS = {m.NAME: m for m in (claude, claude_web, codex)}


def theme(agent):
    """Тема экрана для агента: у чата claude.ai она та же, что у Claude Code."""
    m = ADAPTERS.get(agent)
    return getattr(m, "THEME", agent) if m else agent
