# Phase 11 — Meal type

**Status:** ✅ Done. First production-iteration phase (production-roadmap §5.1) —
a deliberately small warm-up. Built CP1→CP3 on the dev Pi, each checkpoint tested
before commit. One additive migration; the tuned generation prompt left sealed.

## What landed

- **`MEAL_TYPES` single source of truth** in `models.py` — eight
  `(name, takes_cuisine)` pairs, `DEFAULT_MEAL_TYPE = "Dinner"`, and a
  `meal_type_takes_cuisine()` helper. Cuisine-bearing: Breakfast, Lunch, Dinner,
  Snack, Side dish. Non-cuisine: Dessert, Baking, Sauce or dressing. Lives in
  `models.py` (beside `SECTION_CHOICES`), **not** `wizard/routes.py`, so
  `llm/service.py` can import the flag without a `wizard → llm.service → wizard`
  circular import.
- **`generations.meal_type`** — nullable `String`, exact parallel to `cuisine`;
  one additive Alembic migration. Existing rows backfill to NULL; new rows store
  the picked type ("Dinner" by default). No `recipes.meal_type` — that belongs to
  the keystone migration (§3.5).
- **Wizard step 2 carries meal type above cuisine** — no fifth step, **four
  step-dots unchanged**. The eight types render as a radio group; a non-cuisine
  pick hides the cuisine block via cosmetic JS (`data-takes-cuisine` rendered
  straight from `MEAL_TYPES`).
- **Server is authoritative on cuisine.** A non-cuisine meal type forces
  `cuisine = None` (stored NULL) regardless of what the hidden cuisine radios
  submit — enforced in the step-2 POST (validated against `MEAL_TYPE_NAMES`) and
  re-asserted defensively in `build_brief`.
- **Brief/prompt wiring (dynamic brief only; `SYSTEM_PROMPT` + `VOICE_AND_WRITING`
  untouched).** A `Meal type: X.` line is emitted **only for non-Dinner** picks
  (Dinner stays silent → identical to today). The cuisine block is now three-case:
  `None` → no line at all; `"Surprise me"` → the open-choice line; otherwise →
  `Cuisine: X.`. `meal_type` threaded through `build_brief` → the `Generation` row.
- **Review screen** shows `Meal type`; the cuisine line shows only when set.
- **One Dessert golden** (`dessert_no_cuisine`: `meal_type="Dessert"`,
  `cuisine=None`) — exercises the meal-type line and the cuisine-omission path in
  a single test.

## Verified

- **8 existing goldens byte-identical** across the prompt change — proven API-free
  with a new `eval/render_prompts.py` that renders goldens + spot-checks for a
  deterministic `diff` (the CP1 gate; kept in-repo as a reusable prompt-regression
  tool). Dinner + Surprise-me is unchanged to the byte.
- **Live wizard walks (native dev server):** Dinner → cuisine shows, default
  "Surprise me"; Dessert → cuisine hidden, review shows no cuisine line.
  `generations` rows confirm `meal_type` stored and `cuisine` NULL for Dessert.
- **`flask eval-recipes`:** 9/9 hard-constraint pass, the dessert reading as a
  genuine cuisine-free dessert.

## Surprises / catches

- **`_mock_payload` None-cuisine crash.** `brief.get("cuisine", "Surprise me").lower()`
  blows up on `cuisine=None`, because `.get`'s default only fires on a *missing* key —
  a present-but-`None` value sails through. Surfaced by the dessert golden; one-line fix
  (`brief.get("cuisine") or "Surprise me"`). The real Gemini path never reads `cuisine`,
  so production was never at risk. General lesson: **`.get(k, default)` does not guard
  against an explicit `None`.**

## Dev environment & database (the real time-sink — record for next phase)

The code work was small; nearly all the friction was the dev DB/loop. Worth internalising
so it doesn't recur:

- **The app's DB hides in `instance/`.** `Flask(__name__)` gives an instance folder at
  `<repo>/instance/`, and Flask-SQLAlchemy resolves a *relative* `sqlite:///` URI **relative
  to that instance folder**, not the cwd or `BASE_DIR`. So a relative
  `MY_KITCHEN_DB_PATH=my_kitchen.db` silently routed the live DB to `instance/my_kitchen.db`,
  while CLI checks built from the config URI string hit a *different* `my_kitchen.db` at the
  repo root. Symptoms: `flask db upgrade` a no-op, `flask seed` "data already present", and a
  `meal_type` column that looked missing — all from inspecting the wrong file.
- **Fixes that stick:** (1) keep `MY_KITCHEN_DB_PATH` **unset** in `.env` for native dev, so
  the app uses the *absolute* repo-root default (no instance relocation, cwd-independent);
  (2) derive the CLI path from **`db.engine.url.database`** (the path the app actually opens),
  never from the `SQLALCHEMY_DATABASE_URI` string:
  `DB=$(python -c "from wsgi import app; from my_kitchen.extensions import db; app.app_context().push(); print(db.engine.url.database)")`.
- **`.env` is shared by native dev *and* the container**, so it can't hold an absolute *host*
  path — the container needs `/data`. Unset is the only clean answer: native → absolute
  repo-root file; container → `/data/my_kitchen.db` from its image `ENV`. The leftover
  `MY_KITCHEN_DB_PATH=/data/...` from the add-on example is exactly what broke native
  `flask db` ("unable to open database file" — `/data` doesn't exist off-container).
- **The dev container runs *baked* code, not your working tree.** The root `Dockerfile` does
  `COPY . .` with no source mount (only `./data:/data`), so edits never reach it until
  `docker compose up -d --build` — `restart` reuses the stale image. Native `python run.py`
  (debug live-reload) is the iteration loop; the container is a **pre-merge smoke test only**,
  on a **separate** `/data` DB (its own first-run user, printed once to the log).
- **Alembic "Target database is not up to date"** blocks autogenerate when the DB's stamp is
  behind head; resolve with `flask db upgrade` (or `flask db stamp <rev>` when the schema
  exists but isn't stamped) before `flask db migrate`.
- **When in doubt, rebuild:** with no data worth keeping, `rm` the DB + `flask db upgrade`
  (base→head — the baseline migration creates every table, same path the container entrypoint
  uses) + `flask seed` + `flask set-password` gives a known-good DB in seconds.

## Doc updates to fold in

- **`recipe-app-spec.md`:** §3 `generations` table — add `meal_type` (text,
  nullable). §4 step 2 — meal type renders above cuisine and gates it; non-cuisine
  types null the cuisine. §5.1/§5.3 — the `Meal type:` line (non-Dinner only) and
  cuisine-`None` suppression in the dynamic brief. §7 — `MEAL_TYPES` is a hardcoded
  constant (DB-backed configurable list deferred to keystone §3.5). §9 — meal type
  is stored on generations only, not recipes, this phase.
- **`production-roadmap.md`:** §5 — mark **1. Meal type** done; `recipes.meal_type`
  + the configurable list remain owned by §3.5 / a later phase.

## Deferred (unchanged)

DB-backed configurable meal-type list + manage-screen CRUD; `recipes.meal_type`,
recipe-bank querying and the suggestions UI (keystone + later phases); async
generation (Phase 6) remains the main technical debt.

2026-06-25
