"""
Настройки Agent Status Bar.

Порядок (каждый следующий важнее):
  1. значения по умолчанию;
  2. файл ~/.agent-status/config.toml (путь можно сменить: AGENT_STATUS_CONFIG);
  3. переменные окружения AGENT_STATUS_*.

    python host/daemon.py config          # показать итоговые настройки и путь к файлу
    python host/daemon.py config --init   # создать файл с комментариями

Рядом с конфигом лежит state.json — то, что демон запоминает сам (сцена, выбранная кнопкой).
Только стандартная библиотека: хук импортирует этот модуль на каждом событии.
"""
import json
import os

DEFAULTS = {
    "language": "auto",        # en | ru | auto (по системной локали)
    "serial_port": "",         # пусто — искать плату по USB
    "http_port": 8765,
    "autostart": True,         # хук сам поднимает демон
    "idle_claude": "robot",    # robot | cursor
    "idle_codex": "cursor",    # cursor | typist
    "button_approve": False,   # решать запросы разрешения кнопкой (Claude Code)
    "approve_wait": 20,        # сколько секунд хук ждёт кнопку, 1..120
}

ENV = {
    "language": "AGENT_STATUS_LANG",
    "serial_port": "AGENT_STATUS_SERIAL",
    "http_port": "AGENT_STATUS_PORT",
    "autostart": "AGENT_STATUS_AUTOSTART",
    "idle_claude": "AGENT_STATUS_IDLE_CLAUDE",
    "idle_codex": "AGENT_STATUS_IDLE_CODEX",
    "button_approve": "AGENT_STATUS_BUTTON_APPROVE",
    "approve_wait": "AGENT_STATUS_APPROVE_WAIT",
}

TEMPLATE = """\
# Agent Status Bar — settings. Environment variables AGENT_STATUS_* override this file.

# Screen language: "en", "ru" or "auto" (from the system locale)
language = "{language}"

# Serial port of the board; empty — find it automatically (e.g. "COM5", "/dev/cu.usbmodem1101")
serial_port = "{serial_port}"

# Local HTTP port the hooks talk to
http_port = {http_port}

# Start the daemon from the hook when it is not running
autostart = {autostart}

# Idle scene per theme: Claude — "robot" or "cursor"; Codex — "cursor" or "typist".
# A double press on the board's button switches it and the choice is remembered in state.json.
idle_claude = "{idle_claude}"
idle_codex = "{idle_codex}"

# Answer Claude Code permission requests with the board's button (hold — allow, tap — deny)
button_approve = {button_approve}
# How long the hook waits for the button before Claude Code asks as usual, seconds (1..120)
approve_wait = {approve_wait}
"""


def home(env=None):
    env = os.environ if env is None else env
    return env.get("AGENT_STATUS_HOME") or os.path.join(os.path.expanduser("~"), ".agent-status")


def config_path(env=None):
    env = os.environ if env is None else env
    return env.get("AGENT_STATUS_CONFIG") or os.path.join(home(env), "config.toml")


def _parse_value(raw):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def _parse_toml(text):
    """tomllib (Python 3.11+), а на старом Python — простой разбор key = value."""
    try:
        import tomllib
    except ImportError:
        return _parse_flat(text)
    return tomllib.loads(text)


def _parse_flat(text):
    """Плоский TOML: key = value, комментарии #. Хватает для нашего файла."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("[") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if "#" in val and not val.strip().startswith(('"', "'")):
            val = val.split("#", 1)[0]
        out[key.strip()] = _parse_value(val)
    return out


def _coerce(key, value):
    default = DEFAULTS[key]
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(default, int):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
    return str(value).strip()


def system_language(env=None):
    env = os.environ if env is None else env
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if env.get(var):
            return "ru" if env[var].lower().startswith("ru") else "en"
    try:
        import locale
        loc = locale.getlocale()[0] or ""
    except (ValueError, ImportError):
        loc = ""
    return "ru" if loc.lower().startswith("ru") else "en"


def load(env=None, read_file=True):
    """Итоговые настройки: умолчания < файл < окружение. language всегда en или ru."""
    env = os.environ if env is None else env
    cfg = dict(DEFAULTS)
    errors = []
    if read_file:
        path = config_path(env)
        try:
            with open(path, encoding="utf-8") as f:
                data = _parse_toml(f.read())
            for k, v in data.items():
                if k in DEFAULTS:
                    cfg[k] = _coerce(k, v)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            errors.append(f"{path}: {e}")
    for k, var in ENV.items():
        if env.get(var) not in (None, ""):
            cfg[k] = _coerce(k, env[var])
    lang = str(cfg["language"]).lower()
    cfg["language"] = lang if lang in ("en", "ru") else system_language(env)
    cfg["approve_wait"] = max(1, min(120, cfg["approve_wait"]))
    cfg["_errors"] = errors
    return cfg


def init_file(env=None):
    """Создать файл настроек с комментариями. Возвращает (путь, создан ли)."""
    path = config_path(env)
    if os.path.exists(path):
        return path, False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    vals = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in DEFAULTS.items()}
    with open(path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(**vals))
    return path, True


# ---------- то, что демон запоминает сам ----------

def state_path(env=None):
    return os.path.join(home(env), "state.json")


def load_state(env=None):
    try:
        with open(state_path(env), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(data, env=None):
    path = state_path(env)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass
