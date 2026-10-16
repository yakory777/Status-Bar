"""
Темы и сцены ожидания.

Тема экрана выбирается по агенту, который прислал событие последним.
Сцену ожидания для каждой темы можно выбрать переменной окружения:

    AGENT_STATUS_IDLE_CLAUDE = robot | cursor     (по умолчанию robot)
    AGENT_STATUS_IDLE_CODEX  = cursor | typist    (по умолчанию cursor)
"""
import os

IDLE_SCENES = {
    "claude": ("robot", "cursor"),
    "codex": ("cursor", "typist"),
}


def idle_scene(agent, env=None):
    """Сцена ожидания для агента: из переменной окружения или первая по списку."""
    env = os.environ if env is None else env
    options = IDLE_SCENES.get(agent)
    if not options:
        return None
    wanted = (env.get(f"AGENT_STATUS_IDLE_{agent.upper()}") or "").strip().lower()
    return wanted if wanted in options else options[0]
