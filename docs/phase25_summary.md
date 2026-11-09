# Phase 25 — Usage foundation + special request (0.25.0)

## Schema
One additive migration (`b25e7d3a9c41`) on `generations`:
`special_request` (text), `input_tokens`, `output_tokens` (int, nullable).

## Token capture
Each provider sets `last_usage = {"input", "output"}` per `generate()` call,
alongside `last_finish_reason`. Where the numbers come from:

- Gemini: `usage_metadata.prompt_token_count`, and `candidates_token_count +
  thoughts_token_count` (thinking is billed at the output rate).
- Anthropic: `usage.input_tokens` / `usage.output_tokens`.
- Mock: a chars/4 estimate, so the usage page has numbers in dev.

`_run_generation_job` adds the tokens to the row in a `finally` around **each
attempt**, so a retry is counted and every exit (success, truncation, provider
error, malformed output) commits them. NULL means not tracked: rows from
before 0.25 have no data, and there's no backfill.

`get_provider(config, model=None, max_tokens=None)` now takes per-call
overrides, ready for the Q&A model in Phase 27.

## Limits (`usage/service.py`)
Counted with a `COUNT` over `generations` since **local midnight**
(`APP_TIMEZONE`, converted to naive UTC to match how SQLite returns
`created_at`). This works across both gunicorn workers and needs no new
table. Failed generations count, because they can still have used tokens.

| Config / add-on option | Default |
|---|---|
| `LIMIT_GENERATIONS_PER_USER_DAY` / `limit_generations_per_user_day` | 10 |
| `LIMIT_HOUSEHOLD_CALLS_DAY` / `limit_household_calls_day` | 40 (generations now; plus questions in Phase 27) |

`wizard.generate` checks three things in order:

1. **The session's own running job** (unchanged): resume it.
2. **Any non-stale running job by this user** (new): resume it rather than
   start a second paid call. This holds across tabs and devices.
3. **The limits.** If one is hit: an `info` flash and a redirect to review,
   with the typed request kept.

The review page shows "N left today" when 3 or fewer remain. At 0 it shows a
notice and disables the Generate button.

## Usage page (`/usage`, nav "Usage", under More on mobile)
Shows today's meters (yours and the household's), totals (today, 7 days,
30 days, all time: calls, failed, tokens in/out, estimated cost), a per-person
breakdown for the last 30 days, and the last 20 calls. It's visible to the
whole household. Cost is computed at render time from `MODEL_PRICES`
(USD per 1M tokens, checked Nov 2026) and **never stored**. A model not in the
table shows tokens but no cost. A one-pass Python summary over all generations
is fine at household scale.

## Special request
- `SPECIAL_REQUEST_MAX_CHARS = 280` (in `models.py`).
- `clean_special_request()` collapses whitespace, strips the `<<<` / `>>>`
  fence markers and caps the length. It runs at the route and again in
  `build_brief`.
- **Review UI:** the box sits between the brief recap and Generate, labelled
  "Anything in mind? (optional)", with a one-line hint. The placeholder is
  chosen at random from six examples on each render. Four chips (*Something
  spicy*, *Keep it simple*, *Traditional*, *One pan*) add their text, and a
  chip whose text is already there is skipped. The text survives a trip into a
  suggestion card through `sessionStorage`, which is cleared on submit. It
  also lives in the wizard state, so a blocked submit or "back" from
  generating keeps it.
- **Brief:** `special_request` is added to the brief. When present, the
  **creative seed is suppressed** (stored as NULL).
- **Prompt:** a block after Servings, emitted **only when a request exists**.
  The text is fenced between `<<<` and `>>>`, followed by the instructions:
  steer both recipes as two distinct takes; rank below ALLERGIES and MUST-USE
  and above dislikes, preferences, cuisine and everything else; dislikes still
  apply unless the request names that food outright; the request can't change
  allergies, rules, units or format. The system prompt is untouched.
- **Display:** AI recipes made with a request show "You asked for: …" above
  the intro.

## Prompt regression
`render_prompts.py` before and after: every existing golden and spot check is
**byte-identical**. The only difference is four new goldens appended:
`request_curry`, `request_tired_simple`, `request_adversarial_allergy`
(forbidden: peanut) and `request_names_a_dislike` (required: mushroom).
**`flask eval-recipes` must be run with a live key before merging** to check
that the block steers as intended. The adversarial and dislike cases are the
ones to read closely.

## Verified (dev, mock provider)
- Migration is clean and `flask db check` reports no drift.
- A request is stored cleaned (fence markers stripped), the seed is NULL, the
  block is present and the angle line absent; with no request, the seed is
  set as before.
- Tokens are recorded on the row, and the recipe page shows the request.
- With the limit set to 2: the third generate redirects to review with the
  flash, and the button is disabled.
- A running job by the same user is resumed from a fresh session.
- The usage page renders its totals, and the nav item is present.
