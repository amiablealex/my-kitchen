# Changelog

## 0.14.0 — Recipe suggestions at "Lets cook"

- The review step now shows saved recipes you can cook **right now** that fit
  your brief, as tappable cards — before offering to generate a new one. A
  deterministic, no-AI query over your linked recipe bank (the keystone payoff).
- Recipes carry a quick/relaxed **time badge**: AI recipes inherit it from the
  cook; user recipes set it on the create/edit form.
- The cuisine step's "Surprise me" now reads **Any** (same behaviour).

## 0.13.0
- Filter the recipes list by source (AI generated / created by hand).
- Recipes are now colour-dotted by origin across the recipes list, favourites,
  and the recipe page — a playful AI pinwheel vs a solid dot for your own.

## 0.12.0
- Recipes now carry meal-type and cuisine tags, editable inline on the recipe
  page (cuisine shown only for cuisine-bearing meal types).
- AI recipes are tagged automatically from the wizard choices; created recipes
  can be tagged on the create/edit form. Both tags are optional.
- Edit your own created recipes from a button on the recipe page.

## 0.11.0
- Recipe pages now show which catalogue ingredient each line is linked to, as a
  small tag beside it — and you can change those links. Tap "Edit links" on the
  Ingredients section to re-link a line to a different ingredient, unlink one,
  or add a brand-new ingredient to your catalogue and link it in one step.
- Works on every recipe, including ones generated before now.
- Your corrections are shared across the household and stick — nothing is
  re-linked automatically behind your back.
- No schema change, and the generation prompt is unchanged.

## 0.10.0
- Groundwork for "what can I cook now?" suggestions: every new recipe's
  ingredients are now linked to the shared ingredient catalogue behind the
  scenes. No visible change — recipe pages and the generation prompt are exactly
  as before.
- Applied as a fresh rebuild onto the new, larger ingredient catalogue: saved
  recipes, favourites and history are cleared, and a new login password is
  generated (shown in the add-on log; set your own with `flask set-password`).
  Back up /data first if you want a copy of the old data.
- Additive schema: a new `recipe_ingredients` table plus provenance fields on
  recipes (source / meal type / author). The generation prompt is unchanged.

## 0.9.0
- Recipe generation now runs in the background. Generating no longer holds the
  page open for the whole wait: the "Lets Cook" flow starts the job and shows a
  "cooking up your recipes…" page that updates itself and jumps to your two
  recipes the moment they're ready.
- Fixes generations timing out when cooking remotely (over the Nabu Casa cloud
  link) — the long wait no longer runs through the proxy in one request.
- A double-tap on "Generate recipes" now resumes the same wait instead of
  starting a second generation.
- If a generation gets stuck or takes too long, the page shows a clear message
  and a way to try again, rather than hanging.
- Additive migration: new nullable `generations.status` column; existing
  recipes and history are unaffected. The generation prompt is unchanged.

## 0.8.0
- Add a "meal type" selector to the Lets Cook wizard (Breakfast, Lunch, Dinner,
  Snack, Side dish, Dessert, Baking, Sauce or dressing). It sits on the cuisine
  step; the non-cuisine types (Dessert/Baking/Sauce or dressing) hide and omit cuisine.
- Meal type is a soft steer in the generation brief (Dinner stays the default and
  changes nothing) and is recorded on each generation.
- Additive migration: new nullable `generations.meal_type` column; existing rows unaffected.

## 0.7.4
- dummy version bump to test if data persists

## 0.7.3
- sidebar no longer requires user to be admin

## 0.7.2 
- Csrf fix

## 0.7.1
- Ingress and path handling

## 0.7.0
- Initial Home Assistant add-on packaging (pass 7b).
- Reuses the standalone container recipe; app fetched from `main` at build.
- Add-on options → env (LLM provider/model/key, temperature, max-tokens,
  recent-titles N, timezone, gunicorn sizing).
- SECRET_KEY generated once and persisted to /data (stable across restarts).
- First-run auto-seed: starter catalogue + one user with a generated password
  printed to the add-on log.
- SQLite DB persists in HA's /data (captured by HA backups).
