# Phase 7a — Dockerise & deploy (standalone Pi)

**Status:** ✅ Done. Tested end-to-end on the Pi 4 (dev box), committed.
Scope was pass (a) only — containerise into a clean, portable, persistent image.
HA add-on packaging (pass b) is the next conversation and reuses this image.

## What we built

- **Dockerfile** — `python:3.12-slim`, resolves to arm64 on the Pi. Installs
  `gosu` + `sqlite3` (CLI, for the privilege-drop and for WAL-safe backups),
  pip-installs `requirements.txt`, copies the app, runs as non-root `appuser`.
  Env defaults bake in `FLASK_APP=wsgi:app`, `MY_KITCHEN_DB_PATH=/data/...`.
  `HEALTHCHECK` hits `/healthz` via stdlib `urllib` (slim has no curl).
- **entrypoint.sh** — starts as root only to `chown` the mounted data dir, then
  drops to `appuser` via `gosu`. Runs `flask db upgrade` **once** before workers,
  then `exec`s gunicorn. Warns (non-fatal) if `SECRET_KEY` is unset/the dev default.
- **gunicorn** — `gthread`, 2 workers × 4 threads, `--timeout 120`, logs to
  stdout/stderr. All counts env-tunable (`GUNICORN_WORKERS`/`THREADS`). Threads
  (not processes) soak the 30–60s I/O-bound generation cheaply on limited RAM.
- **.dockerignore** — keeps `.env`, `*.db`/`-wal`/`-shm`, `data/`, `backups/`,
  `eval_runs/`, `docs/`, `.git`, bytecode out of the image (no secrets, no DB).
- **docker-compose.yml** — service + `./data:/data` bind mount + `env_file: .env`
  + port map + `restart: unless-stopped`. No `version:` key (obsolete in v2).
- **.env.example** — documents every var; `SECRET_KEY` flagged must-be-stable;
  `MY_KITCHEN_DB_PATH=/data/my_kitchen.db`.
- **requirements.txt** — added `google-genai` (pinned to the Pi-tested version)
  and `anthropic` (unpinned), so the LLM provider + key are user-configurable.
- **scripts/backup.sh + restore.sh** — WAL-safe. Backup uses SQLite `.backup`
  inside the live container (consistent hot snapshot), prunes to last 14.
  Restore stops the app, snapshots current DB as `pre_restore_*.db`, swaps the
  file, clears stale `-wal`/`-shm`, restarts.
- **DEPLOY.md** — first-run runbook: setup, seed/passwords, day-to-day, update,
  backup/restore, cron, troubleshooting.

## Persistence & first-run

- DB lives at `./data/my_kitchen.db` on the host (bind-mount → `/data`), survives
  `down`/`up` and rebuilds. `/data` maps cleanly onto HA `/data` for pass (b).
- Fresh start: empty volume → `flask db upgrade` builds the **whole** schema from
  the migration chain (no `create_all`). First-run data via `flask seed` +
  `flask set-password` / `create-user`, run with `docker compose exec`.

## Verified on the Pi

Build (clean arm64 wheels, no compile) → migrate-once-then-gunicorn boot →
served on LAN, styled, ProxyFix/static intact → seeded → **real Gemini generation
end-to-end** → favourited → data survived `restart` AND full `down`/`up` (second
boot's migrations a no-op) → backup → mutate → restore rolled it back.

## Learnings worth recording

- **`flask db check` is the convergence gate.** On a fresh empty DB it returned
  "No new upgrade operations detected" — proof that `upgrade` alone reproduces
  the live models exactly, which is what the entrypoint relies on. (The `db
  migrate` fallback errored only because `rm` between commands left an unstamped
  empty DB — a sequencing artefact, not a schema problem.)
- **slim has neither `sqlite3` CLI nor curl.** Both surfaced as needs: `sqlite3`
  added for WAL-safe `.backup`; healthcheck written with stdlib `urllib` instead.
- **WAL mode makes naïve `cp` unsafe** — committed data can sit in `-wal`. Backup
  must use SQLite's online `.backup`; restore must clear stale `-wal`/`-shm` so
  the restored file is authoritative.
- **Root-then-drop entrypoint** (vs a pure `USER` directive) is what makes a
  freshly-mounted volume writable — the pattern that'll carry to HA `/data`.
- **Migrations belong in the entrypoint, once, before workers** — not per worker,
  not in the Dockerfile (no DB/volume at build time).
- Docker wasn't preinstalled on the dev Pi — installed via Docker's official apt
  repo (Debian Bookworm path, arm64).

## Deliberately deferred / out of scope

- HA add-on scaffolding (`config.yaml`/`build.yaml`, `ingress: true`, options
  schema, `/data` mapping, install) → next conversation.
- Multi-arch image publishing; async generation (Phase 6); history-suggestions.
- PWA/service-worker still needs HTTPS — comes alive via HA ingress in pass (b).

## Set up for pass (b)

Image is portable and config-driven (every knob is env), data is on a mountable
dir, binds `0.0.0.0`, ProxyFix/`url_for` ingress-safety intact — so the add-on
wrapper injects options as env, maps `/data`, and reuses this image as-is.
