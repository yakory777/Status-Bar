/*
 * Смотрит на страницу claude.ai раз в полсекунды и сообщает фоновой части расширения
 * о переменах: новый вопрос, думает/пишет, ждёт разрешения, готово.
 */
(function () {
  var TICK_MS = 500;
  var DONE_AFTER_MS = 1500;       // ответ кончился, если «занят» не появлялся полторы секунды
  var KEEPALIVE_MS = 30000;       // пока занят — напоминаем демону (вдруг он перезапустился)

  var mode = "idle";              // idle | busy | wait | done
  var phase = "";
  var title = "";
  var lastSent = 0;
  var quietSince = 0;
  var last = null;

  function send(name, extra) {
    var ev = Object.assign({ hook_event_name: name }, extra || {});
    lastSent = Date.now();
    try {
      chrome.runtime.sendMessage({ type: "event", event: ev });
    } catch (e) {
      // расширение перезагрузили — эта копия скрипта больше не нужна
      clearInterval(timer);
    }
  }

  function tick() {
    var p = AgentStatusDetect.detectPage();
    last = p;
    var now = Date.now();
    var info = { prompt: p.prompt, title: p.title };

    if (p.waiting) {
      quietSince = 0;
      if (mode === "idle" || mode === "done") send("WebPrompt", info);
      if (mode !== "wait") send("WebWait", info);
      mode = "wait";
      return;
    }
    if (p.busy) {
      quietSince = 0;
      if (mode === "idle" || mode === "done") {
        send("WebPrompt", info);
        phase = "";
      }
      if (mode !== "busy" || p.phase !== phase || p.title !== title || now - lastSent > KEEPALIVE_MS) {
        send("WebBusy", Object.assign({ phase: p.phase }, info));
      }
      mode = "busy";
      phase = p.phase;
      title = p.title;
      return;
    }
    if (mode === "busy" || mode === "wait") {
      if (!quietSince) quietSince = now;
      if (now - quietSince >= DONE_AFTER_MS) {
        send("WebDone");
        mode = "done";
        quietSince = 0;
      }
    }
  }

  // окно расширения спрашивает, что видно на странице
  chrome.runtime.onMessage.addListener(function (msg, _sender, reply) {
    if (msg && msg.type === "probe") {
      reply({ mode: mode, page: last || AgentStatusDetect.detectPage() });
    }
  });

  var timer = setInterval(tick, TICK_MS);
  tick();
})();
