# AGENTS.md

Instructions for AI coding agents (Codex, Claude Code and others) working in this repository.

## What this is

A physical status display for coding-agent tasks. Three parts, deliberately decoupled:

- `firmware/` — ESP-IDF 5.x project in C, UI on LVGL 9.2. Two boards, chosen in Kconfig (`ASB_BOARD_*`): LilyGO T-Display-S3 LCD (ST7789 320×170, `display_st7789.c`) and T-Display-S3 AMOLED (RM67162 536×240, `display_rm67162.c`). The UI always renders at 536×240; the LCD driver scales each flushed area down with `display_scale.c` (pure C, testable on a PC). Both drivers implement `display.h`.
- `host/` — Python daemon. Receives hook events over HTTP on `127.0.0.1:8765`, maps them to a screen state through `host/adapters/`, keeps one state per session in `host/sessions.py` and sends the most important one (wait > error > work > done > idle) as JSON lines over USB serial, plus `{"ping":1}` every 5 s.
- `tools/sim/` — firmware simulator: compiles `firmware/main/ui_*.c` and `protocol.c` with LVGL on a PC and renders scenarios from `tools/sim/scenarios/*.txt` to GIF. Use it to verify any change to screen code; CI runs all scenarios.
- `firmware/main/ui_*.c` — everything that draws: `ui_status.c` (task screen, themes, scenario states), `ui_scene_*.c` (idle scenes), `ui_screen.c` (splash, transitions, confetti, sleep, pairing), `ui_icons.c` (battery, Wi-Fi), `ui_draw.c` (drawing helpers). They must not touch hardware directly — only through `platform.h`, implemented by `platform_esp.c` on the board and `tools/sim/sim_platform.c` in the simulator.
- `tools/render_*.py` — the original design previews in Python. The idle scenes were ported from them; keep timings in sync if you change either side. README GIFs of the firmware come from the simulator: `python tools/sim/render_docs.py` renders every screen in both themes and both languages into `docs/firmware/<en|ru>/<claude|codex>/`. Add new screens to its `JOBS` table and to the gallery in both READMEs; new task texts in scenarios need an English line in its `EN` table.
- `host/links.py` and `firmware/main/net_esp.c` — the link to the board: USB serial or Wi-Fi (UDP discovery and TCP on port 8766, same JSON lines). Control messages (`hello`, `welcome`, `pair_required`, `pair` + `pair_token`, `paired`, `wifi_add`/`wifi_remove`/`wifi_list`) are documented in `net_esp.h` and never reach `protocol.c`. Over USB the board trusts the computer at once; over Wi-Fi only after pairing (code on screen + button). Wi-Fi networks can only be changed over USB.
- `host/scenes.py` — which idle scenes each theme offers.
- `host/config.py` — settings: defaults < `~/.agent-status/config.toml` < `AGENT_STATUS_*` env vars; `state.json` keeps what the daemon remembers (scene picked with the button). `python host/daemon.py config` prints the effective values.
- `host/i18n.py` and `firmware/main/ui_i18n.c` — every text on the screen in English and Russian.
- `hooks/` plus the plugin manifests — wire Claude Code (`hooks/hooks.json`) and Codex (`hooks/codex-hooks.json`) events to `hooks/forward.py`.
- `browser/` — Chrome extension (Manifest V3) for the claude.ai chat, which has no hooks. `detect.js` is the only file that knows claude.ai markup; `content.js` turns what it sees into `WebPrompt`/`WebBusy`/`WebWait`/`WebDone` events; `background.js` posts them to the daemon as agent `claude-web` (one session per tab, `SessionEnd` when the tab closes). `host/adapters/claude_web.py` maps them to the screen with the Claude theme (`THEME` in the adapter). Popup texts live in `browser/_locales/<en|ru>/messages.json`. The chat cannot start the daemon: `tools/windows/autostart.cmd` adds it to Windows sign-in.

The firmware must stay agent-agnostic. Agent-specific logic belongs in `host/adapters/` only.

## The contract between host and firmware

One JSON object per line, UTF-8:

```json
{"state":"work","title":"...","step":"...","done":3,"total":5,"sub":0,"others":0,"agent":"claude","idle":"robot"}
{"ping":1}
```

- `state`: `idle` | `start` | `work` | `wait` | `done` | `error` | `compact`
- `sub`: running subagents; `others`: other active sessions
- `approve`: `true` when the current wait can be answered with the button
- `ping`: keep-alive; the board shows “link lost” after `PROTO_LINK_TIMEOUT_MS` of silence
- `title`, `step`: optional strings; omitted means "keep the previous text"
- `done`, `total`: integers, `total` is clamped to 1..12 on the board
- `agent`: `claude` | `codex` — theme; `idle`: idle scene name from `host/scenes.py`
- `lang`: `en` | `ru` — language of the board's own labels

Every field is optional; the board keeps the last value. Do not change this format without updating `host/sessions.py`, `firmware/main/protocol.c`, the simulator scenarios and the Protocol section of both READMEs.

## Commands

```bash
# Python: syntax check and adapter smoke test (no hardware needed)
python -m py_compile hooks/forward.py host/*.py host/adapters/*.py tools/*.py tools/sim/*.py
python tests/test_adapters.py
python tests/test_links.py          # Wi-Fi link against a fake board

# Validate manifests
python -m json.tool .claude-plugin/plugin.json > /dev/null
python -m json.tool .codex-plugin/plugin.json > /dev/null

# Browser extension
for f in browser/*.js; do node --check "$f"; done

# Screen code in the simulator (cmake + C compiler, no ESP-IDF)
python tools/sim/render.py tools/sim/scenarios/basic.txt build/basic.gif

# Firmware (requires ESP-IDF 5.1+)
cd firmware && idf.py set-target esp32s3 && idf.py build
```

## Rules

- `hooks/forward.py` must always exit 0 and must never block the agent for long: keep network timeouts short. The only thing it may print to stdout is the PermissionRequest decision when `button_approve` is on (the default; the daemon waits only while a board is connected) and the button was pressed; the wait is capped by `AGENT_STATUS_APPROVE_WAIT` (≤120 s, below the hook timeout of 130 s in `hooks/hooks.json`).
- During a `wait` without `approve`, the board's presses only show *Answer on the computer* (`wait_hint()` in `ui_input.c`) — they must not mute or switch scenes there.
- Board → host lines are `{"button":"approve"|"deny"}` and `{"button":"scene_next","scene":...}`, handled in `handle_board_line()` in `host/daemon.py`. Approvals live in `host/approvals.py`.
- The boot splash (`splash_draw()` in `ui_screen.c`) waits for Wi-Fi up to `UI_SPLASH_MAX_MS`, never shorter than `UI_SPLASH_MIN_MS`, and leaves early on Wi-Fi, a task, a pairing request or a button press (`tick_cb()`); its end time may only move closer. `platform_wifi_configured()` tells it whether there is anything to wait for; in the simulator `{"sim":{"wifi_saved":false}}` turns that off. The firmware fonts are subsets — draw symbols such as ✓ with `d_line`, not as glyphs.
- Battery, Wi-Fi and mute indicators (`ui_icons.c`) must stay visible on every screen. A new full-screen object on `lv_layer_top()` goes below them: call `ui_icons_to_front()` after creating it. Position objects by constants, not `lv_obj_get_width()` before the first layout — it returns 0 then.
- Button and buzzer pins are Kconfig options (`firmware/main/Kconfig.projbuild`), not hard-coded.
- `hardware/case/lcd/` is the LCD + 103565 case: `geometry.py` (pure Python, also inlined into the Fusion 360 script), `fusion_builder.py`, `make.py` (fit checks, `fusion/AgentStatusBarCase/`). Parts are boxes: `solids` minus `holes` plus `inner` (features inside the cut cavity), then round `cyl_holes`, side `prisms` (legs), the front `logo` and the wall `deco` slots (sketch profiles cut in Fusion). Fusion is the source of the STL files (exported by the script). Edit `geometry.py`, rerun `make.py` — it must report no clashes.
- `hardware/case/amoled/case.py` generates the AMOLED case STL files; edit `PARAMS` there and keep `case.scad` in sync. Run it and check that every part reports watertight.
- Python on the host side: standard library only, except `pyserial` in the daemon (imported lazily, so `daemon.py config` works without it). `hooks/forward.py` imports `host/config.py` on every event — keep it light.
- Never hard-code a user-facing string: on the board use `tr()` from `ui_i18n.h`, on the host `i18n.t()`, and add both `en` and `ru`. Host log lines are English.
- Firmware: all LVGL calls go through `ui_lock()`/`ui_unlock()` in `main.c`; LVGL is not thread-safe.
- LVGL 9.2: object fields are private — use accessors (`lv_obj_get_coords`, `dctx_from_event`), not `obj->coords`.
- After changing anything in `firmware/main/ui_*.c`, run the relevant simulator scenario and look at the frames (`--png-at`).
- Keep `README.md` (English) and `README.ru.md` (Russian) in sync when behavior or setup changes.
- The project logo (`docs/logo/logo.svg`) is drawn in three places with the same shapes on a 100 × 100 grid: the SVG, `draw_logo()` in `ui_screen.c` (the splash opens with it for `LOGO_INTRO` seconds) and `LOGO` in `hardware/case/lcd/geometry.py` (engraved on the case front). Change all three together; the README banners `docs/logo/banner-*.png` are rendered from the SVG.
- Mascots are original characters. Do not add logos or brand characters of Anthropic, OpenAI or anyone else; brand colors are fine.
- Bump `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `.codex-plugin/plugin.json` together.
- Never hard-code screen sizes in UI code beyond `UI_W`/`UI_H` (536×240): the LCD board relies on scaling that size.
- `firmware/prebuilt/agent-status-bar-tdisplay-s3.bin` (LCD) and `…-tdisplay-s3-amoled.bin` are merged images (bootloader, partition table, app) flashed at `0x0` by the beginner guide and the setup page. Rebuild both and replace them whenever firmware or `sdkconfig.defaults` change, or say clearly that they are out of date. Bump `FW_VERSION` in `firmware/main/version.h` and `version` in `docs/flasher/manifest-*.json` together — the Pages workflow refuses to deploy if they differ.
- `docs/flasher/` is the setup page published by `.github/workflows/pages.yml` together with the prebuilt images (Pages source: GitHub Actions). It flashes with ESP Web Tools and talks to the board over Web Serial with the same JSON lines as the daemon; its `hello` carries no token on purpose, so the page never becomes a trusted computer. Its texts live in `TEXT` in `app.js`, both `en` and `ru`.
- `firmware/partitions.csv` keeps `nvs` (Wi-Fi networks, trusted computers) AFTER the app partition on purpose: the merged prebuilt image is written from `0x0` to the end of the app, and anything inside that span is erased on every flash. Never move `nvs` in front of the app.
- claude.ai markup changes without notice. Keep selectors in `browser/detect.js` with fallbacks, show which signals fired in the popup, and say that detection is unverified against the live site unless someone checked it there.
- Hardware behavior cannot be verified in CI. Say so explicitly instead of claiming firmware changes work.
