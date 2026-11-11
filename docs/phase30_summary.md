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
