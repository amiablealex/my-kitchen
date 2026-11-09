# My Kitchen (Home Assistant app)

[![Add repository to your Home Assistant instance.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Famiablealex%2Fmy-kitchen)

[my-kitchen.io](https://my-kitchen.io)

A self-hosted, LLM-powered recipe brain for one household. Keep a shared list of
what's in your kitchen, then walk a quick wizard to resurface a saved recipe you
can cook right now — or turn the same brief into two distinctly different new
recipes to choose from.

Runs as a Home Assistant app (ingress + sidebar panel, remote access via
Nabu Casa), or standalone on any machine with Python. Built for phones and used
daily in the kitchen.

Flask + SQLite, generation via a swappable provider adapter (mock / Anthropic /
Gemini). Runs happily on a Raspberry Pi on the local network.

<img width="1524" height="661" alt="4-screens" src="https://github.com/user-attachments/assets/766c8dc3-0f73-442a-a270-fab390a4fb3a" />

## What it does

- **Stock, not inventory.** A plain in/out toggle for what you've got, grouped
  and colour-coded by section, with quick notes ("needs using"). No quantities,
  no decrementing, no alerts — a list you'll actually keep up to date.
- **What's cookable right now.** Surfaces the saved recipes you can make *right
  now* from what's in stock, before offering to generate anything.
- **Real ingredient catalogue.** Every recipe line links to a structured
  catalogue via a deterministic resolver — and you can correct any link by hand.
- **Your household.** Multi-user, with per-person favourites and dietary tags in
  three kinds: **allergies** (never used, overrides everything), **dislikes**
  (kept out of the whole recipe, but an ingredient you pick still wins) and
  **diets** (a steer across the recipe).
- **Hand-written recipes too.** Add your own, tag them, favourite them — they
  live alongside the AI ones and show up in the Lets Cook wizard.
- **Notes on what you cooked.** Leave dated, attributed notes on any recipe —
  what you changed, how it went, whether to make it again.
- **Print or share a recipe.** A clean, chrome-free view that prints or saves to
  PDF properly.
- **Swappable LLM.** Gemini or Anthropic in production; a `mock` provider runs
  the whole flow offline with no key.
- **Build around anything.** Pick what to use up — including staples, if you want
  a meal built around the oregano.
- **Find it fast.** Filter your recipes by cuisine, meal type, cook or source —
  or just type a name — all from one search box.

Not yet: importing recipes from a web page or a photo, and a local-model
provider. Both are on the list; see [the roadmap](https://my-kitchen.io/approach).

## Install (Home Assistant app)

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
| `LLM_MODEL` | Override the provider's default model | `gemini-3.5-flash` |
| `LLM_TEMPERATURE` | Generation variety | 0.8 |
| `LLM_MAX_TOKENS` | Output ceiling per generation | 8000 |
| `LIMIT_GENERATIONS_PER_USER_DAY` | Recipe generations each person can start per day | 10 |
| `LIMIT_HOUSEHOLD_CALLS_DAY` | All AI calls across the household per day | 40 |
| `LIMIT_REGENERATES_PER_BRIEF` | "Neither — try again" rounds from one brief | 3 |
| `LIMIT_QUESTIONS_PER_USER_DAY` | @kitchen questions each person can ask per day | 20 |
| `LLM_QA_MODEL` | Model for @kitchen answers | `gemini-3.5-flash-lite` (falls back to `LLM_MODEL`) |
| `APP_TIMEZONE` | Timestamps in history | Europe/London |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | API key for the chosen provider | — |

`mock` needs no key or SDK — use it to test the whole flow offline. For a live
provider, install its SDK (`pip install anthropic` or `pip install google-genai`),
set `LLM_PROVIDER` and the matching key in `.env`, and restart.

## Database

SQLite, with schema managed by Alembic (Flask-Migrate). The DB file is gitignored (per-machine).

Fresh machine (empty DB):

    flask db upgrade    # build the schema from migrations
    flask seed          # add the starter catalogue

Existing DB being put under migrations for the first time (one-off):

    flask db stamp head # records the current schema as already-applied; touches no data

After pulling a change that includes a new migration:

    flask db upgrade

`flask shell` opens a shell with `db` and all models pre-imported.

## Run standalone / develop

Not on Home Assistant? It's a normal Flask app. See **[DEPLOY.md](DEPLOY.md)**
for Docker and bare-metal, or for a quick dev loop:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit
flask db upgrade && flask seed  # schema + starter catalogue
python run.py
```

## Tech

Flask (app-factory + blueprints), SQLAlchemy + SQLite + Alembic, gunicorn,
server-rendered Jinja with a plain-CSS design system (no build step). Generation
runs on a background thread, with the page polling until it's ready.

## Contributing & issues

Bugs and ideas welcome via [Issues](https://github.com/amiablealex/my-kitchen/issues).
This is a personal household project shared in the hope it's useful.

## License

[MIT](LICENSE) © amiablealex
