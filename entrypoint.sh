#!/bin/sh
set -e

DB_PATH="${MY_KITCHEN_DB_PATH:-/data/my_kitchen.db}"
DATA_DIR=$(dirname "$DB_PATH")

# Start as root only to make a freshly-mounted volume writable by the app user
# (compose bind mount now, HA /data later), then drop privileges for everything.
mkdir -p "$DATA_DIR"
chown -R appuser:appuser "$DATA_DIR"

# Non-fatal warning: a stable SECRET_KEY is load-bearing — sessions and CSRF
# tokens break across restarts without one.
if [ -z "${SECRET_KEY}" ] || [ "${SECRET_KEY}" = "dev-only-change-me" ]; then
    echo "WARNING: SECRET_KEY is unset or the insecure dev default."
    echo "         Set a stable SECRET_KEY or logins/CSRF will break on restart."
fi

# Migrations run ONCE, before any workers start. Fresh volume -> builds the whole
# schema from baseline; existing volume -> applies pending upgrades; up-to-date -> no-op.
echo "Running database migrations..."
gosu appuser flask db upgrade

# I/O-bound generation -> gthread soaks the 30-60s waits cheaply. Modest counts
# keep memory low on a 1GB Pi. Everything env-tunable.
echo "Starting gunicorn on 0.0.0.0:${MY_KITCHEN_PORT:-8000}..."
exec gosu appuser gunicorn wsgi:app \
    --bind "0.0.0.0:${MY_KITCHEN_PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
