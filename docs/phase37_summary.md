# 0.37.0 — niceness pass

UX polish rather than new features. Plan: `plan_phase_37.md` in the Claude
project. One additive migration (`e8a3c51f2b94`, `recipes.source_note`).

- **Recipe form dock.** `recipe_form.html` puts *Cancel* + *Save* in a
  `.wizard-dock.form-dock`. `recipe_form.js` hides it while the on-screen
  keyboard is open: the visual viewport is 150px+ shorter than its tallest and
  a text field has focus (focus alone doesn't hide it). A `beforeunload` guard
  fires only once the form is dirty (input/change, or rows added, removed,
  reordered or relinked via a MutationObserver that ignores the shared picker
  moving) and never after a valid submit. Edit mode's back link and *Cancel*
  go to the recipe. The edit route already flashed "Recipe saved."
- **Photos.** Receipt sheet and recipe-from-photo have two inputs, one with
  `capture="environment"`. `receipt.js` binds both; *Another photo* returns to
  the pick step. `photo_import.js` binds every `.photo-pick`. The camera
  button reads *Take another* after the first page. Needs testing in the HA
  companion app, whose WebView decides whether `capture` opens the camera.
- **Source line.** `Recipe.provenance` → `(label, url)`: AI → "AI generated";
  else note → host → "from a photo" → None. The note replaces the host as link
  text; `source_url` is never edited. Pasted-text imports show nothing unless
  noted. "Where it's from" (≤ `SOURCE_NOTE_MAX_CHARS` = 80, whitespace
  collapsed) is on the form for create, import review and edit. The print view
  shows "From BBC Good Food (bbcgoodfood.com)" when a note replaces a host.
- **Stock marks.** `RecipeIngredient.stock_state` → have / need / unlinked /
  none, mirroring `suggestions.is_cookable` (staples in, retired out,
  optional extras never "need"). `_ingredients.stock_mark` renders it; the CSS
  draws the tick (the `check` icon), the dot and the dash. The link endpoints
  return `stock`, so `recipe_links.js` updates the mark with the pill. New
  `GET /cook/recipe/<id>/stock` → `{ri_id: state}`, read on `pageshow` when the
  page comes back from the back-forward cache.
- **Keep screen on.** `wake.js` + a `.wake-chip` in the first method heading
  (method headings are now `.section-head`). Screen Wake Lock API, secure
  context only; re-requested on `visibilitychange`; released on leaving. A
  refusal shows "Not available right now" briefly.
- **Seed categories** (fresh installs only): Meat / Fish / Beans & pulses /
  Other protein; Pasta / Bread / Grain / Other carb; Vegetable / Herb; Fruit /
  Dairy / Spice / Oil & vinegar / Condiment / Pantry / Baking, with
  `display_order` per section. Ingredient names are unchanged, so the eval
  fixtures and prompt renders are identical. Names stay globally unique (the
  receipt scanner maps categories by name); the clash message names the
  section and suggests "<name> <section>".
- **Icons:** `image`, `light_mode` added. **SW cache:** v29.

Tested on a throwaway DB (migrated with `flask db upgrade`, mock provider),
Playwright at 390px: marks for every state, provenance on the page and print
view, dock hide with a simulated keyboard, guard on Cancel and none on Save,
link/unlink returning `stock`, the stock endpoint, both clash messages, and
the photo page and receipt sheet. No JS errors. The wake lock is refused in
headless Chromium, so the on state was checked visually only.
