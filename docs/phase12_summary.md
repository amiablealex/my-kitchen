# Phase 12 — Async generation

**Status:** ✅ Done. Production-roadmap §5.2. Generation moved off the synchronous
request onto a background thread; the wizard now starts a job and a polling page
redirects to the choice screen when it finishes. Built CP1→CP3 on the dev Pi,
each checkpoint tested before commit. One additive migration; the tuned
generation prompt left **completely sealed** — this was plumbing only, no change
to the prompt, the brief, or any generation logic.

**Headline acceptance test passed:** a generation triggered over the remote Nabu
Casa cloud URL completes via polling with no proxy timeout — the real driver for
the whole phase.

## Architecture (as built)

- **The `Generation` row *is* the job.** A single nullable `status` column
  ("running" | "done" | "error") tracks it. **No separate jobs table.**
- **One `threading.Thread(daemon=True)` per generation.** No pool, no queue, no
  Celery/RQ, no separate worker process.
- **Coordination goes through the DB, never memory.** gunicorn runs 2 worker
  processes (gthread, 2×4). The background thread lives in *one* worker's memory,
  but a poll request can land on the *other* worker — so job state lives in the
  row, and the thread/poll re-query by `generation_id`. No in-memory dict, no
  thread handle shared across requests.

## What landed

- **`generations.status`** — nullable `String`; one additive Alembic migration
  (`f3c9a72b4e10`, batch mode). Existing rows backfill to NULL. **NULL means
  legacy/complete**, so every status branch treats NULL as "done" — historical
  generations still render in history and `/choice`.
- **`run_generation` split into two** (`llm/service.py`):
  - **`start_generation(app, wizard_state, time_label, user_id)`** — the
    synchronous starter, runs *in the request*. Does only fast, reliable work:
    `build_brief` (DB reads) + `build_user_prompt` (string assembly), creates the
    `Generation` row as `status="running"` with `raw_prompt` stored, commits
    (assigning `id` and making the running row visible to polls), spawns the
    daemon thread, returns `generation_id`.
  - **`_run_generation_job(app, generation_id, user_prompt, brief)`** — the thread
    body, runs *outside any request*. Pushes its own app context, uses a fresh
    `db.session`, re-queries the row by id, runs only the slow/fallible part
    (provider call → the retry-once-on-malformed-JSON loop → validate/normalize →
    write the two `Recipe` rows), sets `status`. Cleans up the session in a
    `finally` (`db.session.remove()`).
- **Thread signature is `(app, generation_id, user_prompt, brief)`** — primitives
  only across the boundary. `SYSTEM_PROMPT` is imported directly. **The brief is
  built once in the starter and passed in** — rebuilding it in the thread would
  re-roll `pick_seed()` and re-read stock, so the stored `creative_seed` wouldn't
  match what was used. `brief` is a plain-data dict (names/notes/lists), no ORM.
- **`app` captured via `current_app._get_current_object()`** in `/generate` and
  passed to the thread for its app-context push. The thread never touches
  `current_app`, `request`, or the Flask session.
- **New wizard routes:**
  - **`/generating/<id>`** — renders the wait page (relocated from the old
    review overlay). Short-circuits to `/choice` if already done (incl. legacy
    NULL). Injects the `url_for`-built **status URL** into the template.
  - **`/status/<id>`** (JSON) — returns `{status, redirect_url, error}`.
    `redirect_url` is a server-side `url_for('wizard.choice', …)` (ingress-safe).
    Carries the **stale-job guard**.
- **Stale-job guard.** A still-"running" row older than **5 minutes** is flipped
  to `status="error"` *in the poll* (no reaper process) and **persisted** — so
  history stays clean and the idempotency check sees it as not-running. A zombie
  thread that finishes later is harmless (last-writes "done" with two real
  recipes). The rule lives in one shared `_is_stale(gen)` helper used by both the
  poll and the idempotency guard, so it can't drift.
- **`/generate` rewired:** keeps the synchronous pre-flight servings guard
  (`derived_servings < 1` → flash + redirect) *before* creating any row, then
  starts the job and redirects to `/generating`.
- **Session idempotency.** The new `generation_id` is stashed in the session; a
  re-POST to `/generate` while that generation is still `running` and not stale
  redirects to its existing wait page instead of starting a second run. A
  finished/failed/stale active generation falls through to a fresh start (and the
  stash updates). Combined with the disable-on-submit button, a double-click
  resumes the same wait — one generation.
- **Generating page UX:** polls every 2s; friendly "cooking up your recipes…"
  state; navigates to `redirect_url` on done; shows the error + a "back to review"
  retry on error; after ~120s still running, swaps to a "taking longer than usual
  — still cooking" reassurance and **keeps polling** (the server's 5-min stale
  guard is the real backstop; retry only appears on a terminal error). Plain
  `fetch()` to the `url_for`-injected status URL — never a hardcoded path.
- **Review overlay relocated.** `review.html` lost the full-screen wait overlay
  (it now lives on the generating page) and keeps only the disable-on-submit
  guard. A small `.gen-page` centering wrapper added to `app.css`; the old
  `.gen-overlay` rule is now unused (left in place, commented, to keep the blast
  radius small — a candidate for a later cleanup).

## Verified

- **CP1 (headless, dev Pi + local harness):** migration applies base→head; a real
  generation polls `running → done` with 2 recipes saved and `/choice` rendering;
  a forced provider failure (`LLM_PROVIDER=bogus`) → `status="error"` + `gen.error`
  surfaced on the page; a legacy NULL-status row still renders in history/choice.
  Real Gemini round-trip returned two recipes; logs showed the 2s polling.
- **CP2 (over HA ingress):** full click→generating→auto-redirect-to-choice flow;
  **double-click Generate resumes the same wait — one generation in history**;
  the status fetches resolve under the ingress sub-path (the `url_for` injection
  works through the relay); 120s reassurance copy confirmed.
- **CP3:** stale guard triggers live (backdated a running row's `created_at` →
  poll flips it to error → UI shows retry); **headline remote test passed**
  (generation over the Nabu Casa cloud URL completes via polling, no proxy
  timeout); `flask eval-recipes` green as a provider-plumbing smoke check.
- **Prompt path sealed throughout:** `python -m my_kitchen.eval.render_prompts`
  byte-identical to the pre-refactor baseline at every checkpoint. (The eval
  harness imports only from `llm.prompt`, never `service.py`, so the refactor
  literally cannot move a rendered byte — but the diff was run anyway as the gate.)

## Surprises / catches

- **The `created_at` clock trap (the one real landmine).** `models.utcnow()`
  writes a timezone-**aware** UTC datetime, but SQLite + SQLAlchemy `DateTime`
  (no `timezone=True`) hands it back **naive** (UTC wall-clock) on re-query — and
  the stale guard always reads a *re-queried* row (thread + poll). A naive blanket
  `datetime.utcnow()` comparison happens to work today, but to be robust either
  way, `_generation_age_seconds` branches on `created.tzinfo`: naive → compare
  against naive UTC now; aware → compare against aware UTC now. Same trap the
  existing `localdt` filter already worked around. **Lesson: a stored datetime's
  awareness is not the same as the awareness you wrote — re-read it and check.**
- **WAL + `busy_timeout=5000` were already set** (an `Engine` "connect" listener
  in `extensions.py`) and apply to the thread's fresh connection too. So the
  thread-writer / poll-reader concurrency is handled for free — no SQLITE_BUSY
  under normal use, two concurrent generations (two users) just write two rows.
  Nothing to add; worth knowing it's load-bearing for this phase.
- **`get_provider` moved into the thread** (a build decision). Provider
  construction is fallible (missing key → `ProviderError`); the brief wants the
  thread to own the fallible LLM path, so the starter stays pure DB-write + spawn
  and a bad-key/bad-provider error now surfaces via the poll page rather than
  synchronously. `gen.model` is set inside the thread, mirroring the old
  success/failure values. Consequence: `error.html` is now effectively unused by
  `/generate` (kept in place; harmless) — async errors surface on the generating
  page.
- **Single commit for recipes + `status="done"`.** They land in one commit so a
  poll on the *other* worker never sees "done" before the recipes exist.
- **The stale guard doubles as worker-death recovery.** If a gunicorn worker is
  killed mid-generation its daemon thread dies with it, orphaning the row at
  "running". Because the poll lands on the *other* worker and reads the DB, the
  next poll past 5 minutes flips it to error → retry. This is exactly why
  coordination goes through the row, not memory.

## Doc updates to fold in (for the orchestrator)

- **`recipe-app-spec.md`:**
  - §3 `generations` table — add `status` (text, nullable; "running" | "done" |
    "error"; NULL = legacy/complete, treated as done on read). Added Phase 12.
  - §4 wizard — step 5 "Generate" now builds the brief, creates the running row,
    spawns a background thread and redirects to a **generating/poll page**; step 6
    "Choose" is reached via the poll's redirect when status flips to done. Note the
    session idempotency (a double-submit resumes the same wait).
  - §5 generation engine — generation runs on a background daemon thread keyed off
    the `Generation` row's `status`; the retry-once loop now lives inside the
    thread body.
  - §8 build phases — **Phase 6 (async) is now delivered** as production-iteration
    Phase 12 (was "deferred behind Phase 7 by decision"). Update the **Operational
    notes**: the synchronous 15–60s request block is gone; `/generate` returns
    fast, so the gunicorn `--timeout 120` no longer governs generation (kept as
    headroom). The "main technical debt" / remote-timeout risk is **cleared**.
  - §9 assumptions — the "synchronous generation blocks the request" assumption is
    superseded.
- **`production-roadmap.md`:**
  - §4 Foundational — mark **Async generation** done.
  - §5 sequenced phases — mark **2. Async generation** done (`phase12_summary.md`);
    note photo ingestion's async prerequisite is now satisfied.

## Deferred / unchanged

- **Keystone (structured-ingredient resolver)** is next (§5.3) — the big migration.
- **Photo ingestion** still later; its async prerequisite is now in place.
- No streaming/SSE, no progress percentage, no queue/worker process, no thread
  pool — deliberately, per scope. One daemon thread per generation.
- The unused `.gen-overlay` CSS rule is a candidate for a future cleanup.

## Release

Shipped as add-on **0.9.0** (minor bump: feature + additive migration). `/data`
backed up before the schema-changing release; the migration auto-applies on
update via the entrypoint (additive/backward-safe). Tested off `main`, then
merged to `main` for HA to detect and install.

2026-06-26
