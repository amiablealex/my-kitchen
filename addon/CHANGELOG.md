# Changelog

## 0.7.0
- Initial Home Assistant add-on packaging (pass 7b).
- Reuses the standalone container recipe; app fetched from `main` at build.
- Add-on options → env (LLM provider/model/key, temperature, max-tokens,
  recent-titles N, timezone, gunicorn sizing).
- SECRET_KEY generated once and persisted to /data (stable across restarts).
- First-run auto-seed: starter catalogue + one user with a generated password
  printed to the add-on log.
- SQLite DB persists in HA's /data (captured by HA backups).
