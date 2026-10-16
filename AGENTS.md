# AGENTS.md

Instructions for AI coding agents (Codex, Claude Code and others) working in this repository.

## What this is

A physical status display for coding-agent tasks. Three parts, deliberately decoupled:

- `firmware/` — ESP-IDF 5.x project in C for the LilyGO T-Display-S3 AMOLED (536×240, RM67162 over QSPI), UI on LVGL 9.2.
- `host/` — Python daemon. Receives hook events over HTTP on `127.0.0.1:8765`, maps them to a screen state through `host/adapters/`, writes JSON lines to the board over USB serial.
- `tools/` — renderers for every GIF in `docs/`: the task screen (`render_task.py --theme claude|codex`) and the idle scenes (`render_idle_robot.py`, `render_idle_cursor.py --theme claude|codex`, `render_idle_typist.py`), sharing `anim_common.py`. They are the design reference: timings, easing, palettes and sprites in firmware must match them. Regenerate the GIFs after changing a renderer.
- `host/scenes.py` — which idle scenes each theme offers and how the user picks one (`AGENT_STATUS_IDLE_CLAUDE`, `AGENT_STATUS_IDLE_CODEX`).
- `hooks/` plus the plugin manifests — wire Claude Code (`hooks/hooks.json`) and Codex (`hooks/codex-hooks.json`) events to `hooks/forward.py`.

The firmware must stay agent-agnostic. Agent-specific logic belongs in `host/adapters/` only.

## The contract between host and firmware

One JSON object per line, UTF-8:

```json
{"state":"work","title":"...","step":"...","done":3,"total":5}
```

- `state`: `idle` | `start` | `work` | `wait` | `done`
- `title`, `step`: optional strings; omitted means "keep the previous text"
- `done`, `total`: integers, `total` is clamped to 1..12 on the board
- `agent`: `claude` | `codex` — theme; `idle`: idle scene name from `host/scenes.py`. Both optional; the current firmware ignores them until themes are ported

Do not change this format without updating both `host/daemon.py` and `firmware/main/main.c`, plus the Protocol section of both READMEs.

## Commands

```bash
# Python: syntax check and adapter smoke test (no hardware needed)
python -m py_compile hooks/forward.py host/daemon.py host/scenes.py host/adapters/*.py tools/*.py
python tests/test_adapters.py

# Validate manifests
python -m json.tool .claude-plugin/plugin.json > /dev/null
python -m json.tool .codex-plugin/plugin.json > /dev/null

# Firmware (requires ESP-IDF 5.1+)
cd firmware && idf.py set-target esp32s3 && idf.py build
```

## Rules

- `hooks/forward.py` must always exit 0 and must never block the agent for long: keep network timeouts short and never print to stdout.
- Python on the host side: standard library only, except `pyserial` in the daemon.
- Firmware: all LVGL calls go through `ui_lock()`/`ui_unlock()` in `main.c`; LVGL is not thread-safe.
- Keep `README.md` (English) and `README.ru.md` (Russian) in sync when behavior or setup changes.
- Mascots are original characters. Do not add logos or brand characters of Anthropic, OpenAI or anyone else; brand colors are fine.
- Bump `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `.codex-plugin/plugin.json` together.
- Hardware behavior cannot be verified in CI. Say so explicitly instead of claiming firmware changes work.
