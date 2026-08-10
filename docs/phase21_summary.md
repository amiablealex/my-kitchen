# Phase 21 — Faceted recipe filter (0.21.0)

**Shipped:** one filter input over cuisine / meal type / cook / source plus free
text, as tokenised chips. History and Favourites.

## Decisions
- **Suggestion-driven, not auto-detecting.** "italian" is a cuisine tag AND a
  title word; auto-converting hides recipes named after their own cuisine.
- **Client-side, including Cook.** Whole bank already in the DOM. Loses
  URL-backed state; gains instant filtering.
- **Pipe-bounded facet fields** ("|italian|indian|") so a substring test is a
  whole-value match — "indian" can't half-match "west indian".
- **New file, not an edit to `recipe_filter.js`** — that one is shared with
  Manage → Ingredients and had to keep working.
- **Grouping kept, Source param dropped.** Grouping is display; source is now a
  chip.

## Bugs found
- `index.html` showed `row.gen.cuisine` (the *request* — "Any"/"Surprise me")
  instead of `row.chosen.cuisine` (the tag). A retagged recipe displayed the
  wrong cuisine. Fixed.
- `?source=` was orphaned: preserved in a hidden input with no control left.

## Learnings
- **`flex-basis` is main-axis.** `.recipe-filter`'s `flex: 1 1 12rem` meant
  *width* in the row-direction toolbar; wrapping it in a column-direction
  `.facet-box` silently turned that into a 12rem *height*. Any rule moved into a
  container of the opposite direction needs its flex re-examined.
- **A plain IIFE reads the DOM at parse time.** The `#facet-options` blob placed
  after the script tag meant the element didn't exist yet — and a broad
  `try/catch` swallowed it as an empty option list, so it failed as a silent
  behaviour regression rather than an error. Distinguish "element missing" from
  "JSON malformed"; they're different bugs.
