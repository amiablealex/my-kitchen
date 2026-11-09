# Phase 27 — Ask @kitchen (0.27.0)

The last of the four phases planned in `plan_phases_24-27.md`.

## Schema
One additive migration (`d27b3c5e8f12`) on `recipe_comments`: `kind`
(NULL/`note` | `question`), `answer`, `answer_status` (`pending` | `done` |
`error`), `answered_at`, `model`, `input_tokens`, `output_tokens`. Constants
in `models.py`: `KITCHEN_MENTION = "@kitchen"` and
`QUESTION_MAX_CHARS = 500`.

**The answer lives on the question's row.** Threading needs no new column,
deleting the question takes the reply with it, and existing author-only
delete covers both. Visibility model: shared and attributed, like notes.
Not in the print view, the brief or suggestions.

## Posting
Questions go through the same `recipe_comment_add` form. `_strip_mention`
only treats a **leading** `@kitchen` as a question (case-insensitive,
followed by a word boundary and optional punctuation, then removed).
"hi @kitchen" and "@kitchens" stay notes, so a passing mention can't cost a
call. The question is stored without the prefix and rendered with a
`.mention` chip.

The route checks length, then `question_blocked_reason` (per-user questions
plus the household total; when blocked, nothing is posted and a flash
explains). It then creates the row as `pending`, starts `answer_question`
on a daemon thread and **waits up to 20 s**. The redirect goes to
`#note-<id>`.

This avoids SDK-specific HTTP timeouts entirely. The usual case lands
answered; a slow one shows "Thinking…" and `notes.js` reloads every 4 s
(never while the note box has text in it).

A pending row older than 120 s counts as stale and shows *Try again*. While
pending, `answered_at` marks when the current attempt started, so a retry
restarts that clock. A retry reuses the row and checks only the household
limit.

## Answering (`llm/qa.py`)
- **Prompt:** its own `QA_SYSTEM_PROMPT` (answer only, short, plain text, UK
  conventions, sensory cues, no allergens or dislikes, stay on this recipe,
  suggest Refine for rewrites). The generation prompt is untouched.
- **Context:** the recipe as contract JSON (`recipe_to_contract`), the
  servings the cook is viewing (posted from the scaler's `sessionStorage` as
  `viewing_servings`), **all active household members'** allergies and
  dislikes, in-stock items and staples, the last 3 answered Q&As on the
  recipe, and the question fenced in `<<<`/`>>>`.
- **Model:** `LLM_QA_MODEL` / `llm_qa_model`. Blank means
  `DEFAULT_QA_MODELS["gemini"] = "gemini-3.5-flash-lite"`. A `ProviderError`
  on the QA model **falls back once to the main model**, so a renamed or
  unavailable Lite id degrades to a slightly dearer answer rather than a
  broken feature.
- **Call settings:** `max_tokens` 1024 (thinking counts against it),
  temperature 0.4, `json_mode=False`, `thinking="low"`.
- **Clean-up:** `_clean_answer` strips stray markdown emphasis and headings
  and caps the text at 4000 characters.

## Provider changes
- `generate()` takes `json_mode` (default True) and `thinking` (optional).
- **Gemini** builds `ThinkingConfig(thinking_level=...)` only if the
  installed SDK can express it, and retries once without it if the API
  refuses.
- **Anthropic** ignores both knobs.
- **Mock** returns canned plain text when `json_mode=False`.
- `get_provider()` also takes a `temperature` override.

## Limits and usage
- `LIMIT_QUESTIONS_PER_USER_DAY` / `limit_questions_per_user_day` (default 20).
- Questions now count towards the household daily total.
- The usage page treats question rows as calls through a small adapter
  (`_QuestionCall`): a "Question" type, a per-user meter, and inclusion in
  every total, the per-person table and recent calls.

## UI
- The composer label reads "Add a note, or ask @kitchen", with a matching
  placeholder.
- An *Ask @kitchen* chip (with the pinwheel) prefixes the mention, and is
  disabled when you have no questions left today.
- The submit button reads *Ask @kitchen* while the box starts with the
  mention, and *Asking…* on submit.
- The reply is indented with a teal rule and a faint teal wash, the pinwheel
  avatar and the name "Kitchen". The thinking state uses three bouncing dots
  in the accents, with reduced motion respected.

## Verified (dev, mock)
- Migration is clean and `flask db check` reports no drift.
- Mention parsing: `@kitchen how long?` and `@Kitchen: why` are questions;
  `hi @kitchen` and `@kitchens rule` are notes; a bare `@kitchen` is refused
  with a prompt to add the question.
- A posted question is answered within the wait, with model and tokens
  recorded. The prompt carries the scaled servings, the household allergy
  and the Q&A history.
- With the limit set to 3, the fourth question is refused with a flash and
  the chip is disabled.
- An error row shows *Try again*, and a retry answers it.
- The usage page counts questions and shows the meter. Deleting a question
  removes the row.

## After this arc
Phases 24–27 are complete. Remaining roadmap: web ingestion, photo
ingestion, and a Gemini 3.6 Flash eval for generation cost. The spec and
roadmap deltas are recorded in each phase summary (24–27) for the next doc
pass.
