# Phase 19 — Recipe notes (0.19.0)

**Shipped:** free-text household notes on any recipe. Attributed, timestamped,
oldest-first, many per user per recipe. Author-only delete; no edit.

## Decisions
- **Notes instead of ratings; ratings retired.** A rating needs a consumer —
  prompt forbidden, favourites own the filter, sorting is a report nobody runs.
  Notes carry the rating *and* the reason. Recorded in roadmap §4 so it isn't
  re-litigated.
- **Own table, not a join.** The join-table rule covers one-value-per-pair.
- **No AJAX.** POST-redirect-GET + `#notes` anchor: page-level submission, not
  an inline edit like the tag/link editors.
- **No edit, no `updated_at`.** Correction = a second note.
- **Absent from the print view** — free, since it's a separate template.
- **No `cooked_on` column.** The date lives in the prose.

## Learnings
- `order_by` on the relationship beats sorting in the route — the chronology
  can't be got wrong by a caller.
- `white-space: pre-wrap` preserves the author's line breaks without ever
  reaching for `|safe`.
- `flask db migrate` writes the file; `flask db upgrade` applies it. Skipping
  the second gives a clean autogenerate log and a `no such table` at first
  template access. Read the generated file, then upgrade, then restart.

## Untouched
`llm/prompt.py`, the resolver, the eval harness, the suggestions query, the
print/share route. No golden-set re-run required.
