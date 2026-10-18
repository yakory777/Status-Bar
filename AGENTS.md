# AGENTS.md

Instructions for AI coding agents (Codex, Claude Code and others) working in this repository.

## What this is

A physical status display for coding-agent tasks. Three parts, deliberately decoupled:

- `firmware/` — ESP-IDF 5.x project in C for the LilyGO T-Display-S3 AMOLED (536×240, RM67162 over QSPI), UI on LVGL 9.2.
- `host/` — Python daemon. Receives hook events over HTTP on `127.0.0.1:8765`, maps them to a screen state through `host/adapters/`, keeps one state per session in `host/sessions.py` and sends the most important one (wait > error > work > done > idle) as JSON lines over USB serial, plus `{"ping":1}` every 5 s.
- `tools/sim/` — firmware simulator: compiles `firmware/main/ui_*.c` and `protocol.c` with LVGL on a PC and renders scenarios from `tools/sim/scenarios/*.txt` to GIF. Use it to verify any change to screen code; CI runs all scenarios.
- `firmware/main/ui_*.c` — everything that draws: `ui_status.c` (task screen, themes, scenario states), `ui_scene_*.c` (idle scenes), `ui_screen.c` (splash, transitions, confetti, sleep, pairing), `ui_icons.c` (battery, Wi-Fi), `ui_draw.c` (drawing helpers). They must not touch hardware directly — only through `platform.h`, implemented by `platform_esp.c` on the board and `tools/sim/sim_platform.c` in the simulator.
<<<<<<< HEAD
- `tools/render_*.py` — the original design previews in Python. The idle scenes were ported from them; keep timings in sync if you change either side. README GIFs of the firmware come from the simulator: `python tools/sim/render_docs.py` renders every screen in both themes and both languages into `docs/firmware/<en|ru>/<claude|codex>/`. Add new screens to its `JOBS` table and to the gallery in both READMEs; new task texts in scenarios need an English line in its `EN` table.
- `host/scenes.py` — which idle scenes each theme offers.
- `host/config.py` — settings: defaults < `~/.agent-status/config.toml` < `AGENT_STATUS_*` env vars; `state.json` keeps what the daemon remembers (scene picked with the button). `python host/daemon.py config` prints the effective values.
- `host/i18n.py` and `firmware/main/ui_i18n.c` — every text on the screen in English and Russian.
=======
- `tools/render_*.py` — the original design previews in Python. The idle scenes were ported from them; keep timings in sync if you change either side. README GIFs of the firmware come from the simulator: `python tools/sim/render_docs.py` renders every screen in both themes into `docs/firmware/claude/`, `docs/firmware/codex/` and `docs/firmware/`. Add new screens to its `JOBS` table and to the gallery in both READMEs.
- `host/scenes.py` — which idle scenes each theme offers and how the user picks one (`AGENT_STATUS_IDLE_CLAUDE`, `AGENT_STATUS_IDLE_CODEX`).
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
- `hooks/` plus the plugin manifests — wire Claude Code (`hooks/hooks.json`) and Codex (`hooks/codex-hooks.json`) events to `hooks/forward.py`.

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
<<<<<<< HEAD
- `lang`: `en` | `ru` — language of the board's own labels
=======
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046

Every field is optional; the board keeps the last value. Do not change this format without updating `host/sessions.py`, `firmware/main/protocol.c`, the simulator scenarios and the Protocol section of both READMEs.

## Commands

```bash
# Python: syntax check and adapter smoke test (no hardware needed)
python -m py_compile hooks/forward.py host/*.py host/adapters/*.py tools/*.py tools/sim/*.py
python tests/test_adapters.py

# Validate manifests
python -m json.tool .claude-plugin/plugin.json > /dev/null
python -m json.tool .codex-plugin/plugin.json > /dev/null

# Screen code in the simulator (cmake + C compiler, no ESP-IDF)
python tools/sim/render.py tools/sim/scenarios/basic.txt build/basic.gif

# Firmware (requires ESP-IDF 5.1+)
cd firmware && idf.py set-target esp32s3 && idf.py build
```

## Rules

- `hooks/forward.py` must always exit 0 and must never block the agent for long: keep network timeouts short. The only thing it may print to stdout is the PermissionRequest decision when `AGENT_STATUS_BUTTON_APPROVE=1` and the button was pressed; the wait is capped by `AGENT_STATUS_APPROVE_WAIT` (≤120 s, below the hook timeout of 130 s in `hooks/hooks.json`).
- Board → host lines are `{"button":"approve"|"deny"}` and `{"button":"scene_next","scene":...}`, handled in `handle_board_line()` in `host/daemon.py`. Approvals live in `host/approvals.py`.
- Battery, Wi-Fi and mute indicators (`ui_icons.c`) must stay visible on every screen. A new full-screen object on `lv_layer_top()` goes below them: call `ui_icons_to_front()` after creating it. Position objects by constants, not `lv_obj_get_width()` before the first layout — it returns 0 then.
- Button and buzzer pins are Kconfig options (`firmware/main/Kconfig.projbuild`), not hard-coded.
- `hardware/case/case.py` generates the STL files; edit `PARAMS` there and keep `case.scad` in sync. Run it and check that every part reports watertight.
<<<<<<< HEAD
- Python on the host side: standard library only, except `pyserial` in the daemon (imported lazily, so `daemon.py config` works without it). `hooks/forward.py` imports `host/config.py` on every event — keep it light.
- Never hard-code a user-facing string: on the board use `tr()` from `ui_i18n.h`, on the host `i18n.t()`, and add both `en` and `ru`. Host log lines are English.
=======
- Python on the host side: standard library only, except `pyserial` in the daemon.
>>>>>>> e5c9d72a9298cb89b6bad1e778c1d4711e7ac046
- Firmware: all LVGL calls go through `ui_lock()`/`ui_unlock()` in `main.c`; LVGL is not thread-safe.
- LVGL 9.2: object fields are private — use accessors (`lv_obj_get_coords`, `dctx_from_event`), not `obj->coords`.
- After changing anything in `firmware/main/ui_*.c`, run the relevant simulator scenario and look at the frames (`--png-at`).
- Keep `README.md` (English) and `README.ru.md` (Russian) in sync when behavior or setup changes.
- Mascots are original characters. Do not add logos or brand characters of Anthropic, OpenAI or anyone else; brand colors are fine.
- Bump `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `.codex-plugin/plugin.json` together.
- Hardware behavior cannot be verified in CI. Say so explicitly instead of claiming firmware changes work.
