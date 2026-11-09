# Phase 24 — Archive + servings scaler (0.24.0)

The first of four phases planned in `plan_phases_24-27.md`. No LLM surface:
the prompt, resolver and eval harness are untouched, so no golden-set re-run.

## Archive

**Schema (one additive migration, `a24f0c1e7b52`).** `recipes.archived_at` +
`recipes.archived_by_user_id` (FK users), and `generations.archived_at`, which
is used **only** for failed generations because they have no recipes to
archive. The recipe columns are the record for anything with content. Because
`Recipe` now has two FKs to `users`, both relationships declare
`foreign_keys` (`author`, `archived_by`).

**Visibility model: shared and attributed.** When one person archives a
recipe, it's archived for the whole household, like notes and ingredient
links. It's a soft delete only, with no hard delete.

**Where it's filtered.** `Recipe.live()` is the one filter clause, used by
History's hand-made list, Favourites and the wizard suggestions query. The
History AI rows go through `_generation_row()`:

- a chosen row disappears with its chosen recipe (the unchosen sibling never
  comes back as an "unchosen" row)
- an unchosen row shows whichever of its recipes are still live
- a failed row follows `generations.archived_at`

The facet options are built from the visible rows, so they follow
automatically. The anti-repetition recent titles still include archived
recipes on purpose.

**Surfaces.**
- *Recipes list:* a quiet archive button on every row. It posts JSON to
  `history.row_archive`, which archives what the row shows and **returns the
  set it touched**. The row is removed, and the toast's **Undo** posts that
  same set to `history.row_restore` and puts the same DOM element back. URLs
  come from `data-*` on `#recipe-bank` (`recipe_archive.js`). JSON rather than
  an HTML fragment because the client re-inserts markup it already holds.
- *Recipe page:* *Archive this recipe* (form POST, the page stays put). An
  archived recipe's URL still renders, with a banner saying when and by whom,
  and a **Restore** button, which is the undo.
- *Archive page* `/history/archived`, linked from the Recipes header: archived
  recipes, most recently archived first, each with Restore. Failed generations
  aren't listed because there's nothing in one to restore.

## Servings scaler

Front-end only (`servings.js`). Nothing is posted; the print/share view and
the JSON export always use the recipe's own count.

- A stepper (−/+, 48px targets) under the Ingredients heading, range 1 to
  max(24, 4 × base), with "Reset to N" and a note that method quantities and
  times are still for N. The "Serves N" line near the title follows the
  stepper. The stepper is hidden until the JS runs, so without JS the page is
  unchanged.
- The chosen count is kept in `sessionStorage` under `mk:serves:<id>`, so it
  survives the page's own reloads (adding a note, favouriting).
- A new `scalable_line` macro in `_ingredients.html` gives the same text as
  `ingredient_line`, with the amount in `<span class="ing-amt" data-amount>`.
  The share view still uses `ingredient_line`.
- **Parsing.** Only a leading number or range is scaled, with any trailing
  words kept (`2 large` → `3 large`). Handled forms: integers, decimals,
  unicode fractions, `1 1/2`, `1-2` / `1 to 2`. Anything that doesn't start
  with a number (`a splash`, `to taste`) is left exactly as written.
- **Formatting.** Metric units (from the unit or the amount's suffix) round to
  the nearest 5 at 100 and above, to whole numbers from 10, and to one decimal
  below 10. Everything else rounds to the nearest ⅛ / ¼ / ⅓ / ½ / ⅔ / ¾, and
  to whole numbers from 10. A real amount never scales to nothing. Scaled
  amounts are tinted teal.
- The link editor only rewrites the pill, never the line, so scaled amounts
  survive link edits.

## Verified (dev, throwaway DB)
- Upgrade from the Phase 19 head is clean; `flask db check` reports no drift.
- History: archiving a chosen row hides it and the sibling stays hidden; a
  failed row and a hand-made row archive and restore. Undo restores exactly
  the set that was archived. Archived recipes are absent from Favourites and
  suggestions and present on the Archive page.
- Recipe page: amount spans render; the archived banner shows and the archive
  button hides; the share view has no scaler markup.
- Parser cases checked in node: `200g ×2 → 400`, `1½ ×½ → ¾`, `1-2 ×2 → 2–4`,
  `0.5 ×3 → 1½`, `a splash` unchanged.

## Spec deltas (to fold into `recipe-app-spec.md`)
§3 `recipes`: `archived_at`, `archived_by_user_id`; `generations`:
`archived_at` (failed rows only). §4 step 5: suggestions exclude archived
recipes. §5.4: the servings stepper and archive action/banner. §6: archive
filtering, per-row archive with undo, the Archive page.
