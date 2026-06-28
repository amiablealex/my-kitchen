# Phase 16 — Create a recipe from scratch (4b)

Shipped as add-on **0.11.0**. No LLM, no resolver, **no schema change** — every
column already existed from the keystone (Phase 14).

## What shipped
- **Create/edit form** for hand-written recipes (`source='user'`). One template
  (`wizard/recipe_form.html`) + JS (`static/recipe_form.js`) drives both.
  Fields: title, blurb, intro, servings, meal type (`MEAL_TYPES`), repeatable
  prep/cook/tips steps, and catalogue-linked ingredient lines. The ingredient
  picker reuses the **4a shared-panel UX** but is build-then-submit, not the 4a
  per-row AJAX editor.
- **Discoverability (folded into 4b):** user recipes now appear in the Recipes
  list merged by `created_at` with AI generations; the Cook filter works for
  both sources.
- **Favourite any recipe** regardless of source (storage already keyed on
  `recipe_id`; only needed the generation guards).
- **Entry point:** "Create a recipe" button on the Recipes page header.

## Routes (all on `wizard_bp`, `/cook` prefix)
- `GET/POST /recipe/new` — create.
- `GET/POST /recipe/<id>/edit` — edit; **guarded to `source='user'` only** (AI
  recipes bounce back with a flash — their links are edited inline via 4a).
- `POST /recipe/ingredient/add` — create-only catalogue add for the picker,
  returns the new id (distinct from 4a's `add-and-link`, which links an existing
  row). Reuses manage's `_parse_ingredient_form` / `_name_taken`.

## Save shape
`source='user'`, `generation_id=NULL`, `created_by_user_id=current_user`. Writes
**both** the structured `recipe_ingredients` rows (`raw_text` = catalogue name,
server-trusted; `position` = list order) **and** `ingredients_json` (display
parity + keeps the "still written" invariant). Edit = **replace-all** the
ingredient rows (delete-orphan handles removal). Server validation: title
required, servings ≥ 1, ≥ 1 catalogue-linked ingredient, ≥ 1 cook step. Every
ingredient line must be catalogue-linked (off-catalogue → add-and-use first).

## Generation None-guard (the correctness crux — user recipes are the first with
`generation_id` NULL)
- `wizard.recipe` — allergy caveat: skip when `recipe.generation is None`.
- `wizard.choose` — `abort(404)` when no generation (a user recipe has no
  sibling/choice screen).
- `history/favourites.html` — attribution branches: generation → "cooked by",
  else → "created by {author}".
- `history.index` / `history/index.html` — user rows never deref a generation.
- Note: `toggle_favourite` never touched `.generation` — no change needed.

## Cook filter (history)
Per-source, not flattened: AI rows filter on `Generation.created_by_user_id`,
user rows on `Recipe.created_by_user_id` (both carry the same author concept).
Kept per-source so unchosen/failed generations (no recipe rows) stay filterable.

## Learnings
- The 4a link editor is **not** reusable for creation — it edits persisted rows.
  Only the picker *UX* (shared panel, client search, add) transfers; the
  persistence model is different (build-then-submit).
- Index-keyed form fields (`ing-{i}-*`, `prep|cook|tips-{i}-*`) + regex index
  collection server-side handles dynamic add/remove rows cleanly; ascending
  index == on-screen order (no reordering UI), so it doubles as `position`.
- A single `prefill` JSON channel unifies edit pre-population and error
  re-render — one hydration path in the JS for both.

## Inherited by later phases
- **4c (filters/badges):** recipe-type (AI/user/imported) filter + source colour
  badges — deliberately **out** of this phase. The merged list + per-source Cook
  filter are the substrate it builds on.
- **Suggestions (roadmap item 5):** user recipes are now first-class, linked
  recipes in the bank, so the "cookable from stock" join over `recipe_ingredients`
  picks them up for free alongside AI recipes.
- **Web/photo ingestion:** `source='imported'` recipes reuse this exact
  create/edit form as their review/edit UI (the §3.4 plan) — the form is already
  source-agnostic on save.

## Scope extension (shipped 0.12.0) — recipe tags + edit affordance

After the original 4b shipped (0.11.0), the same conversation added recipe-level
meal-type/cuisine tagging and a recipe-page edit entry, plus one migration.

**New column.** `recipes.cuisine` (nullable String) — additive migration chained
onto the keystone head. No backfill (both DBs were fresh); production rebuilt.

**Cuisine constants moved to `models.py`** (so `llm/service.py` can import without
a circular import, same reason as `MEAL_TYPES`): `CUISINES` (real, taggable),
`SURPRISE_ME`, `WIZARD_CUISINES = CUISINES + ["Surprise me"]`, and
`recipe_cuisine_from(value)` (maps a generation's requested cuisine to a recipe
TAG: "Surprise me"/None → None). `wizard/routes.py` now imports these and derives
`CUISINE_MEAL_TYPES` (the cuisine-bearing meal types) for gating.

**AI copy-forward.** `_run_generation_job` sets `cuisine=recipe_cuisine_from(gen.cuisine)`
beside the existing `meal_type=gen.meal_type` — generation stays sealed, this is
post-hoc on the row like the meal_type copy. So "Surprise me"/non-cuisine
generations yield NULL-cuisine recipes; concrete cuisines tag through.

**Both tags optional, gated by hierarchy.** New shared `_normalise_tags(meal_type,
cuisine)` in `wizard/routes.py` is the single gate (validates against
`MEAL_TYPE_NAMES`/`CUISINES`; forces cuisine NULL unless the meal type is set AND
`meal_type_takes_cuisine`). Used by both the form save and the inline editor — so
client gating is cosmetic, server is authoritative (mirrors the wizard step-2
pattern). The create form no longer defaults meal type to Dinner; untagged is
allowed.

**Inline tag editor** (`recipe_set_tags` → `POST /cook/recipe/<id>/tags`;
`recipe_tags.js`). Mirrors the 4a ingredient-link editor: pills + an edit panel,
AJAX save (X-CSRFToken, url_for-injected endpoint). Works on ANY recipe (AI or
user) — tags are shared, not per-user. Returns `cuisine_allowed` so the JS
hides/shows the cuisine pill. Form picker gating reuses the same
`cuisine_meal_types` JSON + a `syncCuisineVisibility()` on meal-type change.

**Edit affordance.** "Edit recipe" button on the recipe page, `source='user'`
only → the existing pre-filled `/cook/recipe/<id>/edit`. `prefill` now carries
`cuisine`; the form has a gated cuisine `<select>` (with a "No cuisine" option)
alongside meal type (now with a "No meal type" option).

**Gotcha recorded.** The tag edit panel uses the `hidden` attribute, but a class
rule with `display:flex` out-specifies `[hidden]`'s UA rule, so the panel stayed
visible. Fix is CSS, not JS: `.recipe-tags-view[hidden], .recipe-tags-edit[hidden]
{ display:none }`. (The form picker avoided this only by never setting `display`.)
Rule of thumb: any element toggled via `.hidden`/`hidden` needs an
attribute-qualified `[hidden]{display:none}` if its base class sets `display`.

**Inherited.** Recipes are now meal-type + cuisine taggable across all sources —
the substrate for the wizard pre-AI suggestions (filter saved recipes by the
wizard's meal-type/cuisine inputs). 4c (recipe-type filter + source badges) still
deferred.
