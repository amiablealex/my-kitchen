# Phase 28 — Petals, checkpoint 1 (0.28.0)

A front-end-only redesign: no migration, no route changes, no prompt
changes. The look was settled on a design canvas over three rounds (beads /
keycaps / petals, then A×C hybrids, then "Petals, refined"). The rules it
landed on are written up in `brand-ui-guide.md` §8 (v0.2).

## What changed
- **Tokens (`app.css` `:root`).** Petal radii (`--petal-sm|--petal|--petal-lg`
  plus `-flip` variants), `--pinwheel`, `--k` (an element's accent) and
  `--pick` (the fill for a selected option). The display sizes step down
  (`--fs-display`, `.recipe-title`, `.home-title`, h1/h2). The root stays
  at 14px.
- **Buttons.** No borders. Primary is teal, secondary is a tonal fill with its
  icon in `--k`, and the new `.btn--ghost` is teal text. `.btn--grow` and
  `.btn--square` make the wizard's nav. `:active` flips the petal.
- **Options.** The inputs are visually hidden; checked fills solid in `--pick`
  with a CSS-drawn tick. Wizard steps set `--pick` through
  `.steps:has(.sN.is-current) ~ *`, so no template change was needed.
- **Stripes → beads.** Flash (now has an icon, mapped per category in
  `base.html`), notice, recipe intro, recipe/stock group headers, wizard
  lanes, toast and the nav's active item. `.note-reply` keeps its line on
  purpose.
- **Destinations.** `nav_item` and `bn_item` add `k-<key>`. Home tiles and the
  Manage index use `.home-tiles` with a `.tile-bead`.
- **Recipe page.** `{% block topbar_actions %}` (new in `base.html`) holds a
  `<details class="overflow">` menu: Edit recipe (user source), Print or
  share, Archive. `base.html` closes it on an outside tap or Escape. The
  trail now shows whenever `can_refine`, even at v1, and ends in a
  `#refine-toggle` node. The refine panel moved under the trail and is no
  longer a `<details>`. Favourite joins the serves line. The old bottom
  button cluster is gone.
- **Refine confirmation.** `refine.js` intercepts the form's submit (which
  fires only after `required` validation), quotes the instruction in
  `dialog#refine-confirm`, and submits only from its Create button
  (`form.submit()`, so the handler doesn't loop). It falls back to
  `window.confirm` without `<dialog>`. `window.mkRefine` (the servings
  rewrite) goes through the same path. It also scrolls the trail to its
  newest end.
- **Notes composer.** *Add note* is always primary. `notes.js` no longer
  swaps btn classes, only the label and pinwheel. *Ask @kitchen* is a
  secondary petal that pre-fills the mention.
- **Recipe rows.** New `history/_rows.html` macros (`cook_av`, `row_meta`,
  `row_ind`) are shared by Recipes and Favourites. There's a new
  `shortdate` filter ("9 Nov", with the year only if it isn't this year).
  Unchosen pairs become one "Pick one" row. The per-row archive button and
  the `recipe_archive.js`/`toast.js` includes are removed from the Recipes
  page.

## Left for later
- `static/recipe_archive.js` and the `history.row_archive` / `row_restore`
  routes are now unused. Remove them in the next checkpoint.
- The choice screen still uses top-border accents, and the stock editor is
  restyled by tokens only. Both get their own mockups before any structural
  change.
- Checkpoint 2: "Make this version N" on @kitchen replies, shown only when
  the answer suggests a change. That means an additive column for the flag
  and change instruction on `recipe_comments`, plus a qa prompt change with
  its own eval.

## 0.28.1 — wizard layout, review page, quieter rows
- **Wizard layout.** Every step is `.wizard-step` (a flex column filling the
  viewport between the top bar and the bottom bar) > step dots + `form.wizard-form`
  > `.wizard-body` + `.wizard-dock`. The dock is sticky at
  `bottom: bottomnav + space-4` and right-aligned, with `pointer-events` only
  on its buttons. On short steps `margin-top: auto` parks it there anyway.
  `.wizard-step--center` (time, cooking-for) centres the body with
  `margin-block: auto`. Cuisine stays top-aligned, because its cuisine block
  shows and hides with the meal type. Step 1 has no Back, so its dock is just
  Continue.
- **Review.** The step dots show all four done (`step_dots(5)`). The brief is
  a `<details class="brief-panel">` whose summary is a chip row (use-up,
  meal, cuisine, time, servings, allergies); the full rows are inside.
  Suggestions sit in `.sugg-band` (orange tint, polka, full-bleed on
  phones). The special request is in `<details class="fancy">`, open when
  there are no suggestions or a request is already filled. The dock's
  primary reads *Make something new* when suggestions exist, otherwise
  *Generate recipes*.
- **Rows.** `cook_av` renders `.cook-i`, a tinted 18px initial at the start of
  `row_meta` (new `who`/`verb` params). The `.cook-av` column is gone.
- **Fix.** `.menu-item` gets `justify-content: flex-start`. It had inherited
  `center` from the bare-button base, which pushed the Archive button's
  contents in.
- `sw.js` cache bumped to v4.

## 0.28.2 — review page, take two
- The review page has no dock. `.wizard-dock` is replaced on this page by
  `.review-actions` inside the *Make something new* card (`.review-new`), so
  Generate sits with the request it sends. It's the same Back + primary pair,
  right-aligned, just not floating.
- Two `.review-section`s, each headed by its bead (`.review-head`): *Already in
  your recipes* (orange tile bead, only with suggestions) and the new card
  (pinwheel `.confirm-bead`; the heading reads "Nothing take your fancy?" when
  suggestions exist). `.sugg-band` and `details.fancy` are removed.
- "Full brief" moved inside the chip row so it wraps with the chips.
- Cuisine step: now `.wizard-step--center`. `#cuisine-block` gets
  `.wizard-group` (`margin-top: space-6`).
- `sw.js` cache v5.

## 0.28.3
- `SPECIAL_REQUEST_CHIPS` cut to two ("Something spicy", "Keep it simple"),
  so they fit one row at phone width. The rotating placeholder still offers
  other examples. The review card drops the `.special-request-hint` line,
  which repeated the card's own heading. No static files changed, so no
  `sw.js` bump.
