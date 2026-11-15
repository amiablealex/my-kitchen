# 0.38.0 — merge ingredients, "or" links, unlinked-line integrity

Prompted by a real slip: deleting "Baby button mushrooms" left an AI recipe
uncookable with no warning. Migration `f2c7d84a1e36`.

- **Dangling links.** `ingredient_delete` used to delete the row only; SQLite
  isn't enforcing foreign keys, so recipe lines kept a dead `ingredient_id`.
  The pill and stock mark (via the relationship) said "not linked" and
  suggestions treated the line as unlinked, but the note and filter
  (`ingredient_id IS NULL`) missed it. Now `_unlink_everywhere` clears the id
  first (a line losing its main link takes its alternative). The migration
  NULLs any `ingredient_id` not in `ingredients` — a repair of broken
  references, the same kind of exception as 0.30.0's category reorder.
- **Scope of "unlinked".** `Recipe.suggestable` = not AI, or chosen.
  `history._unlinked_recipe_ids()` joins Recipe and filters on it, and the
  recipe page renders the note only when suggestable, so pick-one pairs and
  unchosen recipes drop out (they're never suggested).
- **Merge.** `POST /manage/ingredients/<id>/merge` with `into`. Moves main and
  alternative links, clears an alternative that now equals the main link,
  `target.in_stock |= src.in_stock and src.is_active`, carries the note if
  the target has none, deletes the source. The sheet lists every other
  active ingredient in catalogue order. `_recipes_using()` feeds the edit
  head ("used in N recipes"), the delete confirmation and the retire/delete
  flashes.
- **"Or" alternative.** `recipe_ingredients.alt_ingredient_id` (nullable FK),
  `RecipeIngredient.alt_ingredient`, `offers_or` (`\bor\b` in raw_text),
  `satisfied` (main or alternative available; staples in, retired out) used
  by `stock_state` and `suggestions._is_cookable`; `_covers_must_use` and the
  Recipes ingredient search count either link. Invariant: no alternative
  without a main link.
  - Resolver: `resolve_line(text, index)` → (main, alt). Main is the usual
    whole-line resolution, unchanged (resolve-eval: PASS, 0 false links). The
    alternative needs BOTH sides of the first " or " to resolve, to different
    ingredients, and a fuzzy side must contain every word of its match
    (`_side`), so "fresh or frozen peas" doesn't link Fresh rosemary. If the
    whole line misses but both sides hit, the left becomes the main link.
    Used by generation (`llm/service.py`) and import (`llm/importer.py`).
  - Link endpoints take `slot=alt` (only on `offers_or` lines; with no main
    link it sets the main link). Unlinking the main link promotes the
    alternative. Responses (`_link_payload`) carry both links and `stock`.
  - Recipe form carries `ing-N-alt_id` / `alt_name` as hidden fields, shows
    "or X ×", and drops the alternative when the main link is re-picked.
    `_form_alt_id` keeps it only on an "or" line, active, not equal to main.
  - "Used anything up?" offers either half of an "or" that's in stock.
- **SW cache:** v30. **Icon:** `call_merge`.

Tested on a throwaway DB migrated through e8a3c51f2b94 with a dangling row
inserted, then upgraded (repaired to NULL); mock provider; Playwright at
390px. Checked: alternative saved from the form, stock mark and cookability
with only the alternative in stock, slot=alt refused on a non-"or" line,
remove/add/promote/add-new on the alternative, delete unlinking with the note
and filter picking it up, an unchosen pair absent from both, merge moving
lines and stock, retire/delete flashes, the merge sheet's filter and button
label, and no JS errors.
