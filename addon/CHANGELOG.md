# Changelog

## 0.18.2 - Little fixes to share page

- Added border around timer pills for better visibility
- Fixed double-line closing render
- Improved overlap behaviour on long pages (now constrained to sections)

## 0.18.1 - Print / share polish

- The share view is now presented as **Print / share this recipe**, with a
  printer icon — printing or saving to PDF is the reliable way to send a recipe
  to someone.
- Added a short hint on the page explaining how to print from a phone.

## 0.18.0 - Share a recipe

- New **Share this recipe** button on every recipe: opens a clean, chrome-free
  version of the recipe with no navigation bars, so a scrolling screenshot
  captures the whole thing uninterrupted.
- The same page prints (or saves to PDF) properly on a light background.

## 0.17.1 - Tidier cuisine choices
- Condensed the cuisine list into clearer groups, so more recipes get a fitting tag.
- Cuisine and meal type now shown as compact chips rather than a long stacked list.

## 0.17.0 - Richer cuisines & smarter recipe variety
- Expanded the cuisine choices: added French, Middle Eastern, Indian, Thai, Chinese and Mexican, and split the old catch-all "Asian" into its distinct cuisines.
- Creative variety is now tailored to the meal type. Desserts and baking draw on sweet-leaning ideas rather than savoury ones, and sauces are left to their own devices.
- Regional flavour nudges no longer pull against a cuisine you've specifically chosen.
- When no cuisine is chosen, generations now vary between a creative nudge and a completely free hand for more variety across recipes.
- Sharpened how "Sauce or dressing" is interpreted, so you get the sauce itself rather than a dish built around one.

## 0.16.2 - Fixes

- Fixed recipe display for ingredients without specified unit

- Adjusted 'baking' meal type generations to actually result in the craft, not just the technique.

## 0.16.1 - made recipe editing orderable

- Ingredients, prep, cook, tips sections now reoderable within their sections

## 0.16.0 - Much more intuitive stock management

- Shared search bar to filter existing stock and add from catalogue.

- Clear distinction of staples showing up in search

- Management of staples separated in the manage route

## 0.15.1 - Polka hero

- Little styling update on home page and generating spinner

## 0.15.0 - Quite a nice little improvement to user experience

- Making a shift from 'functional' to 'intuitive'

## 0.14.1 - Fixed llm leaning too heavily on "To-buy"

- Prevented llm generated recipes bbeing based around a to_buy not-in-stock ingredient,
instead guided the llm to use as 'optional extras' i.e garnish, flavour enhancers and to never build a
meal around an item not in stock

- Rephrased "You may need to-buy" -> "Optional Extra" for clarity

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
