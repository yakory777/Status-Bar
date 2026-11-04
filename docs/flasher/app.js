/*
 * Страница прошивки и настройки Wi-Fi платы Agent Status Bar.
 * Прошивка — ESP Web Tools (кнопка <esp-web-install-button>), Wi-Fi — Web Serial: те же строки JSON,
 * что шлёт host/daemon.py по кабелю (протокол — firmware/main/net_esp.h):
 *   {"hello":{"name":"web setup"}}   → {"welcome":{"id","fw","trusted","wifi"}}   (без токена — в доверенные не попадаем)
 *   {"wifi_list":1}                   → {"wifi":{"saved":[...],"connected":"SSID"|null,"ip","rssi","id"}}
 *   {"wifi_add":{"ssid","pass"}}      → {"wifi":{..., "rebooting":true}}, плата перезагружается
 *   {"wifi_remove":"SSID"}            → {"wifi":{..., "removed":true, "rebooting":true}}
 */
(function () {
  "use strict";

  var TEXT = {
    title: { en: "Agent Status Bar setup", ru: "Настройка Agent Status Bar" },
    lead: { en: "Flash the board and connect it to Wi-Fi right from the browser — no console, no installs. Plug the board into this computer with a USB-C data cable.",
            ru: "Прошивка платы и подключение к Wi-Fi прямо из браузера — без консоли и установки программ. Подключите плату к этому компьютеру USB-C кабелем с передачей данных." },
    unsupported: { en: "This browser can't talk to USB devices. Open this page in Chrome or Edge on a computer.",
                   ru: "Этот браузер не умеет работать с USB-устройствами. Откройте страницу в Chrome или Edge на компьютере." },
    not_allowed: { en: "Open this page over https.", ru: "Откройте страницу по https." },
    s1_title: { en: "Your board", ru: "Ваша плата" },
    s1_sub: { en: "Tilt the screen against the light: an LCD has a backlight, so black looks grey; an AMOLED is pitch black.",
              ru: "Посмотрите на экран под углом: у LCD есть подсветка, и чёрный на нём серый; у AMOLED чёрный совсем чёрный." },
    lcd_desc: { en: "LCD 1.9″ 320×170 — most common", ru: "LCD 1,9″ 320×170 — самая распространённая" },
    amoled_desc: { en: "AMOLED 1.91″ 536×240", ru: "AMOLED 1,91″ 536×240" },
    untested: { en: "not tested on a board yet", ru: "ещё не проверена на плате" },
    s2_title: { en: "Flash the firmware", ru: "Прошивка" },
    s2_sub: { en: "Latest version:", ru: "Последняя версия:" },
    flash: { en: "Flash the board", ru: "Прошить плату" },
    flash_tip_close: { en: "Close the status bar program on the computer first (Claude Code, the daemon window) — while it runs, the port is busy.",
                       ru: "Сначала закройте программу статус-бара на компьютере (Claude Code, окно демона) — пока она работает, порт занят." },
    flash_tip_boot: { en: "The board doesn't show up or flashing fails: hold BOOT, press RST, release BOOT, and try again.",
                      ru: "Плата не появляется в списке или прошивка не идёт: зажмите BOOT, нажмите RST, отпустите BOOT и попробуйте снова." },
    flash_tip_keep: { en: "The installer asks “Erase device” — leave it unticked and saved Wi-Fi networks stay. Tick it only to wipe the board clean.",
                      ru: "Установщик спросит «Erase device» — оставьте галочку снятой, и сохранённые сети Wi-Fi останутся. Ставьте её, только чтобы стереть плату начисто." },
    s3_title: { en: "Wi-Fi", ru: "Wi-Fi" },
    s3_sub: { en: "The board remembers up to five networks and joins the strongest one nearby. Then it works from any charger.",
              ru: "Плата помнит до пяти сетей и подключается к самой сильной поблизости. После этого её можно питать от любой зарядки." },
    connect: { en: "Connect to the board", ru: "Подключиться к плате" },
    disconnect: { en: "Disconnect", ru: "Отключиться" },
    board_id: { en: "Board", ru: "Плата" },
    firmware: { en: "Firmware", ru: "Прошивка" },
    wifi: { en: "Wi-Fi", ru: "Wi-Fi" },
    saved: { en: "Saved networks", ru: "Сохранённые сети" },
    no_saved: { en: "No networks yet — add one below.", ru: "Сетей пока нет — добавьте ниже." },
    remove: { en: "Remove", ru: "Удалить" },
    add_title: { en: "Add a network", ru: "Добавить сеть" },
    ssid: { en: "Network name", ru: "Имя сети" },
    password: { en: "Password", ru: "Пароль" },
    add: { en: "Add", ru: "Добавить" },
    show_password: { en: "Show password", ru: "Показать пароль" },
    wifi_tip: { en: "2.4 GHz networks only — the board can't see 5 GHz. Type the name exactly as in the network list, with the same capital letters.",
                ru: "Только сети 2,4 ГГц — сети 5 ГГц плата не видит. Имя пишите точно как в списке сетей, с теми же заглавными буквами." },
    s4_title: { en: "Program on the computer", ru: "Программа на компьютере" },
    s4_sub: { en: "To show what Claude Code, Codex or the claude.ai chat is doing, the computer needs the plugin or the browser extension — the step-by-step guide is in the project README.",
              ru: "Чтобы на плате было видно, что делают Claude Code, Codex или чат claude.ai, на компьютере нужен плагин или расширение для браузера — пошаговая инструкция в README проекта." },
    open_repo: { en: "Open the project on GitHub", ru: "Открыть проект на GitHub" },
    footer: { en: "Agent Status Bar · flashing by ESP Web Tools · everything runs in your browser, nothing is sent anywhere",
              ru: "Agent Status Bar · прошивка — ESP Web Tools · всё работает в вашем браузере, никуда ничего не отправляется" },

    st_choose: { en: "Pick the board in the browser window that opens (it may be called “USB JTAG/serial debug unit”).",
                 ru: "Выберите плату в окне браузера (она может называться «USB JTAG/serial debug unit»)." },
    st_hello: { en: "Talking to the board…", ru: "Связываюсь с платой…" },
    st_busy: { en: "The port is busy. Close the status bar program (Claude Code, the daemon), the ESP-IDF monitor or Arduino, then try again.",
               ru: "Порт занят. Закройте программу статус-бара (Claude Code, демон), монитор ESP-IDF или Arduino и попробуйте снова." },
    st_no_answer: { en: "The board doesn't answer. It may have firmware without Wi-Fi — flash it in step 2 first.",
                    ru: "Плата не отвечает. Возможно, на ней прошивка без Wi-Fi — сначала прошейте её на шаге 2." },
    st_connected: { en: "Connected to the board.", ru: "Плата подключена." },
    st_adding: { en: "Saving the network…", ru: "Сохраняю сеть…" },
    st_removing: { en: "Removing the network…", ru: "Удаляю сеть…" },
    st_rebooting: { en: "The board restarts to apply it — reconnecting in a few seconds…",
                    ru: "Плата перезагружается, чтобы применить изменения, — переподключусь через несколько секунд…" },
    st_joining: { en: "Waiting for the board to join Wi-Fi…", ru: "Жду, пока плата подключится к Wi-Fi…" },
    st_joined: { en: "Done! The board is on Wi-Fi.", ru: "Готово! Плата в сети Wi-Fi." },
    st_not_joined: { en: "The board didn't join. Check the password and that the network is 2.4 GHz, then remove it and add again.",
                     ru: "Плата не подключилась. Проверьте пароль и что сеть 2,4 ГГц, затем удалите её и добавьте снова." },
    st_lost: { en: "The board was unplugged. Plug it back in and press “Connect to the board”.",
               ru: "Плата отключена. Подключите её снова и нажмите «Подключиться к плате»." },
    st_reconnect_manual: { en: "Couldn't reconnect by myself — press “Connect to the board”.",
                           ru: "Сам переподключиться не смог — нажмите «Подключиться к плате»." },
    st_error: { en: "Error: {msg}", ru: "Ошибка: {msg}" },
    st_bad_input: { en: "The board rejected the name or password (name up to 32 characters, password up to 63).",
                    ru: "Плата не приняла имя или пароль (имя — до 32 символов, пароль — до 63)." },
    st_installer_failed: { en: "The installer didn't load. Check the internet connection and reload the page.",
                           ru: "Установщик не загрузился. Проверьте интернет и обновите страницу." },
    st_closed_for_flash: { en: "Disconnected so the installer can use the port.", ru: "Отключился, чтобы порт достался установщику." },

    wifi_on: { en: "{ssid} · {ip} · signal {rssi} dBm", ru: "{ssid} · {ip} · сигнал {rssi} дБм" },
    wifi_off: { en: "not connected", ru: "не подключена" },
    fw_latest: { en: "latest", ru: "последняя" },
    fw_update: { en: "update available: {v}", ru: "есть обновление: {v}" },
    confirm_remove: { en: "Remove “{ssid}” from the board?", ru: "Удалить «{ssid}» из памяти платы?" }
  };

  var lang = "en";
  try { lang = localStorage.getItem("asb_lang") || ""; } catch (e) { lang = ""; }
  if (lang !== "en" && lang !== "ru") lang = /^ru\b/i.test(navigator.language || "") ? "ru" : "en";

  function t(key, vars) {
    var s = (TEXT[key] || {})[lang] || key;
    Object.keys(vars || {}).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }

  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-t]").forEach(function (el) { el.textContent = t(el.dataset.t); });
    document.querySelectorAll("[data-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
    });
    document.title = t("title");
    render();
  }

  document.querySelectorAll("[data-lang]").forEach(function (b) {
    b.addEventListener("click", function () {
      lang = b.dataset.lang;
      try { localStorage.setItem("asb_lang", lang); } catch (e) { /* без запоминания */ }
      applyLang();
    });
  });

  var $ = function (id) { return document.getElementById(id); };
  var hasSerial = "serial" in navigator;
  if (!hasSerial) $("unsupported").hidden = false;

  /* ---------- выбор платы и версия прошивки ---------- */

  var latest = null;
  var MANIFESTS = { lcd: "manifest-lcd.json", amoled: "manifest-amoled.json" };

  function chooseBoard(kind) {
    $("installer").setAttribute("manifest", MANIFESTS[kind]);
    fetch(MANIFESTS[kind], { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (m) { latest = m.version; $("fw_version").textContent = m.version; render(); })
      .catch(function () { $("fw_version").textContent = "?"; });
  }
  document.querySelectorAll('input[name="board"]').forEach(function (r) {
    r.addEventListener("change", function () { if (r.checked) chooseBoard(r.value); });
  });
  chooseBoard((document.querySelector('input[name="board"]:checked') || {}).value || "lcd");

  /* ---------- связь с платой по Web Serial ---------- */

  var ESPRESSIF_VID = 0x303A;
  var port = null, reader = null, closing = false;
  var connecting = false, reconnecting = false;
  var openedAt = 0;                       // порт пропал вскоре после открытия — плата перезагрузилась, а не выдернута
  var waiters = [];
  var info = { id: null, fw: null, wifi: null };
  var statusKey = "", statusCls = "", statusVars = null;
  var expectReboot = false;

  function setStatus(key, cls, vars) {
    statusKey = key; statusCls = cls || "info"; statusVars = vars || null;
    var el = $("status");
    el.className = "status " + (key ? statusCls : "");
    el.textContent = key ? t(key, vars) : "";
  }

  function onLine(line) {
    if (line.charAt(0) !== "{") return;                // журнал платы — не наше
    var msg;
    try { msg = JSON.parse(line); } catch (e) { return; }
    waiters = waiters.filter(function (w) {
      if (msg && Object.prototype.hasOwnProperty.call(msg, w.key)) { w.resolve(msg); return false; }
      return true;
    });
  }

  function waitFor(key, ms) {
    return new Promise(function (resolve) {
      var w = { key: key, resolve: resolve };
      waiters.push(w);
      setTimeout(function () {
        var i = waiters.indexOf(w);
        if (i >= 0) { waiters.splice(i, 1); resolve(null); }
      }, ms);
    });
  }

  async function send(obj) {
    if (!port) throw new Error("not connected");
    var w = port.writable.getWriter();
    try { await w.write(new TextEncoder().encode(JSON.stringify(obj) + "\n")); }
    finally { w.releaseLock(); }
  }

  async function request(obj, key, ms) {
    if (!port) return null;
    var p = waitFor(key, ms || 3000);
    try { await send(obj); } catch (e) { return null; }      // порт пропал посреди запроса
    return p;
  }

  async function readLoop(p) {
    var dec = new TextDecoder(), buf = "";
    reader = p.readable.getReader();
    try {
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        buf += dec.decode(r.value, { stream: true });
        var i;
        while ((i = buf.indexOf("\n")) >= 0) {
          var line = buf.slice(0, i).trim();
          buf = buf.slice(i + 1);
          if (line) onLine(line);
        }
        if (buf.length > 4096) buf = "";
      }
    } catch (e) {
      /* кабель выдернули или плата перезагрузилась */
    } finally {
      try { reader.releaseLock(); } catch (e) { /* уже отпущен */ }
      reader = null;
    }
    if (!closing) onPortLost(p);
  }

  async function openPort(p) {
    try {
      await p.open({ baudRate: 115200 });
    } catch (e) {
      var busy = /busy|in use|access|failed to open/i.test(String(e && e.message));
      throw new Error(busy ? "busy" : String(e && e.message || e));
    }
    // Линии DTR/RTS не трогаем: у ESP32-S3 по USB их переключение — команда перезагрузки
    port = p;
    closing = false;
    openedAt = Date.now();
    readLoop(p);
  }

  async function closePort() {
    closing = true;
    var p = port;
    port = null;
    if (reader) { try { await reader.cancel(); } catch (e) { /* уже закрыт */ } }
    if (p) { try { await p.close(); } catch (e) { /* уже закрыт */ } }
  }

  async function greet() {
    // Плата могла перезагрузиться при открытии порта — несколько попыток
    for (var k = 0; k < 4; k++) {
      if (!port) return false;
      var hello = await request({ hello: { name: "web setup" } }, "welcome", 2000);
      if (hello) {
        info.id = hello.welcome.id || null;
        info.fw = hello.welcome.fw || null;
        return true;
      }
    }
    return false;
  }

  async function refreshWifi() {
    var r = await request({ wifi_list: 1 }, "wifi", 3000);
    if (r && r.wifi) { info.wifi = r.wifi; if (r.wifi.id) info.id = r.wifi.id; }
    render();
    return r && r.wifi;
  }

  async function connect(p) {
    setStatus(p ? "st_hello" : "st_choose");
    try {
      if (!p) {
        p = await navigator.serial.requestPort({ filters: [{ usbVendorId: ESPRESSIF_VID }] });
        setStatus("st_hello");
      }
      connecting = true;
      await openPort(p);
    } catch (e) {
      connecting = false;
      if (e && e.name === "NotFoundError") { setStatus(""); return false; }      // окно выбора закрыли
      setStatus(e.message === "busy" ? "st_busy" : "st_error", "bad", { msg: e.message });
      return false;
    }
    var ok = await greet();
    connecting = false;
    if (!ok && (reconnecting || !port)) return false;      // плата перезагрузилась — переподключение идёт само
    if (!ok) {
      await closePort();
      setStatus("st_no_answer", "bad");
      render();
      return false;
    }
    await refreshWifi();
    setStatus("st_connected", "ok");
    return true;
  }

  // Плата перезагружается после изменения сетей: порт пропадает и появляется снова
  async function onPortLost(p) {
    port = null;
    if (!expectReboot && !connecting && Date.now() - openedAt > 5000) {
      info = { id: null, fw: null, wifi: null };
      setStatus("st_lost", "warn");
      render();
      return;
    }
    var afterChange = expectReboot;          // перезагрузка после изменения сетей, а не при подключении
    expectReboot = false;
    connecting = false;
    reconnecting = true;
    setStatus(afterChange ? "st_rebooting" : "st_hello", "info");
    render();
    var deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      await sleep(1000);
      var ports = await navigator.serial.getPorts();
      var again = ports.filter(function (x) {
        var i = x.getInfo ? x.getInfo() : {};
        return x === p || i.usbVendorId === ESPRESSIF_VID;
      })[0];
      if (!again) continue;
      try { await openPort(again); } catch (e) { continue; }
      if (await greet()) {
        reconnecting = false;
        if (afterChange) await waitJoined();
        else { await refreshWifi(); setStatus("st_connected", "ok"); }
        return;
      }
      await closePort();
    }
    reconnecting = false;
    setStatus("st_reconnect_manual", "warn");
    render();
  }

  async function waitJoined() {
    setStatus("st_joining", "info");
    var deadline = Date.now() + 30000;
    while (Date.now() < deadline && port) {
      var w = await refreshWifi();
      if (w && w.connected) { setStatus("st_joined", "ok"); return; }
      if (w && !(w.saved || []).length) { setStatus("st_connected", "ok"); return; }   // сетей не осталось — ждать нечего
      await sleep(3000);
    }
    if (port) setStatus("st_not_joined", "warn");
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  async function changeNetworks(cmd, busyKey) {
    setStatus(busyKey, "info");
    var r = await request(cmd, "wifi", 4000);
    if (!r || !r.wifi) { setStatus("st_no_answer", "bad"); return; }
    if (r.wifi.error) { setStatus("st_bad_input", "bad"); return; }
    info.wifi = r.wifi;
    render();
    if (r.wifi.rebooting) {
      expectReboot = true;
      setStatus("st_rebooting", "info");
    }
  }

  /* ---------- отрисовка ---------- */

  function render() {
    var on = !!port;
    $("connect").hidden = on;
    $("disconnect").hidden = !on;
    $("connect").disabled = !hasSerial;
    $("panel").hidden = !(on && info.wifi);
    if (statusKey) setStatus(statusKey, statusCls, statusVars);

    $("i_id").textContent = info.id || "—";
    var fw = $("i_fw");
    fw.textContent = "";
    if (info.fw) {
      fw.append(info.fw + " ");
      if (latest) {
        var pill = document.createElement("span");
        var newer = compare(latest, info.fw) > 0;
        pill.className = "pill " + (newer ? "warn" : "ok");
        pill.textContent = newer ? t("fw_update", { v: latest }) : t("fw_latest");
        fw.append(pill);
      }
    } else {
      fw.textContent = "—";
    }

    var w = info.wifi || {};
    var wi = $("i_wifi");
    wi.textContent = "";
    var pill2 = document.createElement("span");
    pill2.className = "pill " + (w.connected ? "ok" : "warn");
    pill2.textContent = w.connected
      ? t("wifi_on", { ssid: w.connected, ip: w.ip || "?", rssi: w.rssi != null ? w.rssi : "?" })
      : t("wifi_off");
    wi.append(pill2);

    var ul = $("nets");
    ul.textContent = "";
    var saved = w.saved || [];
    if (!saved.length) {
      var li0 = document.createElement("li");
      li0.className = "empty";
      li0.textContent = t("no_saved");
      ul.append(li0);
    }
    saved.forEach(function (ssid) {
      var li = document.createElement("li");
      var name = document.createElement("span");
      name.textContent = ssid;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn ghost small";
      b.textContent = t("remove");
      b.addEventListener("click", function () {
        if (confirm(t("confirm_remove", { ssid: ssid }))) changeNetworks({ wifi_remove: ssid }, "st_removing");
      });
      li.append(name, b);
      ul.append(li);
    });
  }

  function compare(a, b) {
    var x = String(a).split("."), y = String(b).split(".");
    for (var i = 0; i < Math.max(x.length, y.length); i++) {
      var d = (parseInt(x[i], 10) || 0) - (parseInt(y[i], 10) || 0);
      if (d) return d;
    }
    return 0;
  }

  /* ---------- кнопки ---------- */

  $("connect").addEventListener("click", function () { connect(null); });
  $("disconnect").addEventListener("click", async function () {
    await closePort();
    info = { id: null, fw: null, wifi: null };
    setStatus("");
    render();
  });
  $("add").addEventListener("submit", function (e) {
    e.preventDefault();
    var ssid = $("ssid").value.trim();
    if (!ssid || !port) return;
    changeNetworks({ wifi_add: { ssid: ssid, pass: $("pass").value } }, "st_adding");
    $("ssid").value = "";
    $("pass").value = "";
  });
  $("showpass").addEventListener("change", function () {
    $("pass").type = $("showpass").checked ? "text" : "password";
  });

  // Перед прошивкой отдаём порт установщику
  $("installer").addEventListener("click", async function () {
    if (port) { await closePort(); info = { id: null, fw: null, wifi: null }; setStatus("st_closed_for_flash", "info"); render(); }
  }, true);

  // ESP Web Tools грузится с unpkg; не загрузился — скажем, а не оставим немую кнопку
  var installerFailed = false;
  setTimeout(function () {
    if (!customElements.get("esp-web-install-button")) { installerFailed = true; showInstallerState(); }
  }, 8000);
  function showInstallerState() {
    var el = $("flash_status");
    el.className = "status " + (installerFailed ? "bad" : "");
    el.textContent = installerFailed ? t("st_installer_failed") : "";
  }
  var renderBase = render;
  render = function () { renderBase(); showInstallerState(); };

  applyLang();
})();
