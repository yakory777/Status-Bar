#!/usr/bin/env python3
"""
Хук для Claude Code и Codex: пересылает событие демону статус-бара.

    python3 forward.py claude   < событие на stdin
    python3 forward.py codex

Если демон не запущен, хук поднимает его сам (на SessionStart и UserPromptSubmit).
Отключить автозапуск: переменная окружения AGENT_STATUS_AUTOSTART=0.
Хук всегда завершается с кодом 0 и никогда не мешает работе агента.

Решение кнопкой (AGENT_STATUS_BUTTON_APPROVE=1, только Claude Code): на PermissionRequest
хук ждёт нажатия до AGENT_STATUS_APPROVE_WAIT секунд (по умолчанию 20) и печатает решение.
Не нажали — хук молчит, и Claude Code спрашивает как обычно.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PORT = int(os.environ.get("AGENT_STATUS_PORT", "8765"))
URL = f"http://127.0.0.1:{PORT}/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON = os.path.join(ROOT, "host", "daemon.py")
AUTOSTART_EVENTS = ("SessionStart", "UserPromptSubmit")


def post(agent, data, wait=0.0):
    """Отправить событие. С wait > 0 — дождаться решения кнопкой; вернёт тело ответа."""
    query = f"?agent={agent}" + (f"&wait={wait:g}" if wait else "")
    req = urllib.request.Request(
        URL + query, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=(wait + 5) if wait else 0.5) as r:
        return r.read()


def button_wait(agent, data):
    """Сколько ждать решения кнопкой для этого события (0 — не ждать)."""
    if agent != "claude" or os.environ.get("AGENT_STATUS_BUTTON_APPROVE", "0") != "1":
        return 0.0
    try:
        if json.loads(data or b"{}").get("hook_event_name") != "PermissionRequest":
            return 0.0
        return max(1.0, min(120.0, float(os.environ.get("AGENT_STATUS_APPROVE_WAIT", "20"))))
    except ValueError:
        return 0.0


def print_decision(body):
    """Решение для Claude Code — единственное, что хук печатает в stdout."""
    try:
        decision = json.loads(body or b"{}").get("decision")
    except ValueError:
        return
    if decision not in ("allow", "deny"):
        return
    behavior = {"behavior": "allow"} if decision == "allow" else \
        {"behavior": "deny", "message": "Отклонено кнопкой на статус-баре"}
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PermissionRequest", "decision": behavior}}, ensure_ascii=False))
    sys.stdout.flush()


def start_daemon():
    log_dir = (os.environ.get("PLUGIN_DATA")
               or os.environ.get("CLAUDE_PLUGIN_DATA")
               or tempfile.gettempdir())
    os.makedirs(log_dir, exist_ok=True)
    log = open(os.path.join(log_dir, "agent-status-daemon.log"), "ab")
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True)
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, DAEMON], **kwargs)


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else "claude"
    data = sys.stdin.buffer.read()
    wait = button_wait(agent, data)
    try:
        body = post(agent, data, wait)
        if wait:
            print_decision(body)
        return
    except (urllib.error.URLError, OSError):
        pass

    if os.environ.get("AGENT_STATUS_AUTOSTART", "1") == "0":
        return
    try:
        event = json.loads(data or b"{}").get("hook_event_name")
    except ValueError:
        return
    if event not in AUTOSTART_EVENTS:
        return

    start_daemon()
    for _ in range(10):            # ждём демон до ~2 секунд
        time.sleep(0.2)
        try:
            post(agent, data)
            return
        except (urllib.error.URLError, OSError):
            continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
