# Phase 26 — Regenerate, refine and the version trail (0.26.0)

## Schema
One additive migration (`c26a1f8e4d07`) on `generations`:
- `kind`: NULL/`generate` | `regenerate` | `refine`
- `parent_generation_id` (FK generations)
- `source_recipe_id` (FK recipes)
- `instruction` (text, refine only)

`Generation.recipes` now declares `foreign_keys="Recipe.generation_id"`,
because there's a second FK path between the tables. `Generation.source_recipe`
and `Recipe.refined_from` are ORM-only.

## One job machine
Regenerate and refine are just `Generation` rows. Each one gets the same
running status, background thread, poll page, stale guard, retry-once,
token capture and post-hoc resolver as a normal generation. They also count
towards the daily limits automatically. `_run_generation_job(..., mode)` gets
a `"refine"` mode, which uses `REFINE_SYSTEM_PROMPT`, expects one recipe
(`validate_and_normalize(count=)`) and supersedes the source in the same
atomic commit. The new recipe takes the source's (possibly hand-edited)
meal type, cuisine and time-band tags and becomes the chosen one; the
source's `was_chosen` flips to False.

`_start_guard()` is the shared pre-flight for generate, regenerate and refine:
one running job per user (resume it), then the daily limits.
`_done_url()` routes a finished job: a refine goes to its recipe
(`?refined=1`), everything else to the choice screen. `generating`, `status`
and `choice` all use it.

## Regenerate ("Neither — try again")
- **Choice screen:** a `<details>` panel with the request box pre-filled from
  `gen.special_request`, a tries-left count, and a "The previous two" link
  back up the chain.
- **Brief:** rebuilt from the parent row (`state_from_generation`) with
  current stock. It doesn't depend on the wizard session, so it works from
  History too.
- **Prompt:** a block emitted only when `rejected_titles` is set: every
  title from **the whole chain** so far ("go in a clearly different
  direction"). It sits after recent titles and before the seed; with no
  request, the seed is re-rolled.
- **Limit:** `LIMIT_REGENERATES_PER_BRIEF` / `limit_regenerates_per_brief`
  (default 3), counted by walking up `parent_generation_id`.

## Refine
- **Recipe page panel** (AI recipes; latest version only; not archived):
  "What would you change?" plus four chips. It's open when you arrive with
  `?fresh=1`, which `choose()` now adds. The refine button disables on submit.
- **Scaler link:** when the servings scaler is moved off the base count, its
  note offers *Rewrite the method for this many*, which fills the refine box
  with "Make this for N people" (`window.mkRefine`, so `refine.js` loads
  before `servings.js`).
- **`start_refine`:** the brief comes from the source generation's state with
  must-use emptied, so the dietary context is the original cooking-for list
  with current tags, and the pantry is current stock. Servings are the
  recipe's own.
- **Prompt:** the generation `SYSTEM_PROMPT` is reused **unchanged** with
  `REFINE_ADDENDUM` appended (one recipe, no must-use tier, carry the change
  through every field, allergies absolute, dislikes yield only to a named
  request). `build_refine_prompt` contains the current recipe as contract
  JSON, the fenced change request, then the shared pantry and dietary
  sections.
- `_pantry_lines` / `_dietary_lines` were **extracted verbatim** from
  `build_user_prompt` so both prompts share them. `render_prompts.py` proves
  every existing golden and spot check is byte-identical.

## Version trail
`recipe_versions(recipe)` walks back through `refined_from`, then forward
through finished refines. It returns `[(recipe, label)]`, oldest first, where
the label is "Original" or the instruction that produced that version. The
page renders a horizontal pill strip (v1, v2…, current highlighted) only when
there's more than one version. An older version shows a "Latest version"
notice and no refine panel. Refining a non-latest version is refused at the
route as well, which keeps the history linear.

## History
`_lineage_context()` hides a generation row when something newer stands in
for it:
- **A regenerate round replaces its parent** while the parent has no chosen
  recipe, so a chain shows as one row.
- **A finished refine replaces the generation of its source.**
- **Running jobs no longer show** as "Generation failed".

Chosen rows carry a `vN` badge from a memoised depth walk. `row_archive` uses
the same context, so archiving acts on exactly what the row shows.

## Usage page
Recent calls are labelled Generate / Try again / Refine, and there's a new
*By type* table for the last 30 days.

## Eval
`GOLDEN_REFINES` (`refine_spicier`, `refine_for_six` with a new `servings`
assertion, `refine_allergy_holds` with forbidden "peanut") run in
`flask eval-recipes` alongside the briefs (`--only` works across both).
`render_prompts.py` prints them in a new final section. The mock provider
returns one "Refined …" recipe in refine mode. **Run `flask eval-recipes`
with the live key before merging.** The regenerate block has no golden: it's
only emitted on regenerate, and the end-to-end test checks it's there.

## Verified (dev, mock)
- Migration is clean and `flask db check` reports no drift.
- Generate → choice (prefilled retry) → two regenerates. The third prompt
  lists all 4 earlier titles, and the limit blocks the next try with a flash.
  The "previous two" link works, and History shows **one** row.
- Choose lands with the refine panel open. An empty instruction bounces back.
  A refine lands on the new recipe with `?refined=1`.
- The trail reads Original → "Make it spicier"; the source is superseded and
  the new recipe is chosen with its tags inherited. The old version shows the
  notice and no panel, and refining it is refused.
- History shows one row with a v2 badge, and the usage page shows all three
  types.
