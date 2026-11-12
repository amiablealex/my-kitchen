# 0.36.2 — one recipe list, the filter panel, the unlinked note

Fix release after the input-side arc. No schema change.

## Recipes and Favourites: one list
The source groups are gone. Both pages are one newest-first list in a single
plain card (`.recipe-group--all`, kept so `recipe_archive.js`'s recount and
select-all still work; *Select all* now sits above the list in select mode).
Rows (`history/_rows.html`): `row_title` = source dot + title; `row_meta` =
meal · cuisine · cook name · `relday` (today / yesterday / "3 Nov") ·
Quick/Relaxed. Servings and the initial mark are dropped. The "Pick one" pair
and failed-generation rows stay, in date order. New `relday` template filter.

## The search box is the organiser
`filter_box()` macro + rewritten `recipe_facets.js`. Focusing the box opens
`#facet-panel` attached under it (same teal ring): every value that occurs, in
groups Made by / Meal / Cuisine / Cook, ordered by `_FacetOptions.ORDER` (source
hand → imported → AI; meal and cuisine in the app's orders; cook A–Z). Source
labels are now "By hand" / "Imported" / "AI", with their dots. Typing narrows
the panel and filters titles; picking closes it and adds a chip under the box.
`#facet-count` ("N recipes" / "N favourites" + *Clear*) shows only while
filtering. State is kept per page in sessionStorage (`mk-facets:<path>`), so
it survives opening a recipe and coming back. The dated uppercase-label,
coloured-border chips and the suggestion dropdown are gone.

## "N ingredients aren't linked"
A required (non-optional) line with no catalogue link keeps a recipe out of
suggestions (`_is_cookable`, by design: it can't be checked). The recipe page
says so under *Ingredients* (`#unlinked-note`), counted in the template and
kept live by `recipe_links.js` (`syncUnlinkedNote` on every pill change; rows
carry `data-optional` for to-buy lines). *Link it* switches on edit mode and
opens the editor on the first unlinked line. The import review form shows the
same note (`#rf-unlinked-note`, `syncUnlinked` in `recipe_form.js`, live on
pick, optional toggle and row add/remove).

## Water
`Water` (Pantry, staple) added to `seed_catalogue.py`; existing databases don't
reseed, so add it by hand there. Resolver: `FUZZY_GUARDS` in `resolver/core.py`
refuses a fuzzy hit on Water when the line says coconut / rose / tonic /
blossom. Golden set: "180 ml lukewarm water" → Water; "coconut water" and
"rose water" → unmatched. `flask resolve-eval` passes, 31/31, 0 false links.

`sw.js` cache → v24.
