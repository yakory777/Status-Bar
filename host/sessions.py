"""
Несколько сессий одновременно (два терминала, Claude и Codex сразу).

У каждой сессии своё состояние. На экран попадает самая важная:
ждёт вас > ошибка > работает > готово > ожидание, при равенстве — последняя обновлённая.
Остальные активные сессии показываются бейджем «+N».
"""
import time

from adapters import ADAPTERS
from adapters.common import ACTIVE, IDLE
from scenes import idle_scene

PRIORITY = {"wait": 5, "error": 4, "compact": 3, "work": 3, "start": 3, "done": 2, "idle": 0}
STALE_ACTIVE_S = 30 * 60      # активная сессия без событий 30 мин — считаем брошенной
STALE_DONE_S = 6 * 60 * 60    # завершённая — помним 6 ч, чтобы «Готово» не пропадало сразу


class Session:
    def __init__(self, agent, key, now):
        self.agent = agent
        self.key = key
        self.state = dict(IDLE)
        self.ctx = {}
        self.updated = now


class Sessions:
    def __init__(self, clock=time.monotonic, env=None, approvals=None):
        self.clock = clock
        self.env = env
        self.items = {}
        self.last_agent = "claude"
        self.approvals = approvals        # host/approvals.py — кто ждёт решения кнопкой
        self.scene_choice = {}            # тема → сцена, выбранная кнопкой (важнее переменной окружения)

    @staticmethod
    def key_for(agent, ev):
        return f"{agent}:{ev.get('session_id') or 'default'}"

    def handle(self, agent, ev):
        """Применяет событие. True — картинка на экране изменилась."""
        adapter = ADAPTERS.get(agent)
        if adapter is None:
            return False
        before = self.display()
        now = self.clock()
        key = self.key_for(agent, ev)
        s = self.items.get(key)
        if s is None:
            s = self.items[key] = Session(agent, key, now)
        if not adapter.handle(ev, s.state, s.ctx):
            return False
        s.updated = now
        self.last_agent = agent
        if ev.get("hook_event_name") == "SessionEnd":
            del self.items[key]
        return self.display() != before

    def sweep(self):
        """Убирает брошенные сессии. True — картинка изменилась."""
        before = self.display()
        now = self.clock()
        for key, s in list(self.items.items()):
            age = now - s.updated
            if (s.state["state"] in ACTIVE and age > STALE_ACTIVE_S) or age > STALE_DONE_S:
                del self.items[key]
        return self.display() != before

    def top_key(self):
        top = self._pick()
        return top.key if top else None

    def choose_scene(self, agent, scene):
        """Сцену выбрали кнопкой на плате. True — картинка изменилась."""
        from scenes import IDLE_SCENES
        if scene not in IDLE_SCENES.get(agent, ()):
            return False
        before = self.display()
        self.scene_choice[agent] = scene
        return self.display() != before

    def _scene(self, agent):
        return self.scene_choice.get(agent) or idle_scene(agent, self.env)

    def _pick(self):
        if not self.items:
            return None
        return max(self.items.values(), key=lambda s: (PRIORITY.get(s.state["state"], 0), s.updated))

    def display(self):
        """Состояние для платы: поля протокола целиком."""
        top = self._pick()
        if top is None or top.state["state"] == "idle":
            agent = top.agent if top else self.last_agent
            out = dict(IDLE)
        else:
            agent = top.agent
            out = dict(top.state)
        others = sum(1 for s in self.items.values()
                     if s is not top and s.state["state"] in ACTIVE)
        awaiting = bool(self.approvals and top and top.state["state"] == "wait"
                        and self.approvals.awaiting(top.key))
        out.update(agent=agent, idle=self._scene(agent), others=others, approve=awaiting)
        return out
