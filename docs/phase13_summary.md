# Phase 13 — Keystone 3a: the ingredient resolver

**Status:** ✅ Done. Production-roadmap §3.2 / §5 step 3 (first half of the
keystone). A deterministic, **no-LLM** free-text → catalogue-ingredient resolver,
built and **measured in isolation** against a golden set — the same way the
prompt eval grounds generation. Built CP1→CP3 on the dev Pi, each checkpoint
tested before moving on. Developed on the `keystone` branch; **not merged to
main, no version bump, no CHANGELOG entry** — the catalogue and resolver ship
with 3b. The deliverable is a **number**, not a visible feature.

**Headline:** **38/38 golden cases, ZERO false links, all 6 precision traps
hold, zero misses.** The resolver is dormant — its only consumer this phase is
`flask resolve-eval`. No schema change, no wiring into generation/import/pages.

## What landed

- **Broadened seed catalogue** (`my_kitchen/seed_catalogue.py`, new) — a
  zero-import pure-data module that is the **single source of truth** for both
  the production seed *and* the DB-free eval fixture, so they cannot drift.
  **173 ingredients** across **10 categories** (the original seven plus **Herb**
  → `veg`, **Fruit** → `other`, **Condiment** → `other`). **43 staples.** This is
  data, not schema — `seed_reference_data()` was extended to consume it; **no
  migration**. `in_stock` seeds to equal `is_staple` (initial stock = the
  staples; the household toggles core items in the UI).
- **The resolver package** (`my_kitchen/resolver/`, new): `core.py` (the pure
  DB-free engine), `aliases.py` (the curated alias constant — 45 entries),
  `db.py` (a **dormant** DB-backed wrapper for 3b, not called in 3a).
- **The golden harness** (`eval/resolver_harness.py` + `eval/golden_ingredients.py`,
  new) and the **`flask resolve-eval`** CLI command — the permanent
  resolver-regression tool, mirroring `eval-recipes` / `render_prompts.py`. Also
  runnable DB-free via `python -m my_kitchen.eval.resolver_harness`.
- **`rapidfuzz>=3.0`** added to `requirements.txt`. Confirmed installing on the
  dev Pi 4 (aarch64/Bookworm) from a prebuilt manylinux wheel — no compile.

## The cascade (how precision holds)

Layered, precision-over-recall. The guiding idea: the **least-stripped** form of
the query gets first crack at an exact/alias hit, and removable words are peeled
only after a miss. Two normalisation forms, applied identically to queries,
catalogue names and alias keys:

- **`norm_min`** — lowercase → de-accent → drop digits + punctuation → drop
  UNIT, CONNECTIVE and NUMBER-WORD tokens → singularise. Keeps prep words,
  descriptors, colours, form/type words.
- **`norm_core`** — `norm_min` with the **STRIP** set additionally removed.

Cascade: `norm_min` exact → `norm_min` alias → `norm_core` exact → `norm_core`
alias → `token_set_ratio` ≥ threshold → unmatched.

Because every multi-word canonical (Sweet potato, Ground coriander, Fresh thyme,
Red onion, Black pepper) **exact-hits at `norm_min` before any qualifier could be
dropped**, the precision traps pass *by construction* — they cannot collapse to
the generic entry. Confirmed by an invariant: **all 173 catalogue names
self-resolve `exact`, all 45 aliases resolve to their declared canonical.**

## Normalisation — the strip lists and the threshold (the tuning record)

**The decisive call: colour / form / type words are NEVER stripped.** `STRIP`
(removed only in `norm_core`) holds prep/state/size/adverb words plus
`fresh` / `sea` / `extra` / `virgin` / `whole`, and **deliberately excludes**
`sweet, red, green, black, white, new, spring, ground, dried, smoked, double,
single, sun` — each distinguishes a real catalogue entry. `fresh` is in STRIP but
safe: a `Fresh thyme` / `Fresh rosemary` query exact-hits at `norm_min` before
the strip pass runs. **`tinned` is not stripped** (it would collide
Tinned tomatoes ↔ Tomato, and breaks Tuna (tinned)).

- **Tier-1 drops** — `UNITS` (g, kg, ml, tsp, tbsp, clove, tin, can, pinch,
  handful, slice, …), `CONNECTIVES` (of, a, an, the, and, with, to, …),
  `NUMBER_WORDS` (one…twelve, half, dozen, couple, few, several, some, …).
- **Singularisation** — light, symmetric, with an `us/ss/is` guard plus a
  `NO_SINGULAR` stopset (asparagus, couscous, hummus, molasses, …). Symmetric
  application means "wrong-but-consistent" forms still match.

**Fuzzy threshold = 90.0, scorer = `token_set_ratio`** (not `partial_ratio` /
`WRatio`, whose substring matching would false-link e.g. `lemongrass` → `lemon`).
Evidence: the worst off-catalogue negative scores **71** (`curry leaves` →
Bay leaves); genuine catalogue-name spelling variants score **≥93**
(`greek yogurt` → Greek yoghurt 96, `mozzarela` → Mozzarella 95). 90 sits in a
**19-point gap** above the worst false candidate — the precision-first choice.
Lowering to ~85 would catch more aggressive typos (e.g. `cauliflour`, 86) and
still clear every negative by 14+ points; it is a one-line change
(`FUZZY_THRESHOLD`, or `flask resolve-eval --threshold 85` to preview). Kept at
90 because AI/JSON-LD sources mostly spell correctly.

## CP3 real-cooking finding (and fix)

Adding real cases mined from `examples.md` surfaced a genuine false link:
**"two small red onions" → Onion** (not Red onion). Two causes, both fixed:

1. **Word-quantities weren't stripped.** "two" survived `norm_min`, so `norm_core`
   couldn't reach an exact `red onion`. Fix: `NUMBER_WORDS` are now stripped at
   tier-1, so "two small red onions" → `red onion` → **exact** Red onion.
2. **Fuzzy tie to the generic entry.** When a query is a token-superset of both a
   generic ("Onion") and a specific ("Red onion") name, `token_set_ratio` scores
   **both 100** and first-wins picks the generic. Fix: among candidates at the
   top score, prefer the one sharing the **most tokens** with the query (then the
   longest name) — the more specific match. A precision guard, not a recall lever.
   Confirmed on unknown-adjective cases too: `spanish red onion`,
   `lovely red onions, chopped` → Red onion. "two small red onions" → Red onion
   is now a permanent golden regression case.

## Final numbers (golden set — 38 cases)

```
match rate  : 38/38 = 100.0%
FALSE LINKS : 0          (0 on traps, 0 on negatives, 0 anywhere)
misses      : 0
per-method  : exact=20  alias=8  fuzzy=2  unmatched=8
traps       : 6/6 hold
```

The two fuzzy matches are real-world spelling/abbreviation variants
(`greek yogurt` → Greek yoghurt 96; `dry red lentils` → Red lentils 100). Fuzzy
contributes **zero** matches on the original inputs-doc golden set — exact + alias
+ normalisation carry it, which is the desirable outcome since fuzzy is the only
risky tier.

## Catalogue / alias tweaks (logged, baseline of record)

1. **`cod` dropped** from the white-fish collapse — `Cod fillet` is its own
   catalogue entry; haddock / pollock / white fish (no own entry) stay collapsed
   to White fish fillet.
2. **`aubergine eggplant` doc-slip dropped** from the Bell pepper line (those map
   to Aubergine); only `capsicum → Bell pepper` kept.
3. **`tuna` aliases added** (`tuna`, `tinned tuna`, `tin of tuna` → Tuna (tinned))
   — the inputs package omitted them; the canonical's parenthetical never appears
   in free text.
4. **`brown onion` / `white onion` → Onion** added (CP3) — frequent household
   terms (per `examples.md`), made deterministic rather than left to fuzzy.
5. **`in_stock = is_staple`** seed default.
6. Catalogue is **173 items** (the package said ~150).

## What 3b inherits — the resolver API surface

**Pure core** (`my_kitchen/resolver/core.py`, DB-free, catalogue + aliases
injected):

- `ResolveResult(ingredient_id, matched_name, score, method)` — frozen dataclass;
  `method ∈ {exact, alias, fuzzy, unmatched}`; `score` 0–100 (100 for
  exact/alias). `UNMATCHED` sentinel. **The golden set asserts on
  `matched_name`** (reseed-stable), never the id.
- `build_index(catalogue, aliases) -> Index` then
  `resolve_with_index(free_text, index, threshold=90.0) -> ResolveResult` —
  **the efficient path; 3b should build the index once and reuse it** when
  resolving a recipe's many ingredients.
- `resolve(free_text, catalogue, aliases, threshold=90.0)` — convenience that
  builds an index per call (fine for one-offs).
- Helpers: `norm_min`, `norm_core`, `best_fuzzy` (diagnostics).
- Inputs: catalogue = iterable of `(ingredient_id, name)`; aliases =
  `{alias_text: canonical_name}`.
- Tunables/constants: `FUZZY_THRESHOLD`, `FUZZY_SCORER`, `UNITS`, `CONNECTIVES`,
  `NUMBER_WORDS`, `STRIP`, `NO_SINGULAR`.

**Dormant DB wrapper** (`my_kitchen/resolver/db.py`, **not called in 3a**):

- `load_catalogue() -> [(id, name)]` — active ingredients **including staples**
  (valid resolution targets), excluding retired. Requires app/DB context;
  imports `models` lazily so the pure core stays import-light.
- `resolve_text(free_text) -> ResolveResult` — resolves against the live
  catalogue + `ALIASES`. **3b wires this (or `build_index(load_catalogue(),
  ALIASES)` once) into the ingestion / AI-output post-processing paths.**

**Alias constant** (`resolver/aliases.py: ALIASES`, 45 entries) — stays a curated
Python constant; promotion to a DB table is deferred past 3a.

**Regression tool** — `flask resolve-eval` (or `python -m
my_kitchen.eval.resolver_harness`) + `eval/golden_ingredients.py` (38 cases).
**Re-run after any catalogue / alias / normalisation change in 3b.**

## What 3b does next

- **The big migration:** `recipe_ingredients` (`recipe_id`, nullable
  `ingredient_id` FK, `raw_text`, `amount`, `unit`, `to_buy`, `position`);
  `recipes` gains `source` / `meal_type` / `author` and `generation_id` made
  nullable; `recipe_ratings` join.
- **Wire the resolver in** post-hoc: AI / imported free-text → `resolve_with_index`
  → `ingredient_id` (null = unmatched/`to_buy`, degrades gracefully). Generation
  stays completely sealed.
- **Production catalogue merge (deferred to 3b):** the already-seeded household DB
  won't pick up the new 173 via the idempotent seed guard — 3b needs a
  data-migration/reconciliation step (the dev rebuild was from scratch; there was
  no production data to preserve in 3a).
- **Add-on image rapidfuzz install** — verify in 3b's production rollout (the dev
  Pi 4 aarch64 wheel is confirmed; the add-on base image is a separate check).

## Guardrails honoured

No schema changes; no wiring into generation/import/templates; `prompt.py` /
`build_brief` / `build_user_prompt` / `render_prompts.py` / `golden_briefs.py`
**untouched** (the sealed prompt stays byte-identical); aliases remain a constant,
not a DB table; stock stays a binary toggle; no production release. Change
footprint: 2 modified files (`seed_data.py`, `cli.py`, plus `requirements.txt`)
and 6 new files (`seed_catalogue.py`, the 4-file `resolver/` package, 2 eval
files).
