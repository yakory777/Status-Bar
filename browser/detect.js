/*
 * Что сейчас происходит на странице claude.ai. Всё, что зависит от вёрстки claude.ai, — только здесь.
 * Если сайт поменяется и статус перестанет определяться, правьте этот файл: в окне расширения
 * видно, какие признаки сработали.
 *
 * detectPage() → { busy, phase: "thinking"|"writing", waiting, prompt, title, signals: [...] }
 */
var AgentStatusDetect = (function () {
  // Ответ в процессе: у сообщения Claude стоит data-is-streaming="true"
  var STREAMING = '[data-is-streaming="true"]';
  // ...и в поле ввода вместо «Отправить» кнопка «Остановить»
  var STOP_BUTTON = 'button[aria-label*="Stop" i], button[aria-label*="Остановить" i]';
  // Последнее сообщение пользователя
  var USER_MESSAGE = '[data-testid="user-message"]';
  // Окно разрешения для инструмента (MCP, поиск и т. п.)
  var ALLOW_TEXT = /^(allow once|always allow|allow always|allow for this chat|разрешить|разрешить один раз|разрешить всегда|всегда разрешать)$/i;
  // Заголовок вкладки: «Название чата - Claude». Просто «Claude», «Claude Code», «Новый чат» — не название
  var TITLE_SUFFIX = /\s*[-–|·]\s*Claude( Code)?\s*$/i;
  var GENERIC_TITLES = /^(claude|claude code|claude\.ai|new chat|new session|новый чат|новая сессия)?$/i;
  // Поле ввода и кнопка отправки — запасной способ узнать вопрос, если сообщение на странице не нашлось
  var COMPOSER = 'textarea, [contenteditable="true"]';
  var SEND_BUTTON = /send|отправить/i;

  var typed = "";             // последний отправленный текст из поля ввода

  function rememberComposer(el) {
    var v = el && (el.value !== undefined && el.tagName === "TEXTAREA" ? el.value : text(el));
    v = (v || "").replace(/\s+/g, " ").trim();
    if (v) typed = v.slice(0, 200);
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
    var el = e.target && e.target.closest && e.target.closest(COMPOSER);
    if (el) rememberComposer(el);
  }, true);

  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest && e.target.closest("button");
    if (!b || !SEND_BUTTON.test(b.getAttribute("aria-label") || "")) return;
    var form = b.closest("form, fieldset") || document;
    rememberComposer(form.querySelector(COMPOSER));
  }, true);

  function visible(el) {
    if (!el) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function text(el) {
    return el ? (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim() : "";
  }

  function lastOf(selector) {
    var all = document.querySelectorAll(selector);
    return all.length ? all[all.length - 1] : null;
  }

  function chatTitle() {
    var t = (document.title || "").replace(TITLE_SUFFIX, "").trim();
    return GENERIC_TITLES.test(t) ? "" : t;
  }

  function waitingForPermission() {
    var buttons = document.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      if (ALLOW_TEXT.test(text(buttons[i])) && visible(buttons[i])) return true;
    }
    return false;
  }

  function detectPage() {
    var signals = [];
    var streamEl = lastOf(STREAMING);
    var stop = Array.prototype.filter.call(document.querySelectorAll(STOP_BUTTON), visible)[0];
    if (streamEl) signals.push("streaming");
    if (stop) signals.push("stop_button");
    var busy = !!(streamEl || stop);

    // Пишет — в отвечаемом сообщении уже есть текст; до этого — думает
    var phase = "thinking";
    if (streamEl && text(streamEl).length > 0) phase = "writing";

    var waiting = waitingForPermission();
    if (waiting) signals.push("allow_button");

    var user = lastOf(USER_MESSAGE);
    if (user) signals.push("user_message");
    if (!user && typed) signals.push("typed");

    return { busy: busy, phase: phase, waiting: waiting, prompt: (text(user) || typed).slice(0, 200),
             title: chatTitle(), signals: signals };
  }

  return { detectPage: detectPage };
})();
