# Phase 32 — the stock sheet (0.32.0)

Second of the input-side arc (`plan_phases_31-36.md`). No schema change, no
LLM surface. Builds the confirmation sheet Phase 33's receipt scanner reuses.

## The sheet
`templates/stock/_sheet.html` + `static/stock_sheet.js` →
`window.mkStockSheet.open({mode, title, note, items, unplaced, onDone})`.
One `<dialog class="confirm sheet stock-sheet">`. Pills are `.option`
checkboxes coloured by section (`sec-pick--*`), so the picked style is the
app's own. Mode `in` starts them picked; `out` starts them unpicked. Confirm
posts `{ids, in_stock}` to `stock.bulk` and hands the *changed* ids to
`onDone`; `window.mkStockUndo(ids, wasInStock)` flips exactly those back.

**Needs a hand.** Lines the app couldn't place are dashed rows showing the
line as written. Tapping one clones `#needs-panel-tpl` under it: a search over
`#stock-sheet-catalogue` (active non-staples, embedded JSON — no fetch per
keystroke), *Add as new…* (category must be chosen; posts `stock.create` with
`stock=0`, so Cancel stocks nothing; a 409 for an existing non-staple just
places that item), and *Skip this line*. Placing turns the row into a picked
pill with the original line beneath. Unticking any pill that carries an
original line (a guess) sends it back to Needs a hand. "N lines still to
place" sits above the button but doesn't block it. The panel and catalogue
are only rendered when the caller passes `sheet_catalogue`, so the recipe
page's used-up sheet has neither.

## Quick-add (stock page)
`stock.js`: when the search box holds a comma/semicolon list of 2+ items, the
pantry is hidden (so the offer sits right under the box) and the results area
shows *Add these N items →* (Enter works too). A trailing comma or semicolon
is ignored for an ordinary search, so "milk," still searches "milk". A paste containing line breaks is intercepted and joined
with commas, because a single-line input silently drops line breaks.
`POST stock.parse` → `parse_list()` in `stock/service.py`:
- `split_list()` splits on line breaks, commas and semicolons; strips
  bullets, numbering, trailing prices and multipliers; drops lines with no
  letters or starting with receipt furniture (`_NOT_ITEMS`: total, visa,
  clubcard, bag…); de-duplicates; caps at 80.
- One resolver index per request. A **fuzzy hit on a staple** goes to
  unplaced ("peppers" → Black pepper would otherwise vanish as a staple).
  Exact staple hits and already-in-stock items are only counted, for the
  sheet's note.

After confirming, the page reloads with a sessionStorage toast
(`mk-stock-toast`) offering Undo.

## Used anything up? (recipe page)
`wizard.recipe` builds `used_up_items`: the recipe's linked, active,
in-stock, non-staple ingredients, de-duplicated. When non-empty, a quiet
`.text-btn` line closes the Cook section and `used_up.js` opens the sheet in
`out` mode. No reload: marked items drop from the list (the line hides at
zero) and Undo puts them back.

## Small things
- `stock.create` takes `stock=0` and returns `section`; its 409 carries the
  existing item.
- `stock.bulk` ignores staples and retired ingredients and returns only the
  ids that changed.
- New `.text-btn` (quiet inline button). No accent stripes.
- `sw.js` cache → v18.
