# Phase 34 — recipe import (0.34.0)

Fourth of the input-side arc (`plan_phases_31-36.md`). One additive
migration; a new, separate prompt (the sealed generation prompt is untouched).

## Flow
*Create a recipe* shows one quiet line, "Got it on a website? Import it →"
(no new button on the Recipes header). `wizard.recipe_import` (GET/POST,
`recipe_import.html`): a URL, or a fold-out to paste text. The submit button
reads "Reading the recipe…" while it works. Success renders the **create form
in `import` mode** as the review step; nothing is saved until *Save recipe*.
Problems flash a calm message and keep what was typed.

## Reading (`llm/importer.py`)
- `fetch_page`: http(s) only, browser-like User-Agent, 15 s, 3 MB cap.
  HTTP errors and unreachable hosts become `ImportProblem` messages that point
  at pasting the text.
- `extract_recipe_jsonld`: every `application/ld+json` block, searched
  through lists, `@graph`, `mainEntity` and `itemListElement` for a `Recipe`
  (also as one of several `@type`s) with ingredients. Trimmed to name,
  description, yield, times, category, cuisine, ingredients and instructions;
  `HowToSection` names become `[Section]` lines. HTML entities and tags in
  values are cleaned.
- No JSON-LD → `page_text`: scripts, styles and page furniture dropped,
  capped at 12k characters. Pasted text is sent as-is (min 40 characters).
- `restructure`: one call on the @kitchen model list (`qa_models`: the Lite
  model, falling back to the main model), JSON mode, temperature 0.2,
  thinking low. "Restructure, don't rewrite": source wording and quantities
  kept; only US measures and °F converted; ingredient section headings
  skipped; method `[Section]` lines inform step titles rather than becoming
  steps; tips only from the source. Picks meal type, cuisine and time band
  from the app's lists. `{"error": "not_a_recipe"}` → a calm message.
  `_validate` reuses `schema._normalize_step`, requires a title, ingredients
  and a method, and moves an all-prep method into cook.
- Each ingredient's `item` (the source wording without amount/unit) is run
  through the resolver for a catalogue link.
- One `AiCall` row per attempt, kind `import`. Imports count only towards
  the household cap (`import_blocked_reason`), not the per-person receipt
  limit (`READ_KINDS`).

## The form, for imports
- `_parse_ingredient_lines(imported=True)` keeps each line's own wording
  (`ing-{i}-raw`) as `raw_text` and allows a line with no link. Hand-made
  recipes are unchanged: every line linked, raw_text the catalogue name,
  any posted raw ignored.
- `recipe_form.js`: a hidden raw field per row. An unlinked imported line
  shows its wording (italic, muted) as the label; a linked one shows the
  wording in small text under the link when it differs. Picking a link by
  hand clears the wording, so old text can't sit under a different
  ingredient. The submit guard accepts unlinked wording on imports.
- `_save_recipe_from_form(recipe, source, source_url)`: creates
  `source='imported'` with `source_url` (http(s) only, else NULL). Imported
  recipes are editable like hand-made ones (`recipe_edit` allows both);
  their prefill carries `raw`.

## Display
`recipes.source_url` (migration `c4e9a1d07b52`) and `Recipe.source_host`.
The recipe page's meta line ends with "from bbcgoodfood.com" (a link); the
print view shows "From bbcgoodfood.com". A `urlhost` template filter does
the same for the import note. The orange source dot was already reserved for
imports.

## Recipes list
`history.index` now lists `source='imported'` recipes alongside hand-made
ones, in their own "Imported" group (orange, `.recipe-group--imported`,
already styled; Favourites already grouped them). Rows carry
`kind=r.source`, and `_row_recipes` treats `imported` like `user`. *Edit
recipe* in the recipe page's ⋯ menu shows for imported recipes too.

## Mock
"RECIPE IMPORTER" → `_mock_import`: echoes the JSON-LD's name, ingredients
and steps (amounts not split), or a fixed recipe.

`sw.js` cache → v20.
