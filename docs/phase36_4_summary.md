# 0.36.4 — filter button, compact pills

The search box used to do two jobs on one tap: it raised the keyboard and opened
the full filter panel. On a phone the two together filled the screen, and the
only way out was to tap outside the box, which nothing hinted at.

**Filter button.** `#facet-toggle` (the `tune` icon) sits inside the box's label
at the right. A tap opens the panel with every value (`pinned`) and blurs the
field so no keyboard appears. Tapping again closes it. Mousedown and click call
preventDefault so the label doesn't refocus the field. States: muted at rest,
teal icon while chips are on (`.has-filters`), a teal petal bead while the
panel is open (`.is-open`); `aria-expanded` follows.

**Typing.** Focusing the field no longer opens the panel. While unpinned, the
panel shows only values matching the typed text and closes when there are none
or the text is empty. Opened from the button, it stays open with every value as
you type and delete. Picking a value, tapping outside or Escape closes it, as
before.

**Pills.** `.facet-value` is 26px tall (was 34), 0.8rem text, 10px side padding,
5px gaps, and the group labels are tighter. Option petals are 9px. The panel
with the test data went from about 300px to 223px.

**Placeholder** is "Search recipes" / "Search favourites" (from the noun).

Tested at 390px with touch: tapping the text opens no panel; "din" offers
Dinner; "brown sugar" shows no panel and the matching recipe; the button opens
and closes the panel and drops focus; picking Dinner closes it and the button
turns teal; typing while pinned narrows and clearing the text keeps it open;
tapping outside closes; Favourites works the same. No JS errors.

## 0.36.5 fix
With text typed, the button set `pinned` but the panel still narrowed to the
text. "brown sugar" matches no value, so the panel stayed hidden and the button
seemed dead. Now a pinned panel ignores the text and shows every value. A pick
from it keeps the text, so the search and the chip combine; only a suggestion
found by typing replaces the text, as before. Enter picks the first value only
for typed suggestions; while pinned it just closes the panel.
