var t = chrome.i18n.getMessage;
var DEFAULTS = { enabled: true, port: 8765 };
var SETUP_URL = "https://yakory777.github.io/Status-Bar/";

document.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = t(el.dataset.i18n); });

function show(id, text, cls) {
  var el = document.getElementById(id);
  el.textContent = text;
  el.className = cls || "";
}

function hint(id, text) {
  var el = document.getElementById(id);
  el.hidden = !text;
  el.textContent = text || "";
}

async function checkDaemon(port) {
  try {
    var r = await fetch("http://127.0.0.1:" + port + "/", { cache: "no-store" });
    var data = await r.json();
    show("daemon", t("popup_running"), "ok");
    if (data.board) show("board", data.board.link === "wifi" ? t("popup_board_wifi") : t("popup_board_usb"), "ok");
    else show("board", t("popup_board_none"), "bad");
    hint("daemon_hint", data.board ? "" : t("hint_no_board"));
  } catch (e) {
    show("daemon", t("popup_stopped"), "bad");
    show("board", "—");
    hint("daemon_hint", t("hint_start_daemon"));
  }
}

async function checkPage() {
  var tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  var tab = tabs[0];
  var res = null;
  try {                                   // ответил скрипт страницы — значит, это claude.ai
    if (tab) res = await chrome.tabs.sendMessage(tab.id, { type: "probe" });
  } catch (e) {
    res = null;
  }
  if (!res) {
    var onClaude = tab && tab.url && tab.url.indexOf("https://claude.ai/") === 0;
    show("page", onClaude ? "—" : t("popup_not_claude"));
    hint("page_hint", t(onClaude ? "hint_reload" : "hint_open_claude"));
    return;
  }
  {
    var p = res.page;
    var state = p.waiting ? t("page_wait") : p.busy ? t(p.phase === "writing" ? "page_writing" : "page_thinking")
              : res.mode === "done" ? t("page_done") : t("page_idle");
    show("page", state, p.busy || p.waiting ? "ok" : "");
    document.getElementById("signals").textContent = p.signals.join(", ") || "—";
    hint("page_hint", "");
  }
}

document.getElementById("setup").addEventListener("click", function () {
  chrome.tabs.create({ url: SETUP_URL });
  window.close();
});

chrome.storage.local.get(DEFAULTS).then(function (s) {
  var en = document.getElementById("enabled"), port = document.getElementById("port");
  en.checked = s.enabled;
  port.value = s.port;
  en.addEventListener("change", function () { chrome.storage.local.set({ enabled: en.checked }); });
  port.addEventListener("change", function () {
    var v = parseInt(port.value, 10);
    if (v > 0 && v < 65536) { chrome.storage.local.set({ port: v }); checkDaemon(v); }
  });
  checkDaemon(s.port);
  checkPage();
});
