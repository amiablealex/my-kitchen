# Phase 20 — Staples as must-use (0.20.0)

**Shipped:** staples selectable in wizard step 1; must-use/staples dedupe in the
brief; the `in_stock` staples-tier bug fixed; a notes marker on the recipe lists.

## Decisions
- **Separate drawer, not a fifth lane, not category-grouped lanes.** The four
  sections are a fixed guardrail (spec §3); grouping the wizard by category
  would make the screen's shape depend on user-editable config, which is exactly
  what the guardrail exists to prevent. Staples get category grouping *inside*
  the drawer, where there's no lane semantics to preserve.
- **The drawer auto-opens when a staple is already selected.** A collapsed
  section must never hide active state — that was the main risk of the design
  and the first thing tested.
- **Must-use wins the dedupe.** Mandating an item and separately listing it as
  free-to-use filler is contradictory instruction to the model.
- **The empty-pantry state is no longer a dead end** — the drawer renders even
  when nothing is in stock, so a staples-only brief is now reachable from the UI.

## Bugs found while reading
- `build_brief` filtered the staples tier on `in_stock=True`, but nothing sets
  that flag for staples: Manage's toggle doesn't, new ingredients default
  `False`, and `/stock` excludes them entirely. So a staple added the obvious way
  was **silently invisible to the model**. `suggestions.py::_is_cookable` had it
  right (`if ing.is_staple: continue`); the two halves disagreed about what
  "staple" means. Aligned on the suggestions behaviour.
- `prompt.py` hardcoded `"surprise me"` instead of importing `SURPRISE_ME` from
  `models.py`, where every other consumer keys off it. Renaming the sentinel
  would have silently emitted `Cuisine: Surprise me.` as though it were a real
  cuisine — no error, just worse output on every unconstrained generation. The
  0.14.0 "Any" relabel changed only the display and missed this by luck.

## Verification
`render_prompts.py` diff clean across all three prompt-adjacent changes (staples
tier, dedupe, cuisine sentinel). The sealed-prompt rule satisfied by **proof**
rather than re-testing — no `flask eval-recipes` run needed. The staple counts
(`is_staple` total vs `in_stock=True` subset) were equal on the live catalogue,
which is what made the tier fix a provable no-op on existing data.

## Learnings
- Check a filter's flag has a UI that can set it. `in_stock` on a staple was
  unreachable by design, so the filter could only ever subtract.
- Two modules encoding the same domain rule independently will drift. The fix
  isn't just to align them but to note which one is authoritative — here,
  `suggestions.py`, because it matched the spec's definition.
