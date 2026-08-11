# Phase 22 — Dietary tags: allergies, dislikes and diets (0.22.0)

**Shipped:** 0.22.0. **Schema change:** none.

## The problem

Both live dietary tags were "Pesto" and "Peanut Butter", both typed
`preference`, both meaning *don't like it*. The brief emitted:

> Dietary preferences (steer the AVAILABLE items this way where you sensibly can): Pesto.

Three faults, in increasing order of how much they mattered:

1. **Direction ambiguous.** A bare food noun under "preferences" reads as a
   steer *towards* it. `RULES` said "lean away from preference-breaking
   available items", which only parses for a *style* tag — Vegetarian is broken
   by meat; "Pesto" isn't broken by anything.
2. **Scope wrong — the real bug.** Preferences were confined to the AVAILABLE
   tier. Pesto isn't in stock and isn't in the 173-item catalogue, so the
   constraint never reached it. Even worded perfectly it could not have stopped
   pesto arriving as a `to_buy` extra, assembled from staples, or suggested in
   `tips`.
3. **One type, two jobs.** "Pesto" and "Vegetarian" need opposite language.

## The change

Three types, severity-ordered in `TAG_TYPE_CHOICES`:

| key | label | behaviour |
|---|---|---|
| `allergy` | Allergy — never use this | Unchanged. Absolute, overrides must-use, triggers the caveat. |
| `avoid` | Dislike — leave it out | Whole-recipe exclusion incl. extras, tips, substitutes. Yields to must-use. No caveat. |
| `preference` | Diet — how they eat generally | Steers the whole recipe. Yields to must-use. |

**No migration.** `type` is a plain `db.String` with `default="preference"`, so
adding a value is a constant edit. `preference` kept its key — every existing
row stayed valid and the two tags were re-typed in the UI in under a minute.
Guessing which legacy rows meant which thing would have been strictly worse than
asking the two people who wrote them.

Prompt: dislikes block; precedence ladder allergy > must-use > dislike >
preference; preferences broadened past AVAILABLE; optional extras made to
respect both exclusion lists (the hole pesto would otherwise have come back
through). `combined_dietary()` returns three lists, with unrecognised types
falling to preferences — the old two-way behaviour, so nothing silently vanishes.

## Checkpoints

- **CP1** — constant, `combined_dietary`, `build_brief`, `prompt.py`. `render_prompts.py`: system prompt moved in exactly two places, every golden user prompt byte-identical (none carries a tag). `flask eval-recipes` re-run.
- **CP2** — `TAG_TYPE_HINTS`; Manage groups looped from the constant; stacked-radio type picker; "name the food, not the sentiment" hint; plural headings on user edit.
- **CP3** — type-coloured badges on the cooking-for step; three labelled rows on the review brief.
- **CP4** — assign-to-people checkboxes on the add form; the "ticking sets the full list" note on user edit.

## Learnings

- **A wrong constraint is invisible.** No error, no missing data, a plausible-looking brief line — and months of generations quietly told to *use* the two foods the household least wanted. Nothing in the eval harness covered a tag-carrying brief, so nothing could have caught it. **A golden brief carrying dietary tags is worth adding.**
- **Two types couldn't be worded correctly.** The instinct was to fix the wording and keep the schema. It doesn't work: any sentence right for "Pesto" is wrong for "Vegetarian". The extra concept bought unambiguous language for both.
- **`TAG_TYPE_CHOICES` as display order** removed the hardcoded two-group split; the CSS modifier is the type key, so a fourth type is one constant entry plus one CSS line.
- **Radios beat a `<select>` when the choice is the thing being got wrong.** The picker shows each type's effect and an example at the moment of choosing.
- **Creating and assigning were two screens apart**, so people did the first and stopped — and an unassigned tag reaches no brief at all. Merged into one form; the nudge flash now only fires when nothing was ticked.
- **The allergy caveat stayed keyed on allergies only.** Firing it for a dislike would dilute the one notice that means "check this yourself".
