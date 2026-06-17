# My Kitchen

Personal, self-hosted recipe generator for one household. Walk a short wizard
(stock → ingredients → cuisine → time → servings), get two LLM-generated recipes,
pick one, and it's saved to history. Flask + SQLite, generation via a swappable
provider adapter (mock / Anthropic / Gemini).

Runs on a Raspberry Pi on the local network.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit (see below)
flask seed                    # create tables + placeholder ingredients
python run.py                 # dev server
```

Open `http://<pi-ip>:<port>/`.

## Configuration (.env)

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing | dev placeholder — set this |
| `MY_KITCHEN_PORT` | Listen port | 8000 |
| `MY_KITCHEN_HOST` | Bind address | 0.0.0.0 |
| `MY_KITCHEN_DB_PATH` | SQLite file location | `my_kitchen.db` in project root |
| `LLM_PROVIDER` | `mock`, `anthropic`, or `gemini` | mock |
| `LLM_MODEL` | Override the provider's default model | provider default |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | API key for the chosen provider | — |

`mock` needs no key or SDK — use it to test the whole flow offline. For a live
provider, install its SDK (`pip install anthropic` or `pip install google-genai`),
set `LLM_PROVIDER` and the matching key in `.env`, and restart.

## Database

SQLite, created and seeded by `flask seed`. The DB file is gitignored (per-machine).
`flask seed --reset` drops everything and reseeds — also needed if you add a model
column, since there are no migrations yet.

`flask shell` opens a shell with `db` and all models pre-imported.

## Running under gunicorn

```bash
gunicorn --bind 0.0.0.0:<port> --workers 2 --timeout 120 wsgi:app
```

`--timeout 120` is required: LLM calls take 15–60s+ and gunicorn's default 30s
timeout will kill the worker mid-generation. (Dev server uses `MY_KITCHEN_PORT`;
gunicorn takes the port from `--bind`.)

## Scope

This is the MVP ("prove the loop"): single user, no auth, deliberately unstyled.
Dietary tags, accounts, favourites, equipment, theming, and Docker are later phases.
See the design spec for the full roadmap.
