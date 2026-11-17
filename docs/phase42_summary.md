# 0.42.0 — versions of hand-made and imported recipes

No migration. Built on 0.41.0.

- **Refine on any source.** `recipe_refine` and the recipe page's
  `can_refine` no longer need a generation: any live recipe can get a new
  version. Versions stay AI-only by design; *Edit recipe* remains the
  in-place correction for user and imported recipes (an edit to v1 changes
  what v2's what-changed line compares against, which is fine). The route's
  time label no longer dereferences `recipe.generation`.
- **`start_refine` without a generation.** The brief's state comes from the
  recipe's own tags (meal type, cuisine, time band, servings), must-use
  empty, and `cooking_for_user_ids` = every active household member (the
  set @kitchen already uses). After `build_brief`, diet preferences are
  dropped. The refine Generation stores those ids, so v2's allergy note
  works through the existing `combined_dietary` path.
- **Prompt.** `build_refine_prompt(..., household_recipe=False)`. When set,
  one block after the dietary lines: the lists are the household's, and for
  this recipe they only stop additions (ingredient, extra, serving
  suggestion, substitute); anything already there stays unless the change
  request asks. It replaces the allergy and dislike rules for that recipe
  only. AI recipes' prompts are byte-identical (`render_prompts.py`: no
  removed lines). Two new goldens: `refine_household_keeps_existing`
  (imported satay, peanut allergy, "make this for 4": peanuts stay) and
  `refine_household_never_adds` (hand-made traybake, mushroom dislike,
  "make it more filling": no mushrooms). **Run `flask eval-recipes`** before
  deploying.
- **Provenance.** The refine job copies `source_url` and `source_note` to the
  new version. `Recipe.provenance` for an AI recipe with either: "AI version
  of a recipe from <note or host>", linked to the original URL; otherwise
  "AI generated" as before. The print view picks this up unchanged.
- **History.** Hand-made and imported rows are skipped when they're a
  hidden (non-main) version, so a refined import shows once, as its main
  version. A family row whose original isn't AI carries `also_sources`, so
  the Source filter matches both *AI* and the original's *Imported* / *By
  hand*.

Tested on a throwaway DB with the mock provider: an imported recipe and a
hand-made one each refined; the household block and cooking-for ids in the
raw prompt (and absent from an AI recipe's refine); provenance with and
without a URL; History showing only v2 with both source facets; removing v2
brings the imported original's row back; print view renders. The 0.41.0
smoke run still passes.
