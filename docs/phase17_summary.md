# Phase 18 — Recipes-page organisation (4c)

Shipped as add-on **0.13.0**. Read-side only — **no schema change, no new routes,
no migration**. The deferred 4c work from Phase 16: source filter + a colour-coded
source marker.

## What shipped
- **Source filter** on `/history` alongside the Cook filter. `?source=ai|user`
  (anything else = no filter); read-side only — it decides which tables
  contribute (`ai` → generations only, `user` → user recipes only, `""` → both)
  and composes (AND) with the Cook filter, which each table still applies on its
  own column. Tailored empty state when a filter combination is empty.
- **Source dots** — a colour-coded dot per recipe, no pill, no text:
  - **AI** = a four-quadrant pinwheel in the wizard accents (`--accent-1..4` via
    a `conic-gradient`) — the generative signature, tied to the cook wizard's
    step dots.
  - **User** = solid lime (`--accent-2`).
  - **Imported** = solid orange (`--accent-3`) — reserved, unused until web/photo
    ingestion lands.
  - Polka-dot sized (18px list / 22px recipe page) with a soft shadow.
- Dots appear on the **recipes list**, **favourites list**, and the **recipe
  page** (leading the blurb, or the serves line when there's no blurb — kept off
  the rainbow `<h1>` where a marker would be redundant).

## How
- Single shared macro `templates/_source.html` → `source_dot(source)` maps
  `source` to one `.source-dot--{ai|user|imported}` class; anything not
  user/imported → `ai`. Decorative (`aria-hidden`) — origin is also carried
  textually by the "cooked by" / "created by" meta and the Source filter.
- Colours are pure CSS off the existing brand tokens; the pinwheel is a
  `conic-gradient` of the four accents. No JS.
- Generation rows pass `'ai'` literally; recipe-bearing surfaces pass the real
  `recipe.source` column.

## Deliberately left out
Sort options, counts/summaries, any textual source badge. 4c is strictly
read-side organisation.

## Inherited / next
- The **imported** dot slot is reserved, so web/photo ingestion needs no 4c
  rework — it just starts emitting `source='imported'` recipes.
- The source filter + per-source query split is a clean base if a future phase
  wants source-scoped views elsewhere.
- Remaining roadmap: wizard pre-AI **suggestions** (filter saved recipes by the
  wizard's meal-type/cuisine + in-stock linked ingredients — all the substrate
  now exists), then web ingestion.
