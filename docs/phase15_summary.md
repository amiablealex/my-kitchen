# Phase 15 — 4a: universal recipe-ingredient display + link editor (summary)

**Status: shipped to production.** Bumped to **0.11.0** and merged to `main`. This
is roadmap item 4 split into 4a (this phase: the source-agnostic display + link
editor on existing recipes) and 4b (next: create-a-recipe-from-scratch authoring,
which reuses 4a's picker + add-to-catalogue flow). It completes the keystone's
deferred review-UI half: the catalogue links the resolver has been writing since
Phase 14 are now **visible and editable** on every recipe — "AI proposes → server
verifies → human reviews", finally with the human review step in place.

**No schema change.** `recipe_ingredients` already existed; 4a only reads the rows
and updates `ingredient_id`. No migration, so the version bump carried no schema
risk.

## What shipped

**Display switch (CP1)** — `templates/wizard/recipe.html` Ingredients section now
renders from the structured `recipe.ingredients` (ordered `RecipeIngredient` rows)
instead of `ingredients_json`. The freetext line is byte-identical to before
(`{amount} {unit} {raw_text}`; confirmed `raw_text == item` and amount/unit are the
verbatim JSON values from the Phase 14 write path, so no double-render). Each line
gains a calm trailing **pill**: the linked catalogue ingredient's name on a filled
`--surface-2` chip, or a muted dashed-italic **"not linked"** chip when
`ingredient_id` is null. The `(you may need to buy)` `to_buy` marker is unchanged
and stays **read-only** (editing `to_buy` is deferred to the suggestions phase).
**Legacy fallback:** a row-less recipe (`recipe.ingredients` empty) still renders
from `ingredients_json` exactly as before — no pills, no editor. Production has
rows on everything (rebuilt at 0.10.0), so the fallback is insurance.

**Edit mode (CP2/CP3)** — an "Edit links" toggle on the Ingredients section header
flips it into edit mode (`is-editing` class), revealing a compact per-row edit
button. Clicking a row's button opens a **single shared editor panel**, moved
inline under that row (appended into the `<li>`, so markup stays valid and the read
view is untouched when closed). The editor is unified, mirroring the stock editor's
search-or-add pattern:
- **Re-link** — a search box filters the catalogue **client-side** (the catalogue
  is injected once as JSON; ~175 items, no per-keystroke fetch, trivially
  ingress-safe). Matching ingredients render as pick buttons; clicking one links
  the row. The currently-linked item shows as disabled "(linked)".
- **Unlink** — shown only when the row is currently linked; nulls `ingredient_id`.
- **Add & link** — a `<details>` form (name prefilled from `raw_text`, category
  select, staple checkbox) creates a new catalogue ingredient **and** links the row
  in one action.

Updates are applied in place on success (the pill text/state is swapped by JS); no
page reload. The new ingredient is also pushed into the in-memory catalogue so a
later search in the same session finds it.

## Endpoint shapes (new, on `wizard_bp`, recipe-scoped, CSRF via X-CSRFToken)

- `POST /cook/recipe/<recipe_id>/ingredient/<ri_id>/link`
  body `ingredient_id=<id>` → link (validates the id is an **active** catalogue
  ingredient; rejects missing/retired with `400 {error:"invalid"}`);
  body `ingredient_id=` (empty/absent) → unlink (`ingredient_id = NULL`).
  Success → `{ri_id, ingredient_id, name}` (name null on unlink).
- `POST /cook/recipe/<recipe_id>/ingredient/<ri_id>/add-and-link`
  body `name / category_id / is_staple` → create `Ingredient(in_stock=False,
  is_active=True)` + link. Success → `{ri_id, ingredient_id, name}`.
  Name collision (case-insensitive) → `400 {error:"exists", message: "...search
  above to link it."}` — **faithful to manage**, not a silent link-to-existing.
- Both guard via `_recipe_ingredient_or_404(recipe_id, ri_id)` — a `ri_id` from
  another recipe **404s** rather than being editable through a mismatched URL.
- All endpoint URLs are built with `url_for` and injected into the row via `data-*`
  attributes; the JS never constructs a path (HA ingress / `SCRIPT_NAME` safety).

## Reuse (no drift)
`add-and-link` calls manage's **`_parse_ingredient_form` + `_name_taken`** directly
(verified at runtime: `wizard.routes._parse_ingredient_form is
manage.routes._parse_ingredient_form`). One-way import (`manage.routes` doesn't
import wizard), so no cycle — confirmed by booting `create_app()`.

## Guardrails honoured
- No schema change; `ingredients_json` still written by generation and untouched
  (it's just no longer the display source for recipes that have rows).
- **Linking is explicit, never magic:** a manual link/unlink is authoritative;
  adding a new ingredient triggers **no** background re-resolution of other rows —
  only the acted-on row changes. No batch/re-resolve sweep exists.
- **Shared, not per-user:** link edits mutate `RecipeIngredient.ingredient_id`
  globally — any household member's correction applies for everyone. No join table.
- Resolver, its golden fixture, the generation prompt/brief/service, and
  `ingredients_json` writing all untouched. **`flask resolve-eval` still 28/28,
  zero false links, 6/6 traps hold.**
- Picker lists **active** ingredients only (incl. staples, excl. retired); new
  ingredients default `in_stock=False`.
- Stock stays a binary toggle.

## Verified (dev, full test-client matrix)
Recipe GET 200 with linked + unlinked pills, editor, toggle, ingress-safe URLs,
catalogue JSON, retired excluded; link persists + DB updated; unlink nulls;
link→retired rejected; bad id rejected; add-and-link creates
(`in_stock=False, is_active=True`, staple flag honoured) + links; case-insensitive
dup rejected; cross-recipe ri → 404; resolve-eval 28/28 PASS.

## What 4b inherits
- **The ingredient picker** (client-side catalogue search → pick) and the
  **add-to-catalogue-and-link** flow — 4b's from-scratch authoring form reuses both
  to build a recipe's ingredient lines pre-linked, bypassing the resolver.
- The reused `manage` helpers as the shared ingredient-creation path.
- **Latent guard for 4b (flagged, not fixed here):** the recipe view and
  `toggle_favourite` deref `recipe.generation.cooking_for_user_ids` /
  `recipe.generation.recipes`. AI recipes always have a generation, so 4a is safe,
  but user-created recipes (`generation_id` NULL) will need a null guard there.
