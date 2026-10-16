#!/usr/bin/env python3
"""
Agent Status Bar daemon.

Держит USB-порт платы открытым, принимает события хуков по HTTP
(http://127.0.0.1:8765/?agent=claude или ?agent=codex), переводит их
в состояние экрана через адаптеры и шлёт плате строку JSON.

    pip install pyserial
    python host/daemon.py            # автопоиск платы
    python host/daemon.py COM5       # явный порт
    python host/daemon.py --demo     # демо без агента

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

from adapters import ADAPTERS          # noqa: E402
from adapters.common import IDLE       # noqa: E402

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("Нужен pyserial: pip install pyserial", file=sys.stderr)
    sys.exit(1)

HTTP_HOST = "127.0.0.1"
HTTP_PORT = int(os.environ.get("AGENT_STATUS_PORT", "8765"))
ESPRESSIF_VID = 0x303A

lock = threading.Lock()
ser = None
forced_port = os.environ.get("AGENT_STATUS_SERIAL")

state = dict(IDLE)
contexts = {name: {} for name in ADAPTERS}   # своё состояние у каждого агента


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
        print(f"[serial] подключено: {port}", flush=True)
        return True
    except (serial.SerialException, OSError) as e:
        print(f"[serial] не удалось открыть {port}: {e}", flush=True)
        return False


def send_state():
    """Отправить текущее состояние на плату. Вызывать под lock."""
    global ser
    if ser is None and not open_serial():
        return
    line = json.dumps(state, ensure_ascii=False) + "\n"
    try:
        ser.write(line.encode("utf-8"))
    except (serial.SerialException, OSError):
        print("[serial] связь потеряна", flush=True)
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
                print("[esp]", data.decode("utf-8", "replace").rstrip(), flush=True)
        except (serial.SerialException, OSError):
            with lock:
                ser = None
            time.sleep(1)


# ---------------- события ----------------

def handle_event(agent, ev):
    adapter = ADAPTERS.get(agent)
    if adapter is None:
        print(f"[http] неизвестный агент: {agent}", flush=True)
        return
    with lock:
        if adapter.handle(ev, state, contexts[agent]):
            send_state()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            q = parse_qs(urlparse(self.path).query)
            agent = (q.get("agent") or ["claude"])[0]
            n = int(self.headers.get("Content-Length", 0))
            ev = json.loads(self.rfile.read(n) or b"{}")
            handle_event(agent, ev)
        except Exception as e:
            print("[http] ошибка:", e, flush=True)
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        body = json.dumps({"service": "agent-status-bar", "state": state},
                          ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


# ---------------- демо ----------------

def demo():
    steps = ["Изучаю структуру проекта", "Правлю модуль авторизации",
             "Обновляю логику токенов", "Пишу тесты", "Запускаю тесты"]
    while True:
        handle_event("claude", {"hook_event_name": "UserPromptSubmit",
                                "prompt": "Отрефактори модуль авторизации"})
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
                                        "message": "Разрешить запуск npm test?"})
                time.sleep(3)
        handle_event("claude", {"hook_event_name": "Stop"})
        time.sleep(6)


def main():
    global forced_port
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        forced_port = args[0]

    try:
        srv = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler)
    except OSError:
        print(f"[http] порт {HTTP_PORT} занят — демон уже запущен?", flush=True)
        sys.exit(0)

    threading.Thread(target=serial_watch, daemon=True).start()
    if "--demo" in sys.argv:
        print("[demo] крутим демо, Ctrl+C для выхода", flush=True)
        threading.Thread(target=demo, daemon=True).start()

    print(f"[http] слушаю http://{HTTP_HOST}:{HTTP_PORT}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
