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
  // Кнопкой на плате: «удержать» — разрешить один раз (не «всегда»), «нажать» — отклонить
  var ALLOW_ONCE = /^(allow once|allow for this chat|allow|разрешить один раз|разрешить)$/i;
  var DENY_TEXT = /^(deny|decline|don['’]t allow|do not allow|reject|cancel|отклонить|запретить|не разрешать|отмена)$/i;
  // Вопрос с вариантами (AskUserQuestion в Claude Code): «Submit» отправляет выбранный вариант, «Skip» пропускает
  var SUBMIT_TEXT = /^(submit|отправить|ответить)$/i;
  var SKIP_TEXT = /^(skip|пропустить)$/i;
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

  // Подсказка с сочетанием клавиш внутри кнопки: «Allow once Ctrl ⏎» — её отбрасываем
  var SHORTCUT_TAIL = /(\s*(ctrl|cmd|command|alt|option|shift|enter|return|esc|⌘|⌥|⇧|⌃|⏎|↵|↩|\+))+\s*$/i;

  /* Надпись кнопки без <kbd> и значков клавиш */
  function label(b) {
    var c = b.cloneNode(true);
    Array.prototype.forEach.call(c.querySelectorAll("kbd, svg, [aria-hidden='true']"), function (k) { k.remove(); });
    return text(c).replace(SHORTCUT_TAIL, "").trim();
  }

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

  function allowButton() {
    var buttons = document.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      if (visible(buttons[i]) && ALLOW_TEXT.test(label(buttons[i]))) return buttons[i];
    }
    return null;
  }

  /* Окно вопроса: «Submit» рядом со «Skip». Возвращает «Submit» или null */
  function questionSubmit() {
    var buttons = document.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (visible(b) && SUBMIT_TEXT.test(label(b)) && findButton(SKIP_TEXT, b)) return b;
    }
    return null;
  }

  /* Текст вопроса: первая строка окна с кнопкой «Submit» */
  function questionText(submit) {
    var el = submit.parentElement;
    for (var depth = 0; el && depth < 8; depth++, el = el.parentElement) {
      if (el.querySelector("input[type=radio], input[type=checkbox], [role=radio], [role=checkbox], [role=option]")) {
        var first = (el.innerText || "").split("\n").map(function (s) { return s.trim(); }).filter(Boolean)[0];
        return first ? first.slice(0, 120) : "";
      }
    }
    return "";
  }

  function waitingForPermission() {
    return !!allowButton();
  }

  /* Что просят разрешить: команда из блока кода в том же окне, иначе его заголовок */
  function permissionRequest(allow) {
    var el = allow.parentElement;
    for (var depth = 0; el && depth < 8; depth++, el = el.parentElement) {
      var code = el.querySelector("pre, code");
      if (code && text(code)) return { command: text(code).replace(/^\$\s*/, "").slice(0, 120) };
      var head = el.querySelector("h1, h2, h3, h4, [role='heading']");
      if (head && text(head) && depth >= 3) return { message: text(head).slice(0, 120) };
    }
    return {};
  }

  function matchIn(root, re) {
    var buttons = root.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (visible(b) && !b.disabled && re.test(label(b))) return b;
    }
    return null;
  }

  /* Кнопка с подходящей надписью — ищем сначала в ближайших к near контейнерах (то же окно разрешения) */
  function findButton(re, near) {
    if (!near) return matchIn(document, re);
    var el = near.parentElement;
    for (var depth = 0; el && depth < 8; depth++, el = el.parentElement) {
      var b = matchIn(el, re);
      if (b) return b;
    }
    return null;
  }

  /* Нажать в окне разрешения: "allow" — «Разрешить один раз», "deny" — «Отклонить». true — нажато. */
  function answerPermission(decision) {
    var allow = allowButton();
    var target = null;
    if (allow) {
      target = decision === "allow" ? findButton(ALLOW_ONCE, allow) || allow : findButton(DENY_TEXT, allow);
    } else {
      var submit = questionSubmit();                       // вопрос: удержать — отправить выбранный вариант
      if (!submit) return false;
      target = decision === "allow" ? submit : findButton(SKIP_TEXT, submit);
    }
    if (!target) return false;
    target.click();
    return true;
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

    var allow = allowButton();
    var submit = allow ? null : questionSubmit();
    var waiting = !!(allow || submit);
    var request = allow ? permissionRequest(allow) : submit ? { message: questionText(submit) } : {};
    if (allow) signals.push("allow_button");
    if (submit) signals.push("question");
    if (waiting && findButton(DENY_TEXT, allow)) signals.push("deny_button");
    if (request.command) signals.push("command");

    var user = lastOf(USER_MESSAGE);
    if (user) signals.push("user_message");
    if (!user && typed) signals.push("typed");

    return { busy: busy, phase: phase, waiting: waiting, request: request, prompt: (text(user) || typed).slice(0, 200),
             title: chatTitle(), signals: signals };
  }

  return { detectPage: detectPage, answerPermission: answerPermission };
})();
