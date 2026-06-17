## MVP — "Prove the Loop": Complete
The full MVP loop specified in §8 is built, running on the Pi, and committed. Every item in the agreed MVP scope is delivered:

- Stock list — ingredients grouped by category, fast in/out toggle, inline per-ingredient notes, persisting to SQLite. Seeded with placeholder data (1 user, 7 categories, 23 ingredients) via flask seed.
- Lets Cook wizard — all five steps (stock check → core ingredients into Protein/Carb/Veg/Other lanes → cuisine → time band → servings), state carried through the Flask session, with a review screen before generation.
- Generation engine — one LLM call returning two distinct recipes as structured JSON, validated server-side against the §5.2 contract with one retry on malformed output. Provider adapter with mock / Anthropic / Gemini behind one interface; mock returns canned JSON for offline testing. Mock and live Gemini both confirmed working.
- Choice → display — two-title choice screen, four-section recipe display (title, ingredients with "to buy" flags, prep, cook with timers).
- Persistence & history — every generation and both recipes saved; date-ordered history list handling chosen / unchosen / failed states.

Built incrementally across six checkpoints, each runnable and committed. Single user, no auth, deliberately unstyled — all as scoped.
Future-proofing baked in from the start (per the brief): all internal links via url_for(), relative asset paths, ProxyFix for sub-path/HA-ingress serving, DB path and port via env vars, binds 0.0.0.0. The full §3 schema (including Phase 1–2 tables) was built now, so later phases need no migration. README updated to current state.

## Things we learned that weren't in the original scope

1. Double-submit guard (implemented). The slow LLM call meant users clicked "Generate" again when nothing appeared to happen, firing duplicate API calls, duplicate generation rows, and stalling both gunicorn workers at once. Added a client-side guard that disables the button on submit. This is a 90% fix; a server-side idempotency check is the more robust version, still outstanding.
1. Synchronous generation has a ceiling — roadmap needs a background-worker phase (NOT yet implemented). The biggest architectural finding. Generation blocks the request for 15–60s+, which causes: gunicorn worker timeouts (its default 30s timeout kills the worker mid-call — must run with --timeout 120), apparent "hangs" under the single-threaded dev server, and the double-submit pileup above. The proper fix is making generation asynchronous — fire the LLM call as a background job, return immediately, poll/stream the result. This eliminates worker timeouts, enables real progress indication, and makes double-submit structurally impossible. Recommend adding this as an explicit roadmap phase; it's the main technical debt to clear before this ever faces real concurrency. (Fine as-is for two people on a LAN.)
1. gunicorn --timeout is mandatory, not optional — direct consequence of the above, worth pinning in the deployment notes and the eventual Phase 4 systemd config.
1. No migrations is a known, accepted tradeoff. create_all only; adding a model column requires flask seed --reset (wipes data) or a manual ALTER TABLE. Fine through the MVP, but real migrations (Alembic) will be needed once the schema changes against data worth keeping — likely around Phase 1.
1. Minor deferred polish (noted, not blocking): timestamps display in UTC (an hour off BST); local-time formatting is trivial Phase 3 work.

## Suggested roadmap adjustment
The spec's phases (1: accounts + dietary/allergy + favourites; 2: equipment + configurable categories + prompt sophistication; 3: restyle; 4: Docker) still hold. The one addition: insert an async-generation / background-worker phase before any real concurrency push — pairs naturally with Phase 4 (deployment/robustness) or stands alone. Alembic migrations likely want slotting in around Phase 1.
One small flag for your tracker's accuracy: the double-submit guard was the only change folded in outside a formal checkpoint (it went into your next commit rather than its own), so the server-side idempotency follow-up is easy to lose track of — worth a line item.

2026-06-17
