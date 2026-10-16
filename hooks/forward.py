#!/usr/bin/env python3
"""
Хук для Claude Code и Codex: пересылает событие демону статус-бара.

    python3 forward.py claude   < событие на stdin
    python3 forward.py codex

Если демон не запущен, хук поднимает его сам (на SessionStart и UserPromptSubmit).
Отключить автозапуск: переменная окружения AGENT_STATUS_AUTOSTART=0.
Хук всегда завершается с кодом 0 и никогда не мешает работе агента.
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


def post(agent, data):
    req = urllib.request.Request(
        f"{URL}?agent={agent}", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=0.5)


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
    try:
        post(agent, data)
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
