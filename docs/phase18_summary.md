# Phase 18 — Recipe suggestions at "Lets cook" (add-on 0.14.0)

The keystone payoff. The cook wizard's review step now surfaces saved recipes
the household can cook right now that fit the brief, as tappable cards, before
offering AI generation. A pure deterministic DB query — NO LLM, NO resolver.

## The match rule (as implemented — `my_kitchen/wizard/suggestions.py`)
A saved `Recipe R` is suggested iff ALL hold:
- **Provenance:** chosen AI recipe (`source='ai' AND was_chosen`) OR any non-AI
  recipe (`user`/`imported`). The unchosen AI sibling is passed over by the
  household and hidden from History, so it isn't suggested. (SQL-filtered:
  `source != 'ai' OR was_chosen`.)
- **Meal-type:** `R.meal_type == wizard.meal_type` (always set; defaults Dinner).
  Untagged (NULL) → excluded — an untagged recipe makes no claim. (SQL.)
- **Cuisine:** if wizard cuisine is the Surprise sentinel / None, or the meal
  type is non-cuisine-bearing → no constraint. Else `R.cuisine == wizard.cuisine`;
  untagged (NULL) → excluded. (SQL when constrained.)
- **Cookable** (Python over `R.ingredients`): for each line with `to_buy=False`
  — unlinked (`ingredient_id` NULL) → exclude (can't confirm); staple → skip
  (assumed available); else require `in_stock AND is_active` (retired → exclude).
  `to_buy` lines are ignored (optional extras). Zero required lines → vacuously
  cookable (theoretical: legacy row-less recipes carry meal_type NULL and are
  already excluded upstream).
- **Must-use:** every wizard `selected_ingredient_id` appears among R's linked
  ingredient ids — a real structured check, replacing the old free-text guess.

**Not** filtered by: time band, cooking-for / allergies / preferences (allergy
machinery stays on the generate path only), or servings. Ordered newest-first.
Household-scale bank → SQL-filter the cheap columns, evaluate cookability +
must-use in Python for clarity.

## Summary-page UX (`templates/wizard/review.html`)
- Suggestions on top: a horizontal scroll-snap row of calm cards (source dot via
  the `_source.html` macro, meal-type/cuisine tag pills, an optional quick/relaxed
  badge, "Serves N"). Display font only on the card title, per the brand guide.
- Card tap → the existing recipe page; browser back re-renders the review page
  from the preserved wizard session (no special state handling).
- Below: the generate path (flow unchanged), carrying its own brief recap so the
  user sees what a NEW recipe would be built from. "Nothing take your fancy?"
  framing when there are suggestions.
- Empty/sparse state (the common case early): a gentle "Nothing in your bank
  matches yet — let's make something" nudge over the generate path. Not an error.

## Other changes
- **`recipes.time_band`** (nullable, additive migration, `render_as_batch`). DISPLAY
  ONLY — drives the card badge, never the match query. AI recipes copy it forward
  from the generation in `_run_generation_job` (post-hoc; generation sealed); user
  recipes set it on the create/edit form (server-rendered `selected`, JS-independent).
  No backfill — pre-0.14.0 AI recipes stay NULL (badge omitted) until re-made.
- **"Any" label:** the wizard cuisine step and the review summary display the
  Surprise-me sentinel as "Any". Label only — the value, `recipe_cuisine_from`,
  and all generation behaviour are unchanged.

## What web ingestion (next) inherits
- A working, source-agnostic suggestions query keyed on `recipe_ingredients`
  links — `source='imported'` recipes drop straight in once they resolve/link.
- The standard contract + resolver path already produce the linked rows the query
  needs; ingestion just adds a new extractor and routes through the existing
  review/edit UI (`recipe_form.html`) before saving, exactly like user recipes.
- Confirmed: suggestion quality is gated on link coverage + meal-type/cuisine tags,
  so imported recipes must be tagged on review to be suggestable (same as user).
