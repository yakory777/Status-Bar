"""
Решение запросов разрешения кнопкой на плате.

<<<<<<< HEAD
Хук PermissionRequest (только Claude Code, только при button_approve = true в настройках
или AGENT_STATUS_BUTTON_APPROVE=1) ждёт ответа от демона до approve_wait секунд. Плата показывает подсказку
«удержать — разрешить · нажать — отклонить» и присылает {"button":"approve"|"deny"}.
Нет нажатия — хук ничего не решает, и Claude Code показывает свой обычный запрос.
"""
import threading


def enabled(settings):
    """Решать ли запросы разрешения кнопкой (button_approve в настройках)."""
    return bool(settings.get("button_approve"))


def wait_seconds(settings):
    """Сколько хук ждёт кнопку, 1..120 с."""
    try:
        return float(max(1, min(120, int(settings.get("approve_wait", 20)))))
    except (TypeError, ValueError):
        return 20.0
=======
Хук PermissionRequest (только Claude Code, только при AGENT_STATUS_BUTTON_APPROVE=1)
ждёт ответа от демона до AGENT_STATUS_APPROVE_WAIT секунд. Плата показывает подсказку
«удержать — разрешить · нажать — отклонить» и присылает {"button":"approve"|"deny"}.
Нет нажатия — хук ничего не решает, и Claude Code показывает свой обычный запрос.
"""
import os
import threading

DEFAULT_WAIT_S = 20


def enabled(env=None):
    env = os.environ if env is None else env
    return env.get("AGENT_STATUS_BUTTON_APPROVE", "0") == "1"


def wait_seconds(env=None):
    env = os.environ if env is None else env
    try:
        return max(1.0, min(120.0, float(env.get("AGENT_STATUS_APPROVE_WAIT", DEFAULT_WAIT_S))))
    except ValueError:
        return float(DEFAULT_WAIT_S)
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046


class Approvals:
    def __init__(self):
        self._lock = threading.Lock()
        self._pending = {}            # ключ сессии → [Event, решение]

    def begin(self, key):
        with self._lock:
            slot = self._pending.get(key)
            if slot is None:
                slot = self._pending[key] = [threading.Event(), None]
            return slot

    def wait(self, key, timeout):
        """Ждёт решения для сессии. Возвращает "allow", "deny" или None по таймауту."""
        slot = self.begin(key)
        slot[0].wait(timeout)
        with self._lock:
            if self._pending.get(key) is slot:
                del self._pending[key]
        return slot[1]

    def resolve(self, key, decision):
        """Решение с кнопки. False — эта сессия ничего не ждала."""
        with self._lock:
            slot = self._pending.get(key)
            if slot is None or slot[0].is_set():
                return False
            slot[1] = decision
            slot[0].set()
            return True

    def awaiting(self, key):
        with self._lock:
            slot = self._pending.get(key)
            return slot is not None and not slot[0].is_set()

