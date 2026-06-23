# Phase 7b — Home Assistant add-on packaging

**Status:** ✅ Done. Built incrementally and tested live in HA on a Pi 5
(separate from the dev Pi). Reuses the 7a image recipe — wrapped, not rebuilt.

## What we built

- **Add-on repository** — `repository.yaml` at repo root + the add-on in
  `addon/` (`config.yaml`, `Dockerfile`, `DOCS.md`/`README.md`/`CHANGELOG.md`,
  `icon.png`/`logo.png` reusing the rainbow-pot placeholder). Installed by adding
  the GitHub repo to the HA add-on store; built locally by HA (no registry).
- **Build pattern** — the add-on `Dockerfile` mirrors the 7a recipe but **clones
  `main` at build** (the cloned `entrypoint.sh` is reused as-is). `BUILD_VERSION`
  is referenced in the clone `RUN` to bust Docker's layer cache, so a `config.yaml`
  version bump re-fetches `main`. Build context is the add-on subfolder, so
  `COPY`-ing the repo-root app is impossible — hence the clone.
- **Ingress path handling** — a small WSGI middleware promotes the
  `X-Ingress-Path` header to `SCRIPT_NAME`, so every `url_for` link + `/static`
  asset resolves under the dynamic ingress sub-path. Applied *inside* ProxyFix
  (final say on `SCRIPT_NAME`); no header (direct LAN / standalone) → serves at
  root unchanged.
- **Options → env shim** — `scripts/ha_bootstrap.py` reads `/data/options.json`,
  maps each option onto the exact env var the app already consumes, and emits
  shell `export`s for `entrypoint.sh` to eval. Gated on `/data/options.json`
  existing, so it's a no-op for the standalone compose deploy.
- **SECRET_KEY** — generated once and persisted to `/data/secret_key`, reused on
  every start (stable across restarts/updates; never asked of the user).
- **First-run auto-seed** — `flask first-run-seed` (idempotent: only when zero
  users) seeds the starter catalogue + one user with a generated password printed
  once to the add-on log. Shared seed logic lifted into `my_kitchen/seed_data.py`
  (used by both `seed` and `first-run-seed`).
- **Persistence** — SQLite DB on HA's automatic `/data`; root-then-drop chown
  handles writability; captured by HA backups.

## Verified live (over HTTPS ingress + Nabu Casa cloud)

Install → configure options → start → ingress sub-path serves fully styled
(links + static under the ingress prefix) → real Gemini generation end-to-end →
data + users + login session survived a version-bump rebuild (`flask db upgrade`
a clean no-op, persisted `SECRET_KEY` held). Non-admin household user reaches the
app from the sidebar, including remotely via the cloud URL.

## Learnings worth recording

- **`build.yaml` is gone (Supervisor 2026.04.0).** Set the base image with an
  explicit `FROM` and add `io.hass.*` `LABEL`s manually; no `BUILD_FROM`/
  `ARG BUILD_FROM`. Our `python:3.12-slim` base is now the normal path.
- **`WTF_CSRF_SSL_STRICT = False`** — login over the Nabu Casa cloud relay failed
  with "form expired". Flask-WTF's strict Referer-vs-Host check (HTTPS only)
  can't match the public cloud host behind ingress. Token-based CSRF stays on;
  this only drops a redundant layer (the app already sits behind HA auth).
- **`panel_admin: false` needs a full Core restart to re-register.** The flag
  makes the sidebar panel visible to non-admins, but a changed panel attribute
  is sticky in Core's frontend panel registry — an add-on update isn't enough;
  restart Home Assistant Core, then have the user fully reopen the companion app
  (client-side caches the panel list). **Any future panel change = Core restart.**
- **Store-cache lag on add-on updates.** A pushed version bump can show
  "update available" while the Update modal still compares stale versions (and
  Rebuild refuses, "versions differ"). `ha supervisor reload` (or just waiting a
  minute) re-ingests it.
- **Manifest was already ingress-safe** — relative `../` `start_url`/`scope`
  resolve correctly under the sub-path; no change needed.
- **GitHub-repo add-ons are hash-prefixed**, not `local_` — real container/slug
  is `addon_<hash>_my_kitchen` (find via `docker ps` / `ha addons`).

## Deliberately deferred

- **PWA own-identity** — over the cloud URL the browser installs HA itself
  (HA's origin/manifest wins). A standalone HTTPS origin (own TLS / Tailscale)
  + the deferred root-scoped SW would give My Kitchen its own installable app +
  true offline. Manifest install + secure-context SW groundwork is the 7b win.
- **HA backup restore-test** — backups not yet configured on the HA instance;
  `/data` capture is automatic once they are.
- **Async generation (Phase 6)** — unchanged main technical debt; now that
  deployment is real, rising generation times are the trigger to bring it forward.
- History-suggestions enhancement; bespoke add-on icon/mascot.
