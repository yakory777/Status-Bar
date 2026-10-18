#!/usr/bin/env python3
"""
Agent Status Bar daemon.

Держит USB-порт платы открытым, принимает события хуков по HTTP
(http://127.0.0.1:8765/?agent=claude или ?agent=codex), переводит их
в состояние экрана через адаптеры и шлёт плате строку JSON.

    pip install pyserial
    python host/daemon.py                 # автопоиск платы
    python host/daemon.py COM5            # явный порт
    python host/daemon.py --demo          # демо без агента
    python host/daemon.py config          # итоговые настройки и путь к файлу
    python host/daemon.py config --init   # создать ~/.agent-status/config.toml

Обычно запускать вручную не нужно: хук плагина поднимает демон сам.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config                          # noqa: E402
import i18n                            # noqa: E402
from adapters import ADAPTERS          # noqa: E402
from sessions import Sessions          # noqa: E402
import approvals as approvals_mod      # noqa: E402

serial = list_ports = None             # pyserial грузим в main(): для «config» он не нужен

settings = config.load()
i18n.set_language(settings["language"])

HTTP_HOST = "127.0.0.1"
HTTP_PORT = settings["http_port"]
ESPRESSIF_VID = 0x303A

lock = threading.Lock()
ser = None
forced_port = settings["serial_port"] or None

approvals = approvals_mod.Approvals()
<<<<<<< HEAD
sessions = Sessions(settings=settings, approvals=approvals)
sessions.scene_choice.update(config.load_state().get("scene_choice") or {})
=======
sessions = Sessions(approvals=approvals)
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
PING_EVERY_S = 5          # плата считает связь потерянной после 15 с тишины


# ---------------- serial ----------------

def find_port():
    if forced_port:
        return forced_port
    for p in list_ports.comports():
        if p.vid == ESPRESSIF_VID:
            return p.device
    return None


def open_serial():
    global ser
    port = find_port()
    if not port:
        return False
    try:
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.2
        s.write_timeout = 1
        s.dtr = False          # не перезагружать плату при открытии порта
        s.rts = False
        s.open()
        ser = s
        print(f"[serial] connected: {port}", flush=True)
        return True
    except (serial.SerialException, OSError) as e:
        print(f"[serial] cannot open {port}: {e}", flush=True)
        return False


def send_state():
    """Отправить текущее состояние на плату. Вызывать под lock."""
    send_line(sessions.display())


def send_line(obj):
    global ser
    if ser is None and not open_serial():
        return
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    try:
        ser.write(line.encode("utf-8"))
    except (serial.SerialException, OSError):
        print("[serial] connection lost", flush=True)
        try:
            ser.close()
        except Exception:
            pass
        ser = None


def serial_watch():
    """Переподключение к плате и вывод её логов."""
    global ser
    while True:
        with lock:
            if ser is None and open_serial():
                time.sleep(1.5)          # плата загружается
                send_state()
            s = ser
        if s is None:
            time.sleep(2)
            continue
        try:
            data = s.readline()
            if data:
                text = data.decode("utf-8", "replace").strip()
                if text.startswith("{"):
                    handle_board_line(text)
                else:
                    print("[esp]", text, flush=True)
        except (serial.SerialException, OSError):
            with lock:
                ser = None
            time.sleep(1)


def heartbeat():
    """Пинг для платы и уборка брошенных сессий."""
    n = 0
    while True:
        time.sleep(PING_EVERY_S)
        n += 1
        with lock:
            if n % 6 == 0 and sessions.sweep():
                send_state()
            elif ser is not None:
                send_line({"ping": 1})


# ---------------- сообщения с платы ----------------

def handle_board_line(text):
    """Плата шлёт {"button":"approve"|"deny"|"scene_next", ...} и {"hello":...}."""
    try:
        msg = json.loads(text)
    except ValueError:
        print("[esp]", text, flush=True)
        return
    button = msg.get("button")
    if not button:
        return
    print(f"[button] {button}", flush=True)
    with lock:
        if button in ("approve", "deny"):
            key = sessions.top_key()
            if key and approvals.resolve(key, "allow" if button == "approve" else "deny"):
                send_state()
        elif button == "scene_next":
            agent = sessions.display()["agent"]
            if sessions.choose_scene(agent, msg.get("scene")):
<<<<<<< HEAD
                config.save_state({"scene_choice": sessions.scene_choice})   # переживёт перезапуск
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
                send_state()


# ---------------- события ----------------

def handle_event(agent, ev):
    if agent not in ADAPTERS:
<<<<<<< HEAD
        print(f"[http] unknown agent: {agent}", flush=True)
=======
        print(f"[http] неизвестный агент: {agent}", flush=True)
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        return
    with lock:
        if sessions.handle(agent, ev):
            send_state()


def wait_for_button(agent, ev, timeout):
    """Хук ждёт решения кнопкой. Возвращает "allow", "deny" или None."""
    key = Sessions.key_for(agent, ev)
    with lock:
        approvals.begin(key)
        send_state()                       # плата покажет «удержать — разрешить»
    decision = approvals.wait(key, timeout)
    with lock:
        send_state()                       # подсказку убрать
<<<<<<< HEAD
    print(f"[approve] {key}: {decision or 'no answer'}", flush=True)
=======
    print(f"[approve] {key}: {decision or 'нет ответа'}", flush=True)
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
    return decision


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = None
        try:
            q = parse_qs(urlparse(self.path).query)
            agent = (q.get("agent") or ["claude"])[0]
            n = int(self.headers.get("Content-Length", 0))
            ev = json.loads(self.rfile.read(n) or b"{}")
            handle_event(agent, ev)
            wait = float((q.get("wait") or ["0"])[0])
            if wait > 0 and ev.get("hook_event_name") == "PermissionRequest" and ser is not None:
                decision = wait_for_button(agent, ev, min(wait, 120))
                if decision:
                    body = json.dumps({"decision": decision}).encode()
        except Exception as e:
<<<<<<< HEAD
            print("[http] error:", e, flush=True)
=======
            print("[http] ошибка:", e, flush=True)
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
        if body:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(204)
            self.end_headers()

    def do_GET(self):
        with lock:
            payload = {"service": "agent-status-bar", "state": sessions.display(),
                       "sessions": [{"key": x.key, "state": x.state["state"]}
                                    for x in sessions.items.values()]}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


# ---------------- демо ----------------

def demo():
    steps = i18n.t("demo_steps").split("|")
    while True:
        handle_event("claude", {"hook_event_name": "UserPromptSubmit",
                                "prompt": i18n.t("demo_prompt")})
        time.sleep(3)
        for k in range(len(steps) + 1):
            todos = [{"content": s, "activeForm": s,
                      "status": "completed" if i < k else ("in_progress" if i == k else "pending")}
                     for i, s in enumerate(steps)]
            handle_event("claude", {"hook_event_name": "PostToolUse",
                                    "tool_name": "TodoWrite", "tool_input": {"todos": todos}})
            time.sleep(2.5)
            if k == 2:
                handle_event("claude", {"hook_event_name": "Notification",
                                        "message": i18n.t("demo_permission")})
                time.sleep(3)
        handle_event("claude", {"hook_event_name": "Stop"})
        time.sleep(6)


def show_config():
    """python host/daemon.py config [--init]"""
    if "--init" in sys.argv:
        path, created = config.init_file()
        print(("created " if created else "already exists: ") + path)
    print(f"# file: {config.config_path()}"
          + ("" if os.path.exists(config.config_path()) else "  (not created — run: config --init)"))
    print(f"# state: {config.state_path()}")
    for k in config.DEFAULTS:
        src = "env" if os.environ.get(config.ENV[k]) else ""
        print(f"{k} = {json.dumps(settings[k])}" + (f"    # from {config.ENV[k]}" if src else ""))
    choice = config.load_state().get("scene_choice")
    if choice:
        print(f"# scene chosen with the button: {json.dumps(choice)}")
    for err in settings["_errors"]:
        print("# error:", err)


def main():
    global forced_port, serial, list_ports
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and args[0] == "config":
        show_config()
        return
    try:
        import serial as _serial
        from serial.tools import list_ports as _list_ports
    except ImportError:
        print("pyserial is required: pip install pyserial", file=sys.stderr)
        sys.exit(1)
    serial, list_ports = _serial, _list_ports
    if args:
        forced_port = args[0]
    for err in settings["_errors"]:
        print("[config]", err, flush=True)

    try:
        srv = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler)
    except OSError:
        print(f"[http] port {HTTP_PORT} is busy — is the daemon already running?", flush=True)
        sys.exit(0)

    threading.Thread(target=serial_watch, daemon=True).start()
    threading.Thread(target=heartbeat, daemon=True).start()
    if "--demo" in sys.argv:
        print("[demo] running the demo, Ctrl+C to quit", flush=True)
        threading.Thread(target=demo, daemon=True).start()

    print(f"[http] listening on http://{HTTP_HOST}:{HTTP_PORT} · language: {settings['language']}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
