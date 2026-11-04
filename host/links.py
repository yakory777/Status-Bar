"""
Связь с платой: USB-кабель (pyserial) и Wi-Fi (TCP), поиск платы в сети, приветствие и сопряжение.

Протокол со стороны платы описан в firmware/main/net_esp.h. Коротко:
  • поиск — UDP-запрос {"discover":"agent-status"} на порт 8766 (широковещательно и на wifi_host),
    плата отвечает {"agent_status":"0.3.0","id":"a1b2c3","port":8766};
  • данные — TCP-порт 8766, те же строки JSON, что по USB;
  • первым сообщением — {"hello":{"token":..., "name":...}}; по USB плата доверяет сразу,
    по сети — только после сопряжения (код на экране + кнопка).

Только стандартная библиотека; pyserial нужен лишь для USB и подгружается при первом обращении.
"""
import json
import secrets
import socket
import time

import config

NET_PORT = 8766
ESPRESSIF_VID = 0x303A


class LinkError(Exception):
    pass


# ---------------- USB ----------------

def find_usb_port(forced=None):
    """Порт платы: заданный в настройках или первый с USB VID Espressif."""
    if forced:
        return forced
    from serial.tools import list_ports
    for p in list_ports.comports():
        if p.vid == ESPRESSIF_VID:
            return p.device
    return None


class SerialLink:
    kind = "usb"

    def __init__(self, port):
        import serial
        self._serial = serial
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.2
        s.write_timeout = 1
        s.dtr = False          # не перезагружать плату при открытии порта
        s.rts = False
        try:
            s.open()
        except (serial.SerialException, OSError) as e:
            raise LinkError(str(e))
        self.s = s
        self.name = port

    def write_line(self, text):
        try:
            self.s.write((text + "\n").encode("utf-8"))
        except (self._serial.SerialException, OSError) as e:
            raise LinkError(str(e))

    def readline(self):
        try:
            return self.s.readline().decode("utf-8", "replace").strip()
        except (self._serial.SerialException, OSError) as e:
            raise LinkError(str(e))

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


# ---------------- Wi-Fi ----------------

class NetLink:
    kind = "wifi"

    def __init__(self, ip, port=NET_PORT, timeout=3.0):
        try:
            self.sock = socket.create_connection((ip, port), timeout=timeout)
        except OSError as e:
            raise LinkError(str(e))
        self.sock.settimeout(0.2)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.buf = b""
        self.name = f"{ip}:{port}"

    def write_line(self, text):
        try:
            self.sock.sendall((text + "\n").encode("utf-8"))
        except OSError as e:
            raise LinkError(str(e))

    def readline(self):
        """Одна строка или "" через ~0,2 с тишины. LinkError — соединение закрыто."""
        if b"\n" not in self.buf:
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                return ""
            except OSError as e:
                raise LinkError(str(e))
            if not data:
                raise LinkError("closed by the board")
            self.buf += data
        if b"\n" not in self.buf:
            return ""
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8", "replace").strip()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def local_ips():
    """IPv4-адреса этого компьютера (без 127.x и 169.254.x)."""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:                                       # адрес, через который компьютер выходит в сеть
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))            # пакет не отправляется — только выбор маршрута
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.")))


def local_broadcasts():
    """Широковещательные адреса своих сетей (x.y.z.255 для каждого IPv4 компьютера).
    Общий 255.255.255.255 Windows часто отправляет не в тот адаптер (VPN, WSL, Hyper-V)."""
    return sorted({ip.rsplit(".", 1)[0] + ".255" for ip in local_ips()})


def sweep_targets():
    """Все адреса x.y.z.1–254 своих сетей. Запасной поиск, когда широковещание не доходит,
    а IP платы сменился (роутер выдал другой после перезагрузки)."""
    mine = set(local_ips())
    out = []
    for prefix in sorted({ip.rsplit(".", 1)[0] for ip in mine}):
        out += [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" not in mine]
    return out


def discover(timeout=1.0, hosts=(), port=NET_PORT, sweep=False):
    """Платы в сети: список {"id", "ip", "port", "fw"}. hosts — адреса, которые спросить напрямую;
    sweep — спросить ещё и каждый адрес своих сетей (по разу, в начале)."""
    found = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)
        query = b'{"discover":"agent-status"}'
        targets = ["255.255.255.255"] + local_broadcasts() + [h for h in hosts if h]
        if sweep:
            s.setblocking(False)                       # не ждать, пока система найдёт каждый адрес
            for t in sweep_targets():
                try:
                    s.sendto(query, (t, port))
                except OSError:
                    pass
            s.settimeout(0.2)
        deadline = time.monotonic() + timeout
        next_send = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_send:          # пара повторов — UDP может потеряться
                for t in targets:
                    try:
                        s.sendto(query, (t, port))
                    except OSError:
                        pass
                next_send = time.monotonic() + 0.4
            try:
                data, (ip, _) = s.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("agent_status") and msg.get("id"):
                found[msg["id"]] = {"id": msg["id"], "ip": ip, "port": int(msg.get("port", port)),
                                    "fw": msg["agent_status"]}
    finally:
        s.close()
    return list(found.values())


# ---------------- доверие ----------------

def host_token(env=None):
    """Постоянный токен этого компьютера (создаётся один раз и лежит в state.json)."""
    token = config.load_state(env).get("host_token")
    if not token:
        token = secrets.token_hex(16)
        config.update_state(env, host_token=token)
    return token


def host_name():
    return socket.gethostname()[:40] or "computer"


def read_reply(link, keys, timeout):
    """Читать строки, пока не придёт JSON с одним из ключей keys. Возвращает (ключ, сообщение) или (None, None)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = link.readline()
        if not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        for k in keys:
            if isinstance(msg, dict) and k in msg:
                return k, msg
    return None, None


def hello(link, token, name, timeout=2.0):
    """Поздороваться. Возвращает ("welcome"|"pair_required", тело) или (None, None) для старой прошивки."""
    link.write_line(json.dumps({"hello": {"token": token, "name": name}}, ensure_ascii=False))
    key, msg = read_reply(link, ("welcome", "pair_required"), timeout)
    return (key, msg[key]) if key else (None, None)


def pair(board, token, name, code, timeout=70.0, on_code=None):
    """Сопряжение по сети: "paired", "already", "cancelled" или "timeout".
    on_code() вызывается, только когда плата и правда покажет код (компьютер ей ещё не знаком)."""
    link = NetLink(board["ip"], board.get("port", NET_PORT))
    try:
        key, body = hello(link, token, name)
        if key == "welcome" and body.get("trusted"):
            return "already"
        if on_code:
            on_code()
        link.write_line(json.dumps({"pair": code, "pair_token": token, "name": name}, ensure_ascii=False))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            key, msg = read_reply(link, ("paired", "pair"), 1.0)
            if key == "paired":
                return "paired"
            if key == "pair" and msg.get("pair") == "cancelled":
                return "cancelled"
        return "timeout"
    finally:
        link.close()
