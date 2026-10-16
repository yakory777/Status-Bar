"""Адаптеры агентов. Чтобы добавить новый агент, создайте модуль с NAME и handle()."""
from . import claude, codex

ADAPTERS = {m.NAME: m for m in (claude, codex)}
