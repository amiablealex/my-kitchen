# 0.41.0 — branching versions, stock-aware refine, removing versions

No migration. Built on 0.40.1.

- **Families (`my_kitchen/versions.py`, new).** The refine generations'
  `source_recipe_id` already described a tree; this module reads it (one
  query over refine generations) and is the single answer to "which versions
  does this recipe have" for the trail, History, the Archive page,
  suggestions and the home page. `Family`: members in creation order,
  `number` (v1 = original, never renumbered, removed versions keep theirs),
  `main` (newest live version, None when the family is archived),
  `removable()` (live, not the original, nothing live made from it),
  `trail()` (rows + where *New version* goes). `reseat_main()` keeps
  `was_chosen` in step: in a family of more than one, only the main version
  is chosen; a family of one is left to the choice screen. It runs after a
  refine finishes (in the job thread, replacing the old "source loses
  was_chosen"), on remove, archive and restore (recipe page and History
  swipe/undo). `recipe_versions()` in `llm/service.py` is gone.
- **Branching.** `recipe_refine` no longer requires the newest version; any
  live AI version can be refined. The trail renders rows: the first runs from
  the original along each version's first child, every other child starts a
  row marked "↳ from vN". Visible: live versions, plus the one being viewed
  and its ancestors. On a version with a live child, *+ New version* sits on
  its own branch row ("New version from vN"). The older-version notice is now
  "This is v2. The newest is v3." with *Go to v3*. @kitchen's *Make this
  version N* appears on any live version, numbered family-wide.
- **Stick to what's in stock.** Checkbox `use_stock` on the refine form,
  ticked by default (unticked sends nothing). `start_refine(...,
  stick_to_stock)`. Prompt (`REFINE_ADDENDUM`, sealed-prompt change): what's
  already in the recipe stays allowed when out of stock, with its `to_buy`
  as it was, unless the request asks to drop it or to work with stock; the
  "cookable from AVAILABLE and STAPLES alone" rule applies to additions; an
  ingredient the request names outright may be used out of stock and may be
  central, with `to_buy` false. Ticked: `build_refine_prompt` adds one line
  naming the source's required, linked lines that aren't in stock
  ("…not in stock right now: chorizo. Keep it unless…"), only when there are
  some. Unticked: the AVAILABLE list is left out (`_staples_equipment_lines`
  split from `_pantry_lines`, whose output is unchanged) and a FREE REIN
  block overrides the cookable and extras rules, with every `to_buy` false.
  Chip *No extras — use what I've got* → *Make it work with what I've got*.
  `render_prompts.py`: every existing golden and spot check is byte-identical;
  the new refine goldens are additions. Four new refine goldens
  (`refine_keeps_missing`, `refine_named_not_in_stock`,
  `refine_work_with_what_ive_got`, `refine_free_rein`); goldens accept
  `stick_to_stock` and `missing`. **Run `flask eval-recipes` against the real
  provider before deploying** (the refine system prompt changed).
- **Remove a version.** `POST /cook/recipe/<id>/remove-version`: archive
  semantics, only when `removable`, re-seats main, lands on the parent.
  `recipe_archive` archives the whole family (menu: *Archive recipe (all N
  versions)*, behind the shared confirm). `recipe_restore`: a fully archived
  family comes back whole; otherwise the version plus any archived ancestors.
  History swipe-archive on a family row takes the family; undo restores and
  re-seats. Archive page: a fully archived family is one row ("all 3
  versions", newest member); a version removed on its own is its own row with
  a v-badge. Fixes: archiving the newest version used to hide the whole
  recipe, because older versions stayed hidden as refined sources.
- **History.** `_lineage_context` now hides every family member that isn't
  main (`hidden_versions`); a pair row is hidden only when it has a hidden
  version and no chosen recipe, so refining the *unpicked* recipe of a pair no
  longer hides the pick. The v-badge is the family number.
- **What changed.** `versions.version_changes(parent, child)`: added /
  dropped by catalogue link (or normalised text for unlinked lines), "(not in
  stock)" on added linked lines that aren't satisfied, servings change, else
  "Same ingredients." Computed on page load (the parent always exists:
  removal is end-of-branch only). Shown under the blurb as "From vN, you
  asked: “…”" plus the sentence; the original keeps "You asked for".
- **@kitchen nudge.** `refine.js`: plain text rules (ends with "?", starts
  with a question word, or contains swap phrasing such as "instead of",
  "swap", "replace", "don't have"). When they match, the confirm dialog shows
  its @kitchen face: *Ask @kitchen* posts `@kitchen <text>` through a hidden
  form to `recipe_comment_add` (requestSubmit, so notes.js fills the viewed
  servings), *Make vN anyway* carries on. Skipped for text set by
  `mkRefine` (servings rewrite, @kitchen's *Make this version N*) until the
  user edits it, and when no questions are left today.
- **Suggestions.** Provenance now includes every family member;
  `one_per_family` keeps one card per recipe (main if it qualifies, else the
  newest qualifying version), applied before the limit, in both
  `suggest_recipes` and `cookable_now`. `version_badges` → "v2" on a card
  that isn't the main version. `Recipe.suggestable` and the History
  "unlinked" filter count every family member.
- **SW cache** v33.

Tested on a throwaway DB with the mock provider: refine from v1 twice (one
ticked, one unticked: FREE REIN in the raw prompt, no AVAILABLE), main and
`was_chosen` after each step, trail rows and branch slot, notices, History
showing only the main version, remove v3 → v2 main, original not removable,
remove v2 → v1 main and its pair row back, restore v3, family archive and the
Archive page's single row, restore from any member, History swipe-archive and
undo, `one_per_family` and badges, and the what-changed sentences on hand-built
lines. Not looked at on a phone yet.
