#!/usr/bin/env python3
"""
Wi-Fi-связь без железа: имитация платы по сети (тот же протокол, что в firmware/main/net_esp.c).

    python tests/test_links.py
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest

HOME = tempfile.mkdtemp()
os.environ["AGENT_STATUS_HOME"] = HOME           # не трогать настоящий ~/.agent-status
os.environ.pop("AGENT_STATUS_CONFIG", None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))

import config  # noqa: E402
import links   # noqa: E402


class FakeBoard:
    """Плата в сети: UDP-поиск и TCP-приём на 127.0.0.1, доверие по токенам, сопряжение «кнопкой»."""

    def __init__(self, board_id="a1b2c3", confirm=True):
        self.id = board_id
        self.confirm = confirm                     # что «нажмут» на экране сопряжения
        self.trusted = set()
        self.received = []                         # строки протокола от доверенного клиента
        self.shown_codes = []
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(("127.0.0.1", 0))
        self.port = self.udp.getsockname()[1]
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", self.port))
        self.srv.listen(2)
        self.client = None
        self.alive = True
        threading.Thread(target=self._udp, daemon=True).start()
        threading.Thread(target=self._tcp, daemon=True).start()

    def info(self):
        return {"id": self.id, "ip": "127.0.0.1", "port": self.port, "fw": "0.3.0"}

    def send(self, obj):
        self.client.sendall((json.dumps(obj) + "\n").encode())

    def _udp(self):
        while self.alive:
            try:
                data, addr = self.udp.recvfrom(256)
            except OSError:
                return
            if b'"discover"' in data:
                self.udp.sendto(json.dumps({"agent_status": "0.3.0", "id": self.id,
                                            "port": self.port}).encode(), addr)

    def _tcp(self):
        while self.alive:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            self.client, trusted, buf = c, False, b""
            while True:
                try:
                    data = c.recv(4096)
                except OSError:
                    break
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = json.loads(line)
                    if "hello" in msg:
                        trusted = msg["hello"]["token"] in self.trusted
                        key = "welcome" if trusted else "pair_required"
                        self.send({key: {"id": self.id, "fw": "0.3.0", "trusted": trusted}})
                    elif "pair_token" in msg:
                        self.shown_codes.append(msg["pair"])
                        time.sleep(0.05)               # «человек смотрит на экран и жмёт кнопку»
                        if self.confirm:
                            self.trusted.add(msg["pair_token"])
                            trusted = True
                            self.send({"paired": {"id": self.id}})
                        else:
                            self.send({"pair": "cancelled"})
                    elif "wifi_list" in msg and trusted:
                        self.send({"wifi": {"saved": ["Home"], "connected": "Home", "ip": "127.0.0.1"}})
                    elif trusted:
                        self.received.append(msg)
            c.close()

    def close(self):
        self.alive = False
        self.udp.close()
        self.srv.close()


class Discovery(unittest.TestCase):
    def test_finds_board(self):
        b = FakeBoard("c0ffee")
        try:
            found = links.discover(timeout=0.6, hosts=["127.0.0.1"], port=b.port)
            self.assertEqual([x["id"] for x in found], ["c0ffee"])
            self.assertEqual(found[0]["port"], b.port)
        finally:
            b.close()


class SweepTargets(unittest.TestCase):
    def test_every_address_of_own_networks_but_ours(self):
        real = links.local_ips
        links.local_ips = lambda: ["192.168.1.23", "10.0.0.5"]
        try:
            t = links.sweep_targets()
        finally:
            links.local_ips = real
        self.assertEqual(len(t), 2 * 253)
        self.assertIn("192.168.1.1", t)
        self.assertIn("10.0.0.254", t)
        self.assertNotIn("192.168.1.23", t)
        self.assertEqual(links.local_broadcasts.__doc__ is not None, True)


class Pairing(unittest.TestCase):
    def setUp(self):
        self.token = links.host_token()

    def test_token_is_stable(self):
        self.assertEqual(links.host_token(), self.token)
        self.assertEqual(len(self.token), 32)

    def test_untrusted_then_paired(self):
        b = FakeBoard()
        try:
            l = links.NetLink("127.0.0.1", b.port)
            key, body = links.hello(l, self.token, "pc")
            l.close()
            self.assertEqual(key, "pair_required")
            shown = []
            self.assertEqual(links.pair(b.info(), self.token, "pc", "123456",
                                        on_code=lambda: shown.append(1)), "paired")
            self.assertEqual(b.shown_codes, ["123456"])
            self.assertEqual(shown, [1])          # код показан компьютером — плата его ждёт
            self.assertEqual(links.pair(b.info(), self.token, "pc", "654321",
                                        on_code=lambda: shown.append(2)), "already")
            self.assertEqual(shown, [1])          # уже доверяет — код не печатается
        finally:
            b.close()

    def test_cancelled(self):
        b = FakeBoard(confirm=False)
        try:
            self.assertEqual(links.pair(b.info(), self.token, "pc", "111111"), "cancelled")
        finally:
            b.close()


class Daemon(unittest.TestCase):
    """Демон поверх имитации: подключение по Wi-Fi, отправка статуса, команда плате, отказ без доверия."""

    @classmethod
    def setUpClass(cls):
        import daemon
        cls.d = daemon

    def test_connect_send_and_request(self):
        d = self.d
        b = FakeBoard("beef01")
        orig = links.discover
        links.discover = lambda **kw: [b.info()]
        try:
            self.assertIsNone(d.connect_wifi())                    # чужой компьютер — плата не пускает
            self.assertIn("beef01", d.nagged)
            self.assertEqual(links.pair(b.info(), links.host_token(), "pc", "222333"), "paired")
            l = d.connect_wifi()
            self.assertIsNotNone(l)
            self.assertEqual(config.load_state()["board_id"], "beef01")
            d.link = l
            with d.lock:
                d.send_state()
            time.sleep(0.2)
            self.assertEqual(b.received[-1]["state"], "idle")
            # ответ платы на служебную команду читает основной цикл — эмулируем его
            reader = threading.Thread(target=self._pump, args=(l,), daemon=True)
            reader.start()
            reply = d.board_request({"wifi_list": 1}, "wifi", timeout=2)
            self.assertEqual(reply["wifi"]["connected"], "Home")
            err = d.board_request({"wifi_add": {"ssid": "x", "pass": "y"}}, "wifi", timeout=1)
            self.assertIn("USB", err["error"])                    # сети меняются только по кабелю
        finally:
            links.discover = orig
            d.drop_link("test over")
            b.close()

    def _pump(self, l):
        for _ in range(40):
            try:
                text = l.readline()
            except links.LinkError:
                return
            if text:
                self.d.handle_board_line(text)


class Settings(unittest.TestCase):
    def test_transport_and_state_merge(self):
        c = config.load(env={"AGENT_STATUS_TRANSPORT": "wifi", "AGENT_STATUS_WIFI_HOST": "10.0.0.7"},
                        read_file=False)
        self.assertEqual((c["transport"], c["wifi_host"]), ("wifi", "10.0.0.7"))
        self.assertEqual(config.load(env={"AGENT_STATUS_TRANSPORT": "pigeon"}, read_file=False)["transport"], "auto")
        config.update_state(scene_choice={"claude": "cursor"})
        self.assertIn("host_token", config.load_state())               # токен не затёрт сценой


if __name__ == "__main__":
    unittest.main()
