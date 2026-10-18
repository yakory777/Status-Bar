"""
Темы и сцены ожидания.

Тема экрана выбирается по агенту, который прислал событие последним.
Сцена для каждой темы — из настроек (config.py): idle_claude, idle_codex
или переменные AGENT_STATUS_IDLE_CLAUDE / AGENT_STATUS_IDLE_CODEX.
"""
IDLE_SCENES = {
    "claude": ("robot", "cursor"),
    "codex": ("cursor", "typist"),
}


def idle_scene(agent, settings):
    """Сцена ожидания для агента: из настроек, а если там чужое имя — первая по списку."""
    options = IDLE_SCENES.get(agent)
    if not options:
        return None
    wanted = str(settings.get(f"idle_{agent}") or "").strip().lower()
    return wanted if wanted in options else options[0]
