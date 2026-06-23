#!/bin/sh
set -e

DB_PATH="${MY_KITCHEN_DB_PATH:-/data/my_kitchen.db}"
DATA_DIR=$(dirname "$DB_PATH")
mkdir -p "$DATA_DIR"

# --- Home Assistant add-on bootstrap (no-op for standalone compose) --------
# HA writes the user's settings to /data/options.json. Translate them into the
# env vars the app consumes, and generate+persist a stable SECRET_KEY. Runs as
# root (pre-drop) so it can write /data/secret_key before we chown.
if [ -f /data/options.json ]; then
    echo "Home Assistant add-on detected — applying options.json..."
    ENV_EXPORTS="$(python3 /app/scripts/ha_bootstrap.py)" || { echo "ha_bootstrap failed"; exit 1; }
    eval "$ENV_EXPORTS"
fi
# --------------------------------------------------------------------------

# Make the freshly-mounted volume (incl. any secret_key just written) owned by
# the unprivileged app user before we drop to it.
chown -R appuser:appuser "$DATA_DIR"

if [ -z "${SECRET_KEY}" ] || [ "${SECRET_KEY}" = "dev-only-change-me" ]; then
    echo "WARNING: SECRET_KEY is unset or the insecure dev default."
    echo "         Set a stable SECRET_KEY or logins/CSRF will break on restart."
fi

echo "Running database migrations..."
gosu appuser flask db upgrade

# First-run seed (HA path sets AUTO_SEED=1). Idempotent: seeds catalogue + one
# user with a generated password ONLY when there are no users yet, and logs the
# temp credentials. Never re-fires once a user exists, so it's safe every boot.
if [ "${AUTO_SEED}" = "1" ]; then
    gosu appuser flask first-run-seed
fi

echo "Starting gunicorn on 0.0.0.0:${MY_KITCHEN_PORT:-8000}..."
exec gosu appuser gunicorn wsgi:app \
    --bind "0.0.0.0:${MY_KITCHEN_PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
