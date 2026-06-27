# Phase 14 — Keystone 3b: the migration + wiring the resolver in (summary)

**Status: shipped to production.** This is the keystone's first production release.
`keystone` was merged to `main`; the add-on was bumped to **0.10.0** and production
rebuilt from scratch on the Pi 5. Ingredients are now a first-class, joinable
table, and every newly generated recipe links its ingredients to the catalogue.
Invisible phase — no recipe-page UI change; validated by a match-rate report, not
a visible feature.

## What shipped

**The migration** (`1aa0511c032b`, revises `f3c9a72b4e10`, one additive revision,
`render_as_batch`):
- New **`recipe_ingredients`** table: `{id, recipe_id (NOT NULL FK), ingredient_id
  (NULLABLE FK), raw_text, amount, unit, to_buy, position}`. `raw_text` preserves
  the AI's ingredient string for display; null `ingredient_id` = unmatched. `amount`
  and `unit` are **TEXT** — the model emits amounts verbatim (`"a splash"`, `"½"`,
  `2`), so a numeric column would reject/lose them.
- **`recipes`** gains `source` (NOT NULL, `'ai'` this phase), `meal_type` (nullable,
  copied forward from the generation), `created_by_user_id` (nullable FK, the
  author), and `generation_id` made **nullable** (user/imported recipes later have
  none). `Recipe.ingredients` relationship: `order_by position`, `delete-orphan`.
- `source` used the reusable add-NOT-NULL-on-a-populated-table pattern (add with a
  temporary `server_default='ai'`, then drop it) — verified backfilling real rows
  to `'ai'` and leaving the steady-state column default-free. Downgrade is
  reversible (the FK drops with its column in the SQLite batch rebuild).

**The wiring** (`_run_generation_job`, `llm/service.py`): strictly post-hoc, after
the `Recipe` rows are built and inside the **same single commit** as the recipes +
`status="done"`. The index is built **once per generation**
(`build_index(load_catalogue(), ALIASES)`); each ingredient's `item` string is
resolved via `resolve_with_index` and written as a `recipe_ingredients` row
(amount/unit/to_buy/position verbatim). A poll on the other gunicorn worker never
sees a half-linked recipe. `ingredients_json` is untouched and remains the display
source. **Generation stayed sealed** — prompt / brief / `build_user_prompt` / retry
loop byte-identical (verified by diff).

**`flask resolve-report`** — 3b's validation in place of UI. Reports match rate
split into REQUIRED (`to_buy=False`, headline) vs EXTRAS (`to_buy=True`,
informational), per-method counts (re-resolved, since method isn't stored), the
FUZZY links for eyeballing, and distinct unmatched `raw_text` (primary =
`to_buy=False` catalogue-gap candidates; secondary = `to_buy=True`).

## Real-output validation (8 generations, 60 ingredient rows)

- REQUIRED **47/47 = 100%**; EXTRAS 12/13 = 92.3%; **OVERALL 59/60 = 98.3%**.
- Method mix: exact=54, **alias=0**, fuzzy=5 (all score 100, all correct),
  unmatched=1.
- Only unmatched: **"White miso paste"** (a `to_buy` extra) — niche, intentionally
  left off-catalogue; degrades gracefully, a user can add it themselves.
- Golden set (`resolve-eval`) held at **28/28, 0 false links, 6/6 traps** throughout
  (no catalogue/alias change made this phase).

## Learnings

- **Aliases don't fire on AI output** (alias=0 across every run). Gemini emits
  canonical-ish names that exact-match or fuzzy-match as descriptor supersets, so
  the alias map is insurance for **web ingestion** (later), not for AI. Confirms
  the 3a rationale that a resolver strong enough for web makes AI hint-routes
  redundant.
- **Fuzzy via `token_set_ratio` scores a descriptor superset at 100** (e.g. "Ground
  cinnamon"→Cinnamon, "Maris Piper or King Edward potatoes"→Potatoes) — benign.
  Sub-100 fuzzy is where a false link would hide; none appeared.
- **`amount` must be text** — see above.
- **Golden set is 28 cases** (16 positives + 6 negatives + 6 traps), not the 38
  some earlier notes cited. Record the real number.
- **CLI decorator-order gotcha**: a stray `@click.option` above `def resolve_report`
  made click pass `threshold` to a no-arg callback. Keep each command's option
  decorators with their own `def`.

## Production rollout

From-scratch rebuild (decided — no catalogue merge): cleared the add-on DB so the
entrypoint ran `flask db upgrade` base→head on an empty DB + `first-run-seed`,
rebuilding the **173-item catalogue** and a fresh user (password to the add-on
log). Verified clean on the Pi 5. **Operational note:** a plain HA update does an
*in-place* additive migration that **keeps the old catalogue** — the deliberate
DB-clear is what makes it the intended rebuild. `rapidfuzz` was pinned (was
`>=3.0`) so the tuned threshold is reproducible in the prod image. Data loss
(history/favourites/users) was accepted up front.

## What the next phase (user-created recipes, 3c) inherits

`recipe_ingredients` is the **authoritative structured source** — the create/edit
form makes it editable and doubles as the ingestion review UI. `recipes.source`/
`meal_type`/`created_by_user_id` and the nullable `generation_id` are already in
place; user-created recipes set `source="user"` and **bypass the resolver**
(catalogue-picked → pre-linked). The resolver call pattern (build index once,
`resolve_with_index` per item) is ready for the ingestion sources that do need it.

## Project-tracking notes

- Add-on at **0.10.0**, `CHANGELOG.md` updated; `keystone` merged to `main`.
- **Living docs still to mark keystone-shipped** (next conversation): `recipe-app-spec.md`
  §8 (a Keystone 3b "done" entry) and `production-roadmap.md` §5 item 3.
- Still deferred (unchanged): the freetext→link display + interactive editor +
  add-to-catalogue (3c); `recipe_ratings`; configurable `meal_type`/`cuisine` DB
  lists; the suggestions query/UI. Stock stays a binary toggle; the generation
  prompt stays sealed.

2026-06-27
