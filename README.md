# My Kitchen (Home Assistant app)

[![Add repository to your Home Assistant instance.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Famiablealex%2Fmy-kitchen)

A self-hosted, LLM-powered recipe brain for one household. Keep a shared stock list of
what's in your kitchen, then walk a quick wizard to resurface a saved recipe you can cook right now, or
turn the brief into two distinctly different recipes to choose from, that you can cook right now, from your
live stock list.

Runs as a Home Assistant add-on (ingress + sidebar panel, remote access via
Nabu Casa), or standalone on any machine with Python. Built for phones and used
daily in the kitchen.

Flask + SQLite, generation via a swappable
provider adapter (mock / Anthropic / Gemini).

Runs on a Raspberry Pi on the local network.

[my-kitchen.io](https://my-kitchen.io)

<img width="1524" height="661" alt="4-screens" src="https://github.com/user-attachments/assets/766c8dc3-0f73-442a-a270-fab390a4fb3a" />

## What it does

- **Simple inventory tracking** A simple in/out toggle for what you've got, grouped
  and colour-coded by section, with quick notes ("needs using").
- **What's cookable right now** Surfaces your saved recipes you
  can make *right now* with what's in stock.
- **Real ingredient catalogue.** Every recipe links to a structured catalogue
  via a deterministic resolver.
- **Your household.** Multi-user with per-person favourites and dietary tags
  (allergies are hard exclusions; preferences are soft steers).
- **Hand-written recipes too.** Add your own, tag them, favourite them — they
  live alongside the AI ones and show up in the Let's Cook wizard.
- **Swappable LLM.** Gemini or Anthropic in production; a `mock` provider runs
  the whole flow offline with no key.

## Install (Home Assistant add-on)

1. Click the button above, or in Home Assistant go to **Settings → Apps →
   Install App → ⋮ → Repositories** and add
   `https://github.com/amiablealex/my-kitchen`.
2. Find **My Kitchen** in the store and **Install** (the first build takes a few
   minutes on a Pi — it builds the image locally).
3. On the **Configuration** tab, set `llm_provider` and the matching API key
   (or choose `mock` to try it keyless). **Save**, then **Start**.
4. Open the **Log** tab — on first run it prints a one-time login user and
   temporary password.
5. Open **My Kitchen** from the sidebar and log in. Change the password in-app.

> Add-ons require Home Assistant **OS** or **Supervised** (not Container/Core).


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

SQLite, with schema managed by Alembic (Flask-Migrate). The DB file is gitignored (per-machine).

Fresh machine (empty DB):

    flask db upgrade    # build the schema from migrations
    flask seed          # add the placeholder catalogue

Existing DB being put under migrations for the first time (one-off):

    flask db stamp head # records the current schema as already-applied; touches no data

After pulling a change that includes a new migration:

    flask db upgrade

`flask shell` opens a shell with `db` and all models pre-imported.

## Run standalone / develop

Not on Home Assistant? It's a normal Flask app. See **[DEPLOY.md](DEPLOY.md)**
for Docker and bare-metal, or for a quick dev loop:

\`\`\`bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit
flask db upgrade && flask seed  # schema + starter catalogue
python run.py
\`\`\`

## Tech

Flask (app-factory + blueprints), SQLAlchemy + SQLite + Alembic, gunicorn,
server-rendered Jinja with a plain-CSS design system (no build step). Generation
runs on a background thread and streams in via a polling page.

## Contributing & issues

Bugs and ideas welcome via [Issues](https://github.com/amiablealex/my-kitchen/issues).
This is a personal household project shared in the hope it's useful. No
guarantees, but PRs and questions are read.

## License

[MIT](LICENSE) © amiablealex
