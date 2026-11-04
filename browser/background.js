/*
 * Фоновая часть: пересылает события со страниц claude.ai демону Agent Status Bar
 * (POST http://127.0.0.1:<порт>/?agent=claude-web). Каждая вкладка — отдельная сессия.
 */
var DEFAULTS = { enabled: true, port: 8765 };

function settings() {
  return chrome.storage.local.get(DEFAULTS);
}

async function post(ev) {
  var s = await settings();
  if (!s.enabled) return;
  var url = "http://127.0.0.1:" + s.port + "/?agent=claude-web";
  var ok = false;
  try {
    var r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(ev) });
    ok = r.ok;
  } catch (e) {
    ok = false;
  }
  chrome.storage.session.set({ daemon_ok: ok, daemon_checked: Date.now() });
}

async function rememberTab(tabId) {
  var s = await chrome.storage.session.get({ tabs: [] });
  if (s.tabs.indexOf(tabId) < 0) {
    s.tabs.push(tabId);
    await chrome.storage.session.set({ tabs: s.tabs });
  }
}

async function forgetTab(tabId) {
  var s = await chrome.storage.session.get({ tabs: [] });
  var i = s.tabs.indexOf(tabId);
  if (i < 0) return;
  s.tabs.splice(i, 1);
  await chrome.storage.session.set({ tabs: s.tabs });
  post({ hook_event_name: "SessionEnd", session_id: "tab-" + tabId });
}

chrome.runtime.onMessage.addListener(function (msg, sender) {
  if (!msg || msg.type !== "event" || !sender.tab) return;
  var ev = Object.assign({}, msg.event, { session_id: "tab-" + sender.tab.id });
  rememberTab(sender.tab.id);
  post(ev);
});

// вкладку закрыли или ушли с claude.ai — сессия закончилась
chrome.tabs.onRemoved.addListener(function (tabId) { forgetTab(tabId); });
chrome.tabs.onUpdated.addListener(function (tabId, change) {
  if (change.url && change.url.indexOf("https://claude.ai/") !== 0) forgetTab(tabId);
});
