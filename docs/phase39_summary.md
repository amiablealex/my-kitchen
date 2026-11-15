# 0.39.0 — kinds, the "or" editor, retired selection

Migration `a5d19e3c7f20` (`ingredients.parent_id`, nullable self-FK).

- **"A kind of".** `Ingredient.parent` / `kinds` (backref, `remote_side`).
  `Ingredient.on_hand` (staple, or in stock and active) and `available_as()`
  (itself, else the first kind on hand; a retired general still counts its
  kinds). `RecipeIngredient.satisfied_by()` walks the link then the "or"
  alternative through `available_as`; `satisfied` and `stock_state` use it,
  so marks, `_is_cookable` and `cookable_now` agree. `stock_label` gives
  "In stock (Fusilli)" when something other than the link covers it; it's
  the mark's title, sent with link changes and by the stock endpoint (now
  `{ri_id: {state, label}}`). `_covers_must_use` counts kinds of linked
  generals. The direction is one-way: a kind's line isn't satisfied by its
  general or a sibling.
  - Manage: `_set_parent` (one level; refuses a general that is itself a
    kind, or an ingredient with kinds); the edit form posts `parent_id`
    only when the field is shown. `POST /ingredients/<id>/kinds` (ticked
    `kind` ids: active, no parent, no kinds) and `.../kinds/<kind>/remove`.
    Delete frees the deleted one's kinds; merge hands the duplicate's kinds
    to the kept one when it can have kinds, via the relationship (a bulk
    UPDATE left them in the doomed collection and the delete NULLed them).
  - The ingredient page: meta line "a kind of X"; *A kind of* select
    (general ones only, grouped by category) unless it has kinds; *Kinds*
    section with chips, × and *+ Add kinds* sheet. `ingredient_sheets.js`
    drives both sheets (replaces 0.38's `ingredient_merge.js`).
- **"Or" editor.** `recipe.html` adds `.ri-or-row` rows (`.ri-or-pill`, not
  `.link-pill`, so nothing reading a row's pills sees the editor's copies)
  and wraps search/results/add-new in `#ri-editor-search-area`.
  `recipe_links.js`: `layout(row)` picks the two-row or plain view;
  `openSearch(slot, heading)` reveals the search for *Change* / *Add*.
- **Retired selection.** The Retired section is `data-retired` with an
  always-shown *Select all* (starts a retired selection). `selCtx`
  ("active"/"retired") set on start; taps on the other context are ignored
  and it's dimmed. The bar shows *Reactivate N* (`data-reactivate`) and
  hides *Move to…* and ⋯ (`.select-bar [hidden] { display:none !important }`
  — `.btn`'s display beat `[hidden]`). Bulk action `reactivate`, with the
  usual `previous` for Undo.
- **Retired page.** `notice--archived` with *Reactivate* (primary, like an
  archived recipe's Restore); Reactivate removed from ⋯; activate now
  returns to the ingredient's page.
- **SW cache** v31.

Tested on a throwaway DB at head with the mock provider and Playwright at
390px: a "pasta" line ticked via Fusilli with the label, a "spaghetti" line
still needing spaghetti with Pasta ticked, must-use via a kind, both
one-level refusals, add/remove kinds, merge moving kinds, delete freeing
them, the two-row editor (search hidden until Add/Change, correct headings,
plain lines unchanged), retired notice, retired select (Reactivate 2, Move
hidden, active taps ignored), bulk reactivate + Undo. resolve-eval PASS; the
0.38 checks re-run clean. No JS errors.
