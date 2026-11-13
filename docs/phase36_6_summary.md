# 0.36.6 — "Needs a hand: Unlinked ingredients" filter

Finding recipes with unlinked lines without opening each one. Rather than a
warning mark on every affected row (noisy, since imports often have one) or a
new system-checks page (a route for a single check), it's a filter.

- `history/routes.py`: `_unlinked_recipe_ids()` is one DISTINCT query for
  recipe ids with a line where `ingredient_id IS NULL AND NOT to_buy`. That's
  the same rule as the note on the recipe page, so the two always agree. A new
  facet `check` (`CHECK_LABELS = {"unlinked": "Unlinked ingredients"}`) comes
  last in `_FacetOptions.FACETS`. Rows carry `data-check="|unlinked|"`. A
  pick-one pair matches if either recipe does. Favourites gets the same.
- `recipe_facets.js`: group name "Needs a hand" (the receipt review's phrase).
  The count line reads "N recipes have unlinked ingredients" while that chip
  is on; this takes priority over the ingredient-search phrase.
- The value only exists while some recipe matches. When everything is linked,
  the group disappears, and the saved chip is dropped on restore (existing
  behaviour for vanished values).

Tested: the group appears last; 4 matching rows with the right count line; a
to-buy unlinked line is ignored; combined with Imported; linking one and
reloading removes it; linking all removes the chip, the count line and the
group. Favourites shows the group too. No JS errors.
