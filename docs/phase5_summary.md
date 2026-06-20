## Roadmap Phase 3 — Stock list interaction redesign

All scoped work built, tested on the Pi, and committed across three runnable
checkpoints. Application-code only — no schema change (the existing `in_stock`
flag already supported everything). Deliberately unstyled, as scoped.

Both stock surfaces — the standalone `/stock` and the wizard's first step
`/cook/stock` — moved from a checklist of *every* catalogue ingredient to a
**pantry view** of only what's in stock, grouped by category. The two surfaces
now share one editing component instead of `/cook/stock` being a near-copy.

- **Shared stock-editing component.** A `stock/_editor.html` partial plus
  `stock/service.py` (`in_stock_groups()`, `search_addable()`), included by both
  `/stock` and the wizard step. Shows in-stock, active, non-staple items only —
  staples and retired ingredients are excluded from both the pantry and search.
- **Explicit remove** (sets `in_stock = false`), replacing the old flip-style
  toggle (the `/stock/<id>/toggle` route was dropped). Removes in place via JS.
- **Search-to-add.** Case-insensitive substring over addable items (active,
  non-staple, not already in stock); `/stock/<id>/add` sets `in_stock = true`.
  Adding reloads the current surface, so the new item appears in the pantry and
  (on the wizard) the step returns to itself.
- **"Add a new ingredient" hand-off** to manage → ingredients, with the typed
  term passed through as `?name=` to pre-fill the add form.
- **CP1** built the component + remove and refactored `/stock` onto it; **CP2**
  added search-to-add + the hand-off; **CP3** wired `/cook/stock` onto the same
  component, keeping the wizard's step heading, Continue link, and session flow.

## Things learned / bumped into

1. **Search returns server-rendered HTML, not JSON.** The "Add" buttons need
   their URLs built by `url_for`, so the JS injects a rendered fragment and never
   constructs a URL itself — keeps sub-path / ProxyFix serving correct. General
   pattern for any future "fetch a list of actionable rows" feature.
1. **LIKE wildcards are escaped** in `search_addable`, so a user typing `%` or
   `_` matches literally instead of acting as a wildcard.
1. **A change that spans two files bites if only half lands.** The `?name=`
   prefill (route + template) and the wizard wiring (import + view body) each
   broke once when only one half was applied — the latter as a `NameError` on
   `in_stock_groups`. Standing reminder: when an edit spans route+template or
   import+body, confirm *both* halves are on disk before restarting.
1. **Template edits need a gunicorn restart.** With debug off, Jinja caches
   templates, so a template-only change is invisible until the worker restarts
   (Python edits obviously need a restart too).
1. **The hand-off link leaves the wizard.** "Add a new ingredient" navigates to
   manage; the wizard session persists (resume via `/cook/stock`), but the nav
   "Cook" link restarts the wizard. Accepted — kept the component shared rather
   than diverging it per surface.

## Forward notes

- No new schema or structural debt opened up; spec §4.1 already described this
  pantry behaviour, so spec and implementation are aligned (no correction needed,
  unlike the favourites rework last pass).
- Still open from earlier and untouched here: equipment-into-the-brief and prompt
  sophistication (roadmap Phase 4), UTC→local-time display (Phase 5), server-side
  idempotency / async generation (Phase 6), Dockerisation (Phase 7), and
  batch-cook.

2026-06-19

## Follow-on cleanup (same phase): removed the in-wizard stock step

After the stock surfaces were consolidated, we removed the wizard's first step
(`/cook/stock`) entirely. That step embedded the destructive pantry editor inside
a "pick ingredients for this meal" flow, where a user thinking about *tonight*
could remove an item from stock while only meaning "not this meal" — inadvertently
mutating the master list. Stock maintenance and meal selection are now cleanly
separated, matching the landing page's two distinct buttons (Update stock / Lets
cook). The wizard opens directly at ingredient selection (now Step 1; cuisine/
time/cooking-for renumbered to 2/3/4), `start()` redirects there, and the
`step_stock` view + template were deleted. Application-code only, no schema change.

Mid-wizard stock fixes still happen, via a persistent "Stock not right? Update →"
link on the ingredient step that round-trips through the shared `/stock` editor
and back. Since `/stock` is shared and can't know to return on its own, the link
passes a `return_to` parameter; `/stock` validates it with an open-redirect guard
(`_safe_return` — internal paths only, rejecting absolute and protocol-relative
URLs, same spirit as the auth `next` check) and renders a "← Back to choosing
ingredients" link. The wizard session is preserved throughout (nothing clears it
but `/cook/` itself, which the round-trip avoids), and because add-to-stock
reloads the current URL, `return_to` survives adds. The ingredient step already
reads in-stock state live on every render, so changes made during the round-trip
appear immediately on return. Finally, the empty-pantry case — now the wizard's
first impression — shows an empty state pointing at "Update stock →" rather than a
blank selection box, while still allowing Continue (a staples-only generation
remains valid).

2026-06-20
