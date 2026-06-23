#!/usr/bin/env python3
"""Home Assistant add-on bootstrap.

Run by entrypoint.sh (as root, before privileges drop) ONLY when
/data/options.json exists. Maps the user's add-on options onto the exact env
vars the app already consumes (see config.py), and generates+persists a stable
SECRET_KEY under /data so sessions/CSRF survive restarts and updates.

Only `export ...` lines go to stdout (the entrypoint eval's them). All
human-readable messages go to stderr so they show in the add-on log unexecuted.
"""
import json
import os
import secrets
import shlex
import sys
from pathlib import Path

OPTIONS_PATH = Path("/data/options.json")
SECRET_PATH = Path("/data/secret_key")

# options.json key -> env var. Numeric/enum always exported; API keys only when
# non-empty so a blank never clobbers a provider default.
DIRECT_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "llm_model": "LLM_MODEL",
    "llm_temperature": "LLM_TEMPERATURE",
    "llm_max_tokens": "LLM_MAX_TOKENS",
    "llm_recent_titles_n": "LLM_RECENT_TITLES_N",
    "app_timezone": "APP_TIMEZONE",
    "gunicorn_workers": "GUNICORN_WORKERS",
    "gunicorn_threads": "GUNICORN_THREADS",
}
SECRET_MAP = {
    "gemini_api_key": "GEMINI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
}


def emit(var, value):
    print(f"export {var}={shlex.quote(str(value))}")


def log(msg):
    print(f"ha_bootstrap: {msg}", file=sys.stderr)


def main():
    try:
        options = json.loads(OPTIONS_PATH.read_text())
    except FileNotFoundError:
        log(f"{OPTIONS_PATH} not found — exporting nothing")
        options = {}
    except Exception as e:
        log(f"could not parse {OPTIONS_PATH}: {e}")
        sys.exit(1)

    for key, var in DIRECT_MAP.items():
        val = options.get(key)
        if val is not None and val != "":
            emit(var, val)

    for key, var in SECRET_MAP.items():
        if options.get(key):
            emit(var, options[key])

    if SECRET_PATH.exists():
        key = SECRET_PATH.read_text().strip()
        log("reusing persisted SECRET_KEY")
    else:
        key = secrets.token_hex(32)
        SECRET_PATH.write_text(key)
        os.chmod(SECRET_PATH, 0o600)
        log("generated and persisted a new SECRET_KEY")
    emit("SECRET_KEY", key)

    emit("MY_KITCHEN_DB_PATH", "/data/my_kitchen.db")
    emit("AUTO_SEED", "1")


if __name__ == "__main__":
    main()
