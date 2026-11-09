# Production iteration plan — Phases 24–27 (0.24.0 → 0.27.0)

Agreed scope for the next four phases, settled 9 Nov 2026. Companion to
`recipe-app-spec.md` and `production-roadmap.md`. Web ingestion moves to after
Phase 27, and the roadmap's parked per-generation "avoid tonight" box is
superseded by the special request (Phase 25).

| Phase | Version | Scope | LLM surface |
|---|---|---|---|
| 24 | 0.24.0 | Archive + servings scaler | None |
| 25 | 0.25.0 | Usage foundation (limits, model per task, token capture, `/usage` dashboard) + special request | Dynamic brief block only |
| 26 | 0.26.0 | Regenerate + refine + version trail | Regenerate block; refine prompt |
| 27 | 0.27.0 | Ask @kitchen (AI replies in the notes feed) | New Q&A prompt |

Usage controls land before any new feature that calls the model.

## Phase 24 — Archive + servings scaler ✓
See `phase24_summary.md`.

## Phase 25 — Usage foundation + special request

**Token capture.** Each provider records `last_usage` (input, output including
thinking) the same way it records `last_finish_reason`. Tokens are added up
across the retry-once attempts and stored on the row that owns the call:
`generations.input_tokens` / `output_tokens`, and the same pair on questions in
Phase 27. Cost is **never stored**. It's worked out when the page loads from a
`MODEL_PRICES` constant (per model, per 1M tokens in and out) and shown as an
estimate. Older rows have no token data, so they count as calls but show as
untracked. No backfill.

**Model per task.** `LLM_MODEL` (generate and refine, stays on Flash) and
`LLM_QA_MODEL` (questions, a Lite model with thinking at its minimum). The
adapter takes the model and max tokens per call.

**Limits** are counted with a `COUNT` over the rows (safe across both gunicorn
workers, no in-memory state) and exposed as add-on options:

| Option | Default |
|---|---|
| Generation jobs per user per day (generate, regenerate and refine all count) | 10 |
| Running generation jobs per user at once | 1 (moves today's per-session check to per-user in the DB) |
| Regenerates from one brief | 3 |
| @kitchen questions per user per day | 20 |
| Household model calls per day, all kinds | 40 |

Hitting a limit shows a calm explanation, never an error page. Outside the
app, also set a Google Cloud Billing budget alert (alerts only, it won't stop
spending) and, if you want a hard stop, a lower per-day request quota on the
API.

**`/usage` dashboard** (nav, under More). Today, the last 7 days and the last
30 days: calls, tokens and estimated cost by type (generate, regenerate,
refine, question) and by person; failures and truncations; how much of each
limit is left today. Household-wide visibility.

**Special request.** A nullable `generations.special_request` column, capped
server-side at about 280 characters (constant next to `COMMENT_MAX_CHARS`).
UI: on the review step between the brief recap and Generate. Label
"Anything in mind? (optional)". A two-row textarea whose placeholder example
is picked at random by the server. Three or four chips that add text when
tapped: *Something spicy*, *Keep it simple*, *Traditional*, *One pan*. The
typed text is kept in `sessionStorage` across trips into a suggestion card.
Prompt: the whole block, including the instruction on how to treat the
request, is emitted **only when a request exists**, so a brief with an empty
box stays byte-identical (`render_prompts.py` proves it). The request is
fenced in delimiters and labelled as the cook's steer on the dish; it never
overrides allergies or the output contract. Precedence: **allergy > must-use >
special request > dislike > diet preference > cuisine/seed**. When a request
is present, the creative seed is suppressed and recipe 2 becomes "a distinct
second take on the request". New golden briefs: two or three with requests,
plus one adversarial ("ignore the allergy").

## Phase 26 — Regenerate + refine + version trail

**Regenerate.** On the choose screen, *Neither — try again* opens a textarea
pre-filled with the original request. A new generation row with
`kind='regenerate'` and `parent_generation_id` is rebuilt from the parent row
with current stock, so it doesn't depend on the wizard session. The brief adds
a block, emitted only on regenerate: "The cook passed on these: X, Y. Go in a
clearly different direction." The generation gets a fresh seed. **History:**
unchosen generations currently appear as rows, so a regenerate chain must
collapse to a single row (the latest round), or every rejected round would
clutter the list. Capped by the regenerate limit.

**Refine** (AI recipes only). A *Refine this recipe* panel on the recipe page
with the prompt "What would you change?" and chips (*Make it spicier*,
*Simpler method*, *Use what I've got instead of the extras*, *Make this for N*).
It opens automatically when arriving from the choose screen and is collapsed
otherwise. It reuses the generation-as-job machinery (`kind='refine'`, source
recipe id, instruction; thread, poll page, stale guard, resolver after the
fact). The prompt reuses the sealed system prompt with an addendum asking for
**one** revised recipe, so the validator takes a count. Refine gets its own
golden set. **Supersede:** when it completes, the source recipe's
`was_chosen` flips to false, so the new version replaces it in History and
suggestions. Favourites and notes stay with the version they were made on.

**Version trail.** History is linear: only the latest version can be refined,
and older versions open read-only with a link to the latest. Above the title,
a strip reads Original → "make it spicier" → "simpler method", each step
labelled with its instruction and tappable to open that version. History shows
a "v3" badge.

## Phase 27 — Ask @kitchen

There's one comment box. Placeholder: "Add a note, or start with @kitchen to
ask a question". An *Ask @kitchen* chip inserts the prefix. The server decides
whether it's a question, and only when the text starts with "@kitchen"
(case-insensitive, prefix removed). Storage extends `recipe_comments`: `kind`
(`note` | `question`), nullable `answer`, `answer_status`, `answered_at`, and
the token pair. The answer lives on the same row as the question, so threading
needs no new column; the template shows it as an indented reply with the AI
pinwheel avatar (the frog chef later). Deleting the question deletes the reply.
A pending or failed answer shows that state with a retry button.

The call is synchronous with a hard timeout of about 30 seconds and a cap of
about 600 output tokens, on `LLM_QA_MODEL`. Context sent: the recipe at the
servings the user is viewing, the last two or three Q&As on this recipe, the
in-stock list by name, and **all active household members' allergies and
dislikes** (answers suggest substitutions). Plain text, UK units, short. It
politely declines anything that isn't about cooking this recipe. Only an
answer, never a rewrite (refine is the rewrite path). Not shown in the print
view, not fed into the brief or suggestions.
