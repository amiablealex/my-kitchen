# Changelog

## 0.9.0
- Recipe generation now runs in the background. Generating no longer holds the
  page open for the whole wait: the "Lets Cook" flow starts the job and shows a
  "cooking up your recipes…" page that updates itself and jumps to your two
  recipes the moment they're ready.
- Fixes generations timing out when cooking remotely (over the Nabu Casa cloud
  link) — the long wait no longer runs through the proxy in one request.
- A double-tap on "Generate recipes" now resumes the same wait instead of
  starting a second generation.
- If a generation gets stuck or takes too long, the page shows a clear message
  and a way to try again, rather than hanging.
- Additive migration: new nullable `generations.status` column; existing
  recipes and history are unaffected. The generation prompt is unchanged.

## 0.8.0
- Add a "meal type" selector to the Lets Cook wizard (Breakfast, Lunch, Dinner,
  Snack, Side dish, Dessert, Baking, Sauce or dressing). It sits on the cuisine
  step; the non-cuisine types (Dessert/Baking/Sauce or dressing) hide and omit cuisine.
- Meal type is a soft steer in the generation brief (Dinner stays the default and
  changes nothing) and is recorded on each generation.
- Additive migration: new nullable `generations.meal_type` column; existing rows unaffected.

## 0.7.4
- dummy version bump to test if data persists

## 0.7.3
- sidebar no longer requires user to be admin

## 0.7.2 
- Csrf fix

## 0.7.1
- Ingress and path handling

## 0.7.0
- Initial Home Assistant add-on packaging (pass 7b).
- Reuses the standalone container recipe; app fetched from `main` at build.
- Add-on options → env (LLM provider/model/key, temperature, max-tokens,
  recent-titles N, timezone, gunicorn sizing).
- SECRET_KEY generated once and persisted to /data (stable across restarts).
- First-run auto-seed: starter catalogue + one user with a generated password
  printed to the add-on log.
- SQLite DB persists in HA's /data (captured by HA backups).
