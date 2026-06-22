# My Kitchen — Deployment (Docker, standalone Pi)

Self-hosted recipe generator, containerised. This is the standalone Docker
setup for a Raspberry Pi on the LAN. (Home Assistant add-on packaging is
separate — it reuses this same image.)

## Requirements

- Raspberry Pi (64-bit Raspberry Pi OS / Debian Bookworm), Pi 4/5.
- Docker Engine + Compose plugin (`docker --version`, `docker compose version`).
- A Gemini API key (or Anthropic), unless running the `mock` provider.

## First-time setup

1. **Clone and enter the repo:**
```sh
   git clone <your-repo-url> my-kitchen
   cd my-kitchen
```

2. **Create your environment file:**
```sh
   cp .env.example .env
```
   Then edit `.env`:
   - Generate a **stable** secret (do this ONCE and never change it, or all
     logins/CSRF break on restart):
```sh
     python -c "import secrets; print(secrets.token_hex(32))"
```
     Paste the result as `SECRET_KEY=`.
   - Set `LLM_PROVIDER` (`gemini` | `anthropic` | `mock`) and the matching
     `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`.
   - Leave the rest at their defaults unless you have a reason to change them.

3. **Build and start:**
```sh
   docker compose up -d --build
```
   On first start the entrypoint runs `flask db upgrade`, which builds the full
   schema on the empty `./data` volume, then starts gunicorn.

4. **Seed initial data and set a password** (the fresh DB has no users yet):
```sh
   docker compose exec my-kitchen flask seed
   docker compose exec my-kitchen flask set-password "Home Cook"
```
   Add more household members any time:
```sh
   docker compose exec my-kitchen flask create-user "Alex"
   docker compose exec my-kitchen flask set-password "Alex"
```

5. **Open the app:** `http://<pi-lan-ip>:8000/` and log in.

## Day-to-day

```sh
docker compose up -d          # start (after a reboot, restart: unless-stopped handles it)
docker compose logs -f        # follow logs
docker compose ps             # status
docker compose down           # stop and remove the container (data is kept in ./data)
docker compose up -d --build  # rebuild + restart after pulling new code
```

### Updating to new code
```sh
git pull
docker compose up -d --build
```
The entrypoint applies any new migrations once before workers start. `create_all`
and the migration chain are kept converged, so a fresh DB and an upgraded DB end
up identical.

## Data & persistence

- The SQLite database lives at `./data/my_kitchen.db` on the host (bind-mounted
  to `/data` in the container). It survives `down`/`up` and rebuilds.
- WAL mode is on, so you'll also see `-wal` and `-shm` sidecar files. Normal.

## Backups

Take a backup (safe to run while the app is live — WAL-consistent):
```sh
./scripts/backup.sh
```
Writes a timestamped copy to `./backups/`, keeping the last 14 (override with
`BACKUP_KEEP`). To automate daily at 02:00, add to the Pi's crontab
(`crontab -e`), using an absolute path:
```
0 2 * * * cd /home/pi/my-kitchen && ./scripts/backup.sh >> ./backups/backup.log 2>&1
```

## Restore

```sh
./scripts/restore.sh ./backups/my_kitchen_YYYYmmdd_HHMMSS.db
```
Stops the app, snapshots the current DB as `pre_restore_*.db` (so a mistaken
restore is itself recoverable), swaps in the backup, clears stale WAL/SHM, and
restarts.

## Troubleshooting

- **Everyone logged out / forms rejected after a restart:** `SECRET_KEY` changed
  or wasn't set. Set a stable one in `.env`.
- **Generation fails immediately:** check `GEMINI_API_KEY` is set and
  `LLM_PROVIDER=gemini` in `.env`; `docker compose logs` shows the provider error.
- **`exec` says service not running:** `docker compose ps` / `logs` — usually a
  config error surfaced at boot.
- **Health:** `curl http://localhost:8000/healthz` → `{"status":"ok"}`.
