# 0.42.1 — the version trail, drawn as a tree

No migration. Built on 0.42.0.

- **Markup.** The trail is one scroller (`nav.version-trail`) holding
  `.version-tree`, a column of rows; rows no longer scroll on their own, so
  drawn lines stay attached. Each chip's `li` carries `data-v` (recipe id)
  and `on-path` when it's the version being viewed or one it was made from.
  A branch row carries `data-from` (parent recipe id) and
  `aria-label="Made from vN"`; its first `li` holds a hidden
  `.version-elbow`. The "↳ from vN" text, the end-of-row "+ New version" node
  and its separate branch row are gone, and so are their styles.
- **The +.** `.version-plus` (`#refine-toggle`) sits inside the current
  chip's `li`, on any refinable version, labelled "New version from vN".
  The refine panel's subtitle still says when it starts a branch
  (`branching`, from `Family.trail`).
- **The note.** The older-version notice box is now `p.version-note`: "This
  is v1. The newest is v3. Go to v3".
- **`Family.trail()`** returns `(rows, branching)`. Rows carry `from` (parent
  id) and `from_n`; nodes carry `on_path`. After a row, its branches are
  added right-most parent first, each followed by its own branches, so a
  line from a version further left passes below rows that start further
  right and never crosses a chip.
- **`static/version_trail.js`** (new, loaded wherever the trail shows): for
  each branch row in page order, measures the parent's `.version-n`, sets the
  row's indent to meet the line and sizes the elbow from the bubble's bottom
  to the row's middle. Redraws after `document.fonts.ready` and on resize
  (debounced). Also scrolls the trail so the current version is in view
  (moved from refine.js). Without JS, branch rows are set in with no line.
- **Lit path.** `li.on-path + li.on-path::before` and `.version-elbow.on-path`
  in `--accent-1` at 0.7.
- **SW cache** v34.

Tested on a throwaway DB with the mock provider: a family of v1→v2→v4,
v1→v3, v2→v5 viewed at v1, v3 and v5 (row order main, v5, v3; elbows land
on the right bubbles; lit path follows), a straight line viewed at v1 and
v2 (one row each), the panel opened from the + on v1, and a redraw after
resizing from 390px to 700px. No JS errors. The 0.41.0 and 0.42.0 smoke
runs still pass.
