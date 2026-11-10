# Phase 29 — @kitchen "Make this version N" (0.29.0)

Checkpoint 2 of the Petals arc (checkpoint 1 is `phase28_summary.md`). It
connects the two AI paths on the recipe page. A question can turn into a new
version, but only when the answer itself proposes a **major** change.

## Schema
One additive migration (`e29a4b7c1d63`, revises `d27b3c5e8f12`) adds a
nullable `suggested_change` (Text) to `recipe_comments`. There is no backfill:
answers from before 0.29 stay NULL and never show the button.

## Signal: a marker line, not JSON
`QA_SYSTEM_PROMPT` gains a "Flagging a bigger change" block.
- **Flag only a MAJOR change**, one that alters the dish enough that the
  ingredients and method need rewriting: vegetarian/vegan, a different method
  or appliance, a different kind of dish, a main ingredient that cooks
  differently, or a whole new component.
- **Never flag** like-for-like swaps (lemon for lime, dried for fresh, thighs
  for breasts, one cheese or oil for another), quantity nudges, garnishes, or
  storage/freezing/reheating/timing/doneness/technique/serving questions.
- **Flag** with a final line `CHANGE: <instruction under 15 words>`.
- **"When in doubt, don't flag."**

The old "suggest they use Refine" line is gone; the button replaces it.
Answers stay plain text (`json_mode=False`, unchanged), so a garbled marker
just costs the button, never the answer.

`split_change(text)` in `llm/qa.py` is pure, and is shared by the job and the
eval. It pulls out the **last** `CHANGE:` line from anywhere in the text,
tolerates markdown bold, strips quotes, caps at 200 characters and
capitalises. It matches within a single line only (`[ \t]`, not `\s`), so an
empty marker can't swallow the next line. The rest goes through
`_clean_answer` as before.

`qa_models(cfg)` now holds the QA-model-then-main-model fallback, shared by
`answer_question` and the eval.

## UI
In the reply, when `c.suggested_change and can_refine` (latest version, not
archived), a ghost `.reply-refine` button reads *Make this version
{{ next_v }}*, with the instruction in `data-refine-change` and `title`.
`refine.js` wires it to `window.mkRefine`, the same path as the servings
rewrite: pre-fill, open, and the confirmation dialog still applies.

## Eval: `flask eval-kitchen`
`eval/kitchen_harness.py` runs 10 fixed questions (4 should flag, 6 shouldn't)
against a transient recipe, never added to the session. It uses the real
prompt, model choice and parser, plus the live stock, staples and household
dietary tags. It prints PASS/FAIL, shows the CHANGE text and the answer on a
miss, and exits 1 on any miss. Options are `--provider` and `--only <text>`.

The mock provider flags by keyword (vegetarian, vegan, slow cooker, air
fryer, "turn this into", pasta), so the plumbing can be exercised offline:
10/10 on mock. **The judgement needs a real run** (Gemini Lite) before
merging. Re-run it after any edit to `QA_SYSTEM_PROMPT`.

## Archive leftovers (from 0.28)
Not removed after all. `row_archive` was the only way to clear a
**failed-generation** row, which has no recipe page and so no ⋯ menu. Failed
rows now carry a × (`.row-archive`, data key `generation_id`), with the
Undo toast reading "Cleared.". Recipe rows stay action-free.
`recipe_archive.js` and `toast.js` are back on the Recipes page, and
`row_restore` serves Undo.

## First real eval run (Pi, Gemini Lite): 7/10, all judgement correct
The three ERRORs (vegetarian, traybake, pasta) were empty replies with
finish reason `MALFORMED_RESPONSE`. The SDK raises nothing and `resp.text` is
None, so the old fallback (exceptions only) never ran. In the app those
questions would have shown *Try again*. They were all should-flag cases.

Fixes:
- **`ask(cfg, prompt)`** in `qa.py` is the one call path for the job and the
  eval. An empty reply counts as a failed attempt, so the main model gets its
  turn. Usage is summed across attempts. It returns `fallback`, and the job
  logs when the fallback answered.
- **The prompt's flag instruction** is now plain text with a literal
  example line, instead of an `CHANGE: <…>` placeholder containing angle
  brackets and nested quotes. That template was the likeliest trigger for
  the malformed output, though it isn't proven.
- **The eval** prints `(answered by fallback …)` with the reason, and counts
  fallbacks in its summary. A pass that needed the fallback is still a pass
  for judgement, but a run with many fallbacks means the Lite model is
  struggling.

## Verified (dev, mock)
- `flask db upgrade` from empty runs to `e29a4b7c1d63`, and `flask db check`
  reports no drift.
- `split_change` edge cases pass: no marker; marker with bold or quotes;
  empty marker; lower-case label; the word "Changes" in prose.
- Posting "@kitchen could I make this vegetarian?" stores the change and
  shows one *Make this version 2* button. "lemon instead of lime" stores NULL
  and shows no button. `CHANGE:` never appears in the page.
- Tapping the button opens the refine panel pre-filled, and Create → dialog.


## 0.29.2 — choosing ingredients: chips, search, stock in place
**Chips.** Both `options--grid` blocks on `step_ingredients.html` became
`options--chips`. The selected morph is untouched (same `.option`, `--pick`,
tick, sharp corner). Staple chips inside the drawer sit on `--surface-2` so
they don't vanish into the drawer's `--surface`.

**Search** (`static/wizard_ingredients.js`). Client-side filter over lane and
staple chips by name (not the note). Empty lanes and staple groups hide; the
drawer opens while a staple matches and returns to its prior state on clear.
Hidden picked inputs still submit. Enter is swallowed: the first submit
button in the form is *Edit stock*, so implicit submission would leave the
page. Escape clears.

**Not in stock.** `GET /cook/ingredients/catalogue?q=` renders
`wizard/_catalogue.html`: `search_catalogue` minus in-stock and staples,
capped at 12. A tap POSTs the existing `stock.add`, builds a picked chip in
the lane named by `data-section` (alphabetical, *just added* meta), and
toasts *X is now in stock* with Undo (`stock.remove`). With an empty pantry
the lanes render hidden so an added chip has somewhere to go.

**Round trip.** *Edit stock* is `<button name="go" value="stock">`. The step's
POST saves `selected_ingredient_ids` then redirects to
`stock.index?return_to=…`. The stock page swaps its top back link for a docked
*Back to your picks* (the Cook tab starts a fresh wizard, so it mustn't be
the obvious way back). Removed-from-stock picks have no chip on return and
fall out on the next submit.

**Review wording.** Nothing picked showed *Staples* / "leaning on staples &
suggested extras". The prompt has always said MUST-USE empty means design
freely from AVAILABLE + staples, so it now reads *Anything in stock* /
"free to use anything in stock"; only an empty pantry says *Staples only*.
No prompt change.

`sw.js` cache → v8.
