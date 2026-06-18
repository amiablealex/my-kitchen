## Roadmap - Accounts & security foundation
All five scoped deliverables for this pass are built, tested on the Pi, and committed across five runnable checkpoints. Application-code only — no migration was needed at any point, confirming the forward note from the catalogue summary that the Phase 2 auth fields were already in the baseline. Deliberately unstyled, single trust-tier, as scoped.

- App-wide CSRF (Flask-WTF CSRFProtect) — closes the deliberate Phase 1 carry-over. Hidden tokens on every existing form (all manage + wizard forms) and all new forms; the stock-list AJAX (toggle/note) carries its token via an X-CSRFToken header sourced from a <meta> tag in base.html.
- Authentication (Flask-Login + Werkzeug hashing) — login (by case-insensitive name + password, with an open-redirect-guarded next), POST logout, and an app-wide login gate via before_app_request (public surface = login view, /healthz, static only — so individual views need no @login_required). No public/self-registration.
- Password CLI — flask set-password <name> (hidden interactive prompt or --password; the first-login bootstrap and the reset path) and flask create-user <name> (idempotent get-or-create, never clobbers). Existing seed left intact.
- "My Kitchen" users area — new users blueprint: list, add, edit/rename, set-password, retire/reactivate. Users are retire-only (see learning 5).
- Generation attribution — wizard now records current_user.id (the default_user_id() single-user fallback is removed); History surfaces "cooked by …"; all pre-auth rows preserved and correctly attributed via the CP4 rename.

## Things learned along the way (not accounted for in scope)

1. The AJAX endpoints were the non-obvious CSRF surface. Form tokens are mechanical; the stock toggle/note fetch calls would have silently started 400ing. Handled via the meta-tag + X-CSRFToken header pattern — the reusable approach for any future JS-driven POST.
1. CSRF token expiry vs an always-on tablet. The default WTF_CSRF_TIME_LIMIT (1 hour) would reject toggles on a stock page left open in the kitchen. Set to None (session-scoped, not time-scoped). General principle for the tablet use case.
1. SECRET_KEY is now load-bearing, not cosmetic — the one operational must-do. Pre-auth it didn't matter; now the dev-only-change-me default invalidates sessions and CSRF tokens on every restart (logs everyone out and would make the new "form expired" path fire constantly). A stable SECRET_KEY env var must be set on the Pi before daily use.
1. Self-retire / household-lockout edge case. is_active doubles as "retired" and "can't log in," and the gate force-logs-out an inactive user mid-session — so a user retiring themselves (or the last active user) could lock the household out. Self-retire is blocked in both the UI and the route. Bears watching when the next pass touches the same user records.
1. Soft-delete is mandatory for users, not just preferred. Like the category FK guard last phase: generations.created_by_user_id means hard-deleting a user breaks history attribution. There is deliberately no hard-delete path for users at all (unlike ingredients, which kept one).
1. Case-insensitive name handling has to be consistent in three places — login lookup, CLI lookup, and the in-app duplicate guard — all aligned on db.func.lower, or "Home Cook" / "home cook" could diverge between creation and login.
1. Rename-don't-recreate was a load-bearing small decision. Renaming the seeded "Home Cook" → real name (rather than creating a fresh user) keeps every existing created_by_user_id pointing at the right person, since the link is by id. Invisible once done, but the other path would have silently split history.

Forward notes

- Next pass (second half of roadmap Phase 2): dietary/allergy tags managed + assigned to users + wired into the prompt (hard allergies vs soft preferences), the wizard "cooking for" upgrade (user-profile select + guests), favourites, and history filter-by-user. Schema already exists (dietary_tags, user_dietary_tags, recipes.is_favourite) → application-code only, no migration, per the standing baseline note.
- Deferred deliberately: "remember me" persistence (session cookie is fine for a tablet). Still open from earlier roadmap notes and untouched here: server-side idempotency / async generation (Phase 5) and local-time display / UTC→BST (Phase 4) — History still renders UTC.
- Behaviour worth recording: the friendly CSRF handler bounces form failures to the login page (a stale token almost always means a dead session) and returns a JSON 400 to the AJAX path. Revisit only if some future form failure shouldn't route to login.
- No roles/permissions: any logged-in household member can manage users and everything else — fine for the two-person trust model, but flag if that assumption ever changes.

2026-06-18
