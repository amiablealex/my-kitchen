# 0.36.3 — petal marks, lighter rows, ingredient search

## What changed

**Source marks are petals.** `.source-dot` now uses `border-radius: 50% 50% 50% 18%`,
which is the house petal (sharp corner bottom-left) at any size, and has lost its
drop shadow. Because the mark is shared, it's a petal everywhere: list rows,
recipe header, filter options, notes, ask chip. Filter-option marks went from 8px
to 10px so the shape reads.

**Rows.** The mark moved out of `.row-title` into its own column of the row
(`row_mark()` in `history/_rows.html`). It's 11px and centred across both lines,
so the title and meta line share one left edge. A pick-one pair
(`.recipe-row--pair`) aligns it to its first line. A failed generation gets a
hollow petal (`.source-dot--failed`), so its text still lines up. The title is
weight 550 with line-height 1.35, the meta line 1.35, and the padding is 8px.
Rows come out at about 52px at the default size: about the same height as
before, but lighter. The Archived list uses the same structure.

**Filter panel.** The teal ring is gone; the search icon turns teal while the
box has focus. The panel is in the page flow (no longer `position: absolute`),
so it pushes the list down and never covers half a row. Title results also stay
visible while typing.

The square corners Alex saw came from `border-radius: var(--petal) var(--petal) 0 0`.
`--petal` is four values, so the declaration was invalid and the browser fell
back to 0. It's spelt out now. The receipt cropper's `.frame-shade--top/--bottom`
had the same bug and is fixed too.

**Ingredient search.** `history/routes.py` `_ingredient_search(recipe_ids)` makes
one join query (RecipeIngredient × Ingredient). It returns each recipe's linked
ingredient ids and a `{lowercased name: id}` lookup, limited to ingredients the
listed recipes use. Rows carry `data-ing="|12|45|"`, and the lookup is printed as
`#facet-ingredients`. `recipe_facets.js` `ingredientFor()` matches the typed
text against whole names, forgiving a simple plural either way. A row then
matches on title OR ingredient. The count line reads "3 recipes use brown sugar"
when the ingredient path is active. It works with filter chips and on
Favourites. Unlinked lines can't match, the same rule as suggestions.

## Tested (Playwright, 390px)
- Rows 52–53px; pair row 85px. Mark is 11px with the petal radius. Title and meta
  start at the same x.
- Panel `position: static`, below it the list starts after the panel; open box
  radius 20px 20px 0 0.
- "brown sugar" finds the linked recipe, with "1 recipe uses brown sugar". "Brown
  Sugar" works too. "brown" matches nothing (whole names only). "egg" finds the
  Eggs recipes ("2 recipes use eggs"). "risotto" still matches by title.
- Imported chip + "Brown Sugar" combined; kept after opening a recipe and going
  back. Select mode, Favourites and Archived render; no JS errors.
