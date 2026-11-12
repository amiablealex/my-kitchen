# Phase 31 — home page (0.31.0)

First of the input-side arc (`plan_phases_31-36.md`). No schema change, no
LLM surface.

## Rotating hero line
`main/hero.py` holds `HERO_LINES`, a list of `(line, min_items)`. Lines may
use `{name}` (the logged-in cook), `{a}`/`{b}` (two random in-stock,
non-staple ingredients; `{A}`/`{B}` capitalised for a sentence start) and
`{n}` (in-stock count). `pick_line()` only offers lines whose data exists, so
nothing renders with a gap. `_lower_first` lowercases a name mid-sentence but
leaves acronyms ("BBQ sauce") alone. The previous index is kept in
`session["hero_last"]` so a reload never repeats the line. The wordmark title
and the "What's for dinner?" eyebrow are gone; the line uses `.display` with
`text-wrap: balance`. Edit the wording freely: nothing else depends on it.

## Cookable now
`wizard/suggestions.py` gained `cookable_now()`: the same provenance, archive
and cookability rules as `suggest_recipes`, with no meal-type, cuisine or
must-use constraint (the home page has no brief). Recipes with no
`recipe_ingredients` rows are skipped rather than vacuously cookable. Lines and
their ingredients are `selectinload`ed, since it walks the whole bank on every
home load.

The home page shows one muted `<details>` line — "N saved recipes you could
make right now" — hidden at zero, opening in place to the first
`HOME_COOKABLE_CARDS` (10) cards. The count still says the full number.

The card markup moved into `_suggestions.html` (`sugg_card` macro), shared
with the wizard review step, which no longer imports `source_dot` directly.

`sw.js` cache → v17.
