# Phase 30 — organising the catalogue (0.30.0)

Three requests from re-homing ~30 carbs into new Grains, Pasta and Bread
categories: bulk-move ingredients, keep sections together, reorder categories
without typing numbers.

## Ordering
`Category.ordering()` (models) returns the one ORDER BY used everywhere: a
CASE on `section` in `SECTION_CHOICES` order, then `display_order`, then
`lower(name)`. Every former `order_by(Category.display_order, …)` uses it:
manage, stock service and route, the wizard's staples, and the recipe editor.
`display_order` now means position *within* the section.
`_next_display_order(section)` appends to a section. Changing a category's
section on its page puts it at the end of the new one. The Order input is gone
from both forms.

Migration `a73e5c19d2f4` (data only, revises `f41c8d2a9b70`) renumbers each
section 1..n by (display_order, lower(name)), so relative order survives.

## Reorder on the tree
`manage.categories_reorder` takes JSON `{section, ids}`. The ids must be
exactly that section's categories (409 otherwise, so a stale page can't drop
or steal one), and are renumbered 1..n. `static/category_tree.js` handles:
- the per-section *Reorder*/*Done* toggle (only shown with 2+ categories);
- grips (`drag_indicator`, `touch-action: none`) that drag via pointer
  capture, swapping at neighbours' midpoints;
- arrow keys on a focused grip;
- save on drop, or reload with a toast if the save fails.

While reordering, rows aren't links and the add branch hides. The last real
row takes the curved `└`.

## Select mode (Manage → Ingredients)
`link_chip` gained `id` (→ `data-id`); lists are `[data-selectable]`.
`static/manage_ingredients.js`:
- **Entering:** long-press (450ms, cancelled by 8px movement; the next click
  is swallowed, and the flag resets on every pointerdown) or ⋯ → *Select
  ingredients*. `contextmenu` is suppressed on chips, and CSS sets
  `-webkit-touch-callout: none` / `user-select: none` so Android's link menu
  stays away.
- **While selecting:** a tap toggles `.is-picked`. *Select all* in each header
  covers the visible chips (filter-aware) and flips to *Clear* when all are
  picked. Switching tab clears the selection.
- **The bar** (`.select-bar`, fixed above the bottom nav) has ✕, the count,
  *Move to…*, and a ⋯ with Make staples (Standard tab), Move to standard stock
  (Staples tab) and Retire, which confirms via `mkConfirm`.

`manage.ingredients_bulk` (JSON) has actions `move`, `staple`, `standard` and
`retire`. It returns `message` plus each item's `previous` {category_id,
is_staple, is_active}. The page stashes both in sessionStorage with the scroll
position and reloads. On load it shows the toast; Undo posts `restore` with
`previous`. Bulk delete is deliberately absent.

`confirm.js` now also exposes `window.mkConfirm({title, body, ok}) → Promise`.
The form-based `data-confirm` path is built on it.

## Small things
- Category `<select>`s use `category_select` (optgroups by section) on the
  ingredient page and the add form.
- Manage → Ingredients sorts by `lower(name)`, so lowercase entries no longer
  trail after Z.

`sw.js` cache → v14.


## 0.30.1 — archiving from the Recipes page
**Server.** `history.row_archive` now also takes `{"rows": [{generation_id|recipe_id}, …]}`
(the single-row shape still works). It returns `{recipe_ids, generation_ids}`,
and `row_restore` accepts `generation_ids` alongside the old single
`generation_id`. What a row means is unchanged (`_archive_one`): a picked pair
archives the pick, an unpicked pair archives both, a failed attempt archives the
generation. The lineage context is built once per request.

**Rows.** Every Recipes row carries `data-archive-key` / `data-archive-id`.
Unpicked pairs also carry `data-archive-n` (for "Archived 2 recipes."), and
failed rows `data-archive-failed`.

**`recipe_archive.js`** runs one pointer gesture per row:
- Touch only. It locks to a swipe when `dx < -12` and `|dx| > 1.4·|dy|`, and
  bails as a scroll if `|dy| > 12` first.
- Holding 450ms without moving 8px enters select mode.
- `--dx` moves the row's children; `.is-armed` shows past 40% of the width.
- On release while armed, it slides the row out, then archives.
- After a swipe or a hold, the following click is swallowed by a capture
  handler, so the row's links don't navigate.

Select mode copies Manage → Ingredients: per-group *Select all* (respects the
facet filter's `hidden`), a docked bar with *Archive*, and Esc to leave. Archive
removes the rows in place, and Undo re-inserts the same elements in reverse order.

No confirm dialog, by decision: archiving is reversible.
`sw.js` cache → v15.


## 0.30.2 — a calmer recipe top
In `wizard/recipe.html`:
- The favourite form moved into `topbar_actions` as `.fav-star`, and *Edit
  tags* (`#tag-edit-toggle`) became a ⋯ menu item.
- `.recipe-tags-view` is now `p.recipe-meta`. `#tag-meal-pill` and
  `#tag-cuisine-pill` are plain `.rm-item` spans with dot separators drawn by
  CSS between visible items. `recipe_tags.js` hides an unset one instead of
  writing "No meal type", and closes the ⋯ menu when the editor opens.
- The blurb lost its source bead (the dot leads the meta line). The intro is
  `p.recipe-intro-text`. The old `.recipe-meta-row` "Serves N." line is gone.
- The serves stepper lives in the Ingredients `.section-head`.
- `.servings-note` is a single line: Scaled from N · the method's amounts are
  for N · Reset. `servings.js` finds the note and reset in the section,
  and reset has its own listener.
- The *Rewrite the method for this many* prompt (`.servings-refine`) was
  removed, by decision: the scaled amounts are enough.
- *Edit links* moved to the end of the list; `recipe_links.js` swaps its
  label to *Done editing links*.

`sw.js` cache → v16.
