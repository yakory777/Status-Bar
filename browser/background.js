/*
 * Фоновая часть: пересылает события со страниц claude.ai демону Agent Status Bar
 * (POST http://127.0.0.1:<порт>/?agent=claude-web). Каждая вкладка — отдельная сессия.
 */
var DEFAULTS = { enabled: true, port: 8765 };

function settings() {
  return chrome.storage.local.get(DEFAULTS);
}

var WAIT_S = 110;                 // сколько демон держит запрос, ожидая кнопку на плате

/* Отправить событие. WebWait — длинный запрос: демон ответит {"decision": "allow"|"deny"},
   когда на плате нажмут кнопку, или пустым ответом, если в чате ответили сами. */
async function post(ev, tabId) {
  var s = await settings();
  if (!s.enabled) return;
  var wait = ev.hook_event_name === "WebWait";
  var url = "http://127.0.0.1:" + s.port + "/?agent=claude-web" + (wait ? "&wait=" + WAIT_S : "");
  var ok = false, body = null;
  try {
    var r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(ev) });
    ok = r.ok;
    if (wait && r.status === 200) body = await r.json();
  } catch (e) {
    ok = false;
  }
  chrome.storage.session.set({ daemon_ok: ok, daemon_checked: Date.now() });
  if (body && body.decision && tabId !== undefined) {
    chrome.tabs.sendMessage(tabId, { type: "decision", decision: body.decision }, function (res) {
      void chrome.runtime.lastError;
      chrome.storage.session.set({ last_decision: { decision: body.decision, clicked: !!(res && res.ok),
                                                    at: Date.now() } });
    });
  }
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
  post(ev, sender.tab.id);
});

// вкладку закрыли или ушли с claude.ai — сессия закончилась
chrome.tabs.onRemoved.addListener(function (tabId) { forgetTab(tabId); });
chrome.tabs.onUpdated.addListener(function (tabId, change) {
  if (change.url && change.url.indexOf("https://claude.ai/") !== 0) forgetTab(tabId);
});
