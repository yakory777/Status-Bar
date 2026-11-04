#!/usr/bin/env python3
"""
Agent Status Bar daemon.

Держит связь с платой (USB-кабель или Wi-Fi), принимает события хуков по HTTP
(http://127.0.0.1:8765/?agent=claude или ?agent=codex), переводит их
в состояние экрана через адаптеры и шлёт плате строку JSON.

    pip install pyserial
    python host/daemon.py                 # автопоиск платы
    python host/daemon.py COM5            # явный порт
    python host/daemon.py --demo          # демо без агента
    python host/daemon.py config          # итоговые настройки и путь к файлу
    python host/daemon.py config --init   # создать ~/.agent-status/config.toml
    python host/daemon.py wifi add "Сеть" "пароль"   # сохранить сеть Wi-Fi в плату (по кабелю)
    python host/daemon.py wifi list | wifi remove "Сеть"
    python host/daemon.py boards          # платы в сети
    python host/daemon.py pair            # сопряжение по Wi-Fi: код на экране + кнопка

Обычно запускать вручную не нужно: хук плагина поднимает демон сам.
"""
import json
import os
import secrets
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
import links                           # noqa: E402

settings = config.load()
i18n.set_language(settings["language"])

HTTP_HOST = "127.0.0.1"
HTTP_PORT = settings["http_port"]
TRANSPORT = settings["transport"]          # auto | usb | wifi

lock = threading.Lock()
link = None                                # links.SerialLink или links.NetLink — текущая связь с платой
forced_port = settings["serial_port"] or None
have_pyserial = False

approvals = approvals_mod.Approvals()
sessions = Sessions(settings=settings, approvals=approvals)
sessions.scene_choice.update(config.load_state().get("scene_choice") or {})
PING_EVERY_S = 5          # плата считает связь потерянной после 15 с тишины
DISCOVER_EVERY_S = 5      # как часто искать плату в сети, пока связи нет
SWEEP_EVERY_S = 20        # перебор всех адресов сети, если обычный поиск не нашёл плату
ALIVE_EVERY_S = 10        # по Wi-Fi: как часто спрашивать плату, жива ли она
ALIVE_TIMEOUT_S = 25      # плата молчит столько — соединение мёртвое, ищем заново
USB_RECHECK_S = 10        # на Wi-Fi: как часто проверять, не подключили ли кабель

waiters = {}              # ключ ответа платы → [Event, ответ] (для команд wifi и т. п.)
nagged = set()            # платы, про которые уже сказали «нужно сопряжение»


# ---------------- связь с платой ----------------

def usb_port():
    if not have_pyserial or TRANSPORT == "wifi":
        return None
    try:
        return links.find_usb_port(forced_port)
    except Exception:
        return None


def connect_usb():
    port = usb_port()
    if not port:
        return None
    try:
        l = links.SerialLink(port)
    except links.LinkError as e:
        print(f"[serial] cannot open {port}: {e}", flush=True)
        return None
    print(f"[serial] connected: {port}", flush=True)
    time.sleep(1.5)                         # плата могла перезагрузиться при подключении
    try:                                    # по кабелю плата доверяет этому компьютеру сразу
        l.write_line(json.dumps({"hello": {"token": links.host_token(), "name": links.host_name()}}))
    except links.LinkError:
        pass
    return l


last_sweep = 0.0
last_rx = 0.0             # когда плата присылала что-нибудь последний раз
last_welcome = None


def connect_wifi():
    """Найти плату в сети и подключиться, если она нам доверяет.
    Порядок: широковещательный запрос, адрес из настроек и последний известный адрес платы;
    не нашлась — раз в SWEEP_EVERY_S опросить каждый адрес сети (IP мог смениться)."""
    global last_sweep
    state = config.load_state()
    mine = state.get("board_id")
    hosts = [settings["wifi_host"], state.get("board_ip")]
    boards = links.discover(timeout=1.0, hosts=hosts)
    if not boards and time.monotonic() - last_sweep > SWEEP_EVERY_S:
        last_sweep = time.monotonic()
        boards = links.discover(timeout=1.5, hosts=hosts, sweep=True)
    boards.sort(key=lambda b: b["id"] != mine)          # своя плата — первой
    for b in boards:
        try:
            l = links.NetLink(b["ip"], b["port"])
        except links.LinkError:
            continue
        try:
            key, body = links.hello(l, links.host_token(), links.host_name())
        except links.LinkError:
            key, body = None, None
        if key == "welcome" and body.get("trusted"):
            print(f"[wifi] connected to board {b['id']} at {b['ip']}", flush=True)
            if b["id"] != mine or b["ip"] != state.get("board_ip"):
                config.update_state(board_id=b["id"], board_ip=b["ip"])     # запомнить и новый IP
            nagged.discard(b["id"])
            return l
        l.close()
        if key == "pair_required" and b["id"] not in nagged:
            nagged.add(b["id"])
            print(f"[wifi] board {b['id']} at {b['ip']} does not know this computer yet — "
                  f"run: python host/daemon.py pair", flush=True)
    return None


def drop_link(reason):
    global link
    if link is not None:
        print(f"[{link.kind}] connection lost: {reason}", flush=True)
        link.close()
        link = None


def send_state():
    """Отправить текущее состояние на плату. Вызывать под lock."""
    send_line(sessions.display())


def send_line(obj):
    if link is None:
        return
    try:
        link.write_line(json.dumps(obj, ensure_ascii=False))
    except links.LinkError as e:
        drop_link(e)


def link_watch():
    """Держит связь с платой (кабель важнее Wi-Fi) и читает, что она присылает."""
    global link, last_rx
    last_discover = last_usb_check = 0.0
    while True:
        now = time.monotonic()
        if link is None:
            new = connect_usb()
            if new is None and TRANSPORT != "usb" and now - last_discover > DISCOVER_EVERY_S:
                last_discover = now
                new = connect_wifi()
            if new is None:
                time.sleep(1)
                continue
            with lock:
                link = new
                last_rx = time.monotonic()
                send_state()
        elif link.kind == "wifi" and now - last_usb_check > USB_RECHECK_S:
            last_usb_check = now
            if usb_port():                          # подключили кабель — переходим на него
                with lock:
                    drop_link("switching to USB")
                continue
        l = link
        try:
            text = l.readline()
        except links.LinkError as e:
            with lock:
                if link is l:
                    drop_link(e)
            time.sleep(1)
            continue
        if not text:
            continue
        last_rx = time.monotonic()
        if text.startswith("{"):
            handle_board_line(text)
        else:
            print("[esp]", text, flush=True)


def heartbeat():
    """Пинг для платы, проверка, что плата по Wi-Fi ещё жива, и уборка брошенных сессий.
    По Wi-Fi Windows может минутами считать соединение с пропавшей платой живым,
    поэтому раз в ALIVE_EVERY_S спрашиваем hello и ждём welcome."""
    n = 0
    last_alive = 0.0
    while True:
        time.sleep(PING_EVERY_S)
        n += 1
        with lock:
            now = time.monotonic()
            if link is not None and link.kind == "wifi":
                if now - last_rx > ALIVE_TIMEOUT_S:
                    drop_link("the board stopped answering")
                    continue
                if now - last_alive >= ALIVE_EVERY_S:
                    last_alive = now
                    send_line({"hello": {"token": links.host_token(), "name": links.host_name()}})
            if n % 6 == 0 and sessions.sweep():
                send_state()
            elif link is not None:
                send_line({"ping": 1})


def board_request(cmd, expect, timeout=6.0):
    """Отправить плате служебную команду и дождаться ответа с ключом expect."""
    ev = threading.Event()
    slot = [ev, None]
    waiters.setdefault(expect, []).append(slot)
    try:
        with lock:
            if link is None:
                return {"error": "no board connected"}
            if "wifi_add" in cmd or "wifi_remove" in cmd:
                if link.kind != "usb":
                    return {"error": "connect the board with a USB cable to change Wi-Fi networks"}
            send_line(cmd)
        if not ev.wait(timeout):
            return {"error": "the board did not answer (old firmware?)"}
        return slot[1]
    finally:
        if slot in waiters.get(expect, []):
            waiters[expect].remove(slot)


# ---------------- сообщения с платы ----------------

def handle_board_line(text):
    """Плата шлёт {"button":...}, ответы на hello и служебные команды."""
    try:
        msg = json.loads(text)
    except ValueError:
        print("[esp]", text, flush=True)
        return
    if not isinstance(msg, dict):
        return
    for key, slots in list(waiters.items()):     # кто-то ждёт этот ответ (команда wifi и т. п.)
        if key in msg:
            for slot in slots:
                slot[1] = msg
                slot[0].set()
    if "welcome" in msg:
        global last_welcome
        body = msg["welcome"] or {}
        bid = body.get("id")
        if bid and bid != config.load_state().get("board_id"):
            config.update_state(board_id=bid)
        seen = (bid, body.get("fw"), body.get("wifi"))
        if seen != last_welcome:                    # проверка связи раз в 10 с — в журнал не пишем
            last_welcome = seen
            wifi = f", Wi-Fi: {body['wifi']}" if body.get("wifi") else ""
            print(f"[board] {bid or '?'} firmware {body.get('fw', '?')}{wifi}", flush=True)
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
                config.update_state(scene_choice=sessions.scene_choice)   # переживёт перезапуск
                send_state()


# ---------------- события ----------------

def handle_event(agent, ev):
    if agent not in ADAPTERS:
        print(f"[http] unknown agent: {agent}", flush=True)
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
    print(f"[approve] {key}: {decision or 'no answer'}", flush=True)
    return decision


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path == "/board":            # служебная команда плате (wifi add/list/remove)
            try:
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n) or b"{}")
                self._json(200, board_request(req["cmd"], req["expect"], float(req.get("timeout", 6))))
            except Exception as e:
                self._json(400, {"error": str(e)})
            return
        body = None
        try:
            q = parse_qs(urlparse(self.path).query)
            agent = (q.get("agent") or ["claude"])[0]
            n = int(self.headers.get("Content-Length", 0))
            ev = json.loads(self.rfile.read(n) or b"{}")
            handle_event(agent, ev)
            wait = float((q.get("wait") or ["0"])[0])
            if wait > 0 and ev.get("hook_event_name") == "PermissionRequest" and link is not None:
                decision = wait_for_button(agent, ev, min(wait, 120))
                if decision:
                    body = json.dumps({"decision": decision}).encode()
        except Exception as e:
            print("[http] error:", e, flush=True)
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
                       "board": {"link": link.kind, "via": link.name} if link else None,
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
    """python host/daemon.py config [--init] | config set KEY VALUE"""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) >= 2 and args[1] == "set":
        if len(args) != 4 or args[2] not in config.DEFAULTS:
            print("usage: config set KEY VALUE; keys: " + ", ".join(config.DEFAULTS), file=sys.stderr)
            sys.exit(2)
        path, val = config.set_value(args[2], args[3])
        print(f"{args[2]} = {json.dumps(val)}  → {path}")
        return
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


# ---------------- команды: wifi, pair, boards ----------------

def _load_pyserial():
    global have_pyserial
    try:
        import serial  # noqa: F401
        have_pyserial = True
    except ImportError:
        have_pyserial = False
    return have_pyserial


def _request(cmd, expect, timeout=8.0):
    """Команда плате: через запущенный демон, а если его нет — напрямую по кабелю."""
    import urllib.error
    import urllib.request
    data = json.dumps({"cmd": cmd, "expect": expect, "timeout": timeout}).encode()
    req = urllib.request.Request(f"http://{HTTP_HOST}:{HTTP_PORT}/board", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout + 3) as r:
            body = r.read()
            if r.status == 204 or not body:              # старый демон не знает /board
                return {"error": "an older daemon is running — close Claude Code (or stop the daemon) and try again"}
            return json.loads(body)
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}") or {"error": str(e)}
    except (urllib.error.URLError, OSError):
        pass                                   # демон не запущен — идём сами
    if not _load_pyserial():
        return {"error": "pyserial is required: python -m pip install pyserial"}
    port = links.find_usb_port(forced_port)
    if not port:
        return {"error": "board not found on USB — connect it with a data cable"}
    try:
        l = links.SerialLink(port)
    except links.LinkError as e:
        return {"error": f"cannot open {port}: {e} (is another program using the port?)"}
    try:
        time.sleep(0.3)
        links.hello(l, links.host_token(), links.host_name(), timeout=1.5)   # кабель = доверие
        l.write_line(json.dumps(cmd, ensure_ascii=False))
        key, msg = links.read_reply(l, (expect,), timeout)
        return msg or {"error": "the board did not answer (old firmware? flash version 0.3.0 or newer)"}
    finally:
        l.close()


def _print_wifi(reply):
    w = reply.get("wifi") if isinstance(reply, dict) else None
    if not isinstance(w, dict):
        print("Error:", (reply or {}).get("error", "no answer"))
        return False
    if w.get("error"):
        print("Error:", w["error"])
        return False
    saved = w.get("saved") or []
    print("Saved networks:", ", ".join(f'"{x}"' for x in saved) if saved else "none")
    if w.get("connected"):
        rssi = f", signal {w['rssi']} dBm" if "rssi" in w else ""
        print(f'Connected to "{w["connected"]}", IP {w.get("ip", "?")}{rssi}')
    elif saved and not w.get("rebooting"):
        print("Not connected to Wi-Fi right now (out of range or wrong password?)")
    if w.get("rebooting"):
        print("The board restarts to apply this. Check in ~10 s: python host/daemon.py wifi list")
    return True


def cli_wifi(args):
    sub = args[0] if args else "list"
    if sub == "add" and len(args) >= 2:
        cmd = {"wifi_add": {"ssid": args[1], "pass": args[2] if len(args) > 2 else ""}}
    elif sub == "remove" and len(args) >= 2:
        cmd = {"wifi_remove": args[1]}
    elif sub == "list":
        cmd = {"wifi_list": 1}
    else:
        print('Usage:\n  python host/daemon.py wifi add "SSID" "password"\n'
              '  python host/daemon.py wifi remove "SSID"\n  python host/daemon.py wifi list')
        return 2
    return 0 if _print_wifi(_request(cmd, "wifi")) else 1


def _ip_arg(args):
    return args[args.index("--ip") + 1] if "--ip" in args and args.index("--ip") + 1 < len(args) else ""


def _find_boards(args):
    """Платы в сети для команд boards и pair: обычный поиск, а без ответа — перебор адресов сети."""
    hosts = [settings["wifi_host"], _ip_arg(args), config.load_state().get("board_ip")]
    return links.discover(timeout=2.0, hosts=hosts) or links.discover(timeout=2.0, hosts=hosts, sweep=True)


def cli_boards(args=()):
    boards = _find_boards(args)
    mine = config.load_state().get("board_id")
    if not boards:
        print("No boards found on the network. Is the board connected to Wi-Fi (python host/daemon.py wifi list)?\n"
              "Are this computer and the board on the same network? If yes, give the board's IP\n"
              "(shown by wifi list): python host/daemon.py boards --ip 192.168.1.50\n"
              "and put it into wifi_host in the settings file.")
        return 1
    for b in boards:
        print(f"{b['id']}  {b['ip']}  firmware {b['fw']}" + ("  ← yours" if b["id"] == mine else ""))
    return 0


def cli_pair(args):
    want = args[args.index("--id") + 1] if "--id" in args and args.index("--id") + 1 < len(args) else None
    boards = _find_boards(args)
    if want:
        boards = [b for b in boards if b["id"] == want]
    if not boards:
        print("No board found on the network.\n"
              "  1. Is the board on Wi-Fi? With the USB cable: python host/daemon.py wifi list\n"
              '     (no network yet: python host/daemon.py wifi add "SSID" "password")\n'
              "  2. Is this computer on the same network?\n"
              "  3. Give the IP from wifi list directly: python host/daemon.py pair --ip 192.168.1.50")
        return 1
    mine = config.load_state().get("board_id")
    if len(boards) > 1 and not any(b["id"] == mine for b in boards):
        print("Several boards found — choose one with --id:")
        for b in boards:
            print(f"  python host/daemon.py pair --id {b['id']}    ({b['ip']})")
        return 2
    board = next((b for b in boards if b["id"] == mine), boards[0])
    code = f"{secrets.randbelow(10 ** 6):06d}"
    print(f"Board {board['id']} at {board['ip']}")

    def show_code():
        print(f"\n    Code:  {code[:3]} {code[3:]}\n")
        print("Check that the board shows the same code, then press its button (hold it to cancel).", flush=True)
    try:
        result = links.pair(board, links.host_token(), links.host_name(), code, on_code=show_code)
    except links.LinkError as e:
        print("Could not connect to the board:", e)
        return 1
    if result in ("paired", "already"):
        config.update_state(board_id=board["id"])
        print("Already paired: this computer has talked to the board over the USB cable,\n"
              "and the board trusts it. No code is needed — Wi-Fi works without the cable."
              if result == "already" else
              "Paired! Without a cable the status bar now works over Wi-Fi.")
        return 0
    print("Pairing cancelled." if result == "cancelled" else "No answer from the board in time.")
    return 1


def main():
    global forced_port
    argv = sys.argv[1:]
    args = [a for a in argv if not a.startswith("--")]
    if args and args[0] == "config":
        show_config()
        return
    if args and args[0] == "wifi":
        sys.exit(cli_wifi(argv[1:]))
    if args and args[0] == "pair":
        sys.exit(cli_pair(argv[1:]))
    if args and args[0] == "boards":
        sys.exit(cli_boards(argv[1:]))
    if not _load_pyserial() and TRANSPORT == "usb":
        print("pyserial is required: python -m pip install pyserial", file=sys.stderr)
        sys.exit(1)
    if not have_pyserial:
        print("[serial] pyserial is not installed — USB is off, using Wi-Fi only", flush=True)
    if args:
        forced_port = args[0]
    for err in settings["_errors"]:
        print("[config]", err, flush=True)

    try:
        srv = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler)
    except OSError:
        print(f"[http] port {HTTP_PORT} is busy — is the daemon already running?", flush=True)
        sys.exit(0)

    threading.Thread(target=link_watch, daemon=True).start()
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
