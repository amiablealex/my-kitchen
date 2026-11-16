# 0.40.0 — docs links, seeded kinds

No migration.

- **Seeded kinds.** `seed_catalogue.KINDS` = (Red onion → Onion, New
  potatoes → Potatoes, Cherry tomatoes → Tomato), applied by
  `seed_reference_data()` after the ingredients are created. Fresh installs
  only. No new ingredient names, so the resolver's catalogue and its eval are
  unchanged. Deliberately short: varieties a household buys are its own to
  add (the docs say so).
- **Docs links.** `Config.DOCS_URL` (env `MY_KITCHEN_DOCS_URL`, default
  `https://my-kitchen.io/docs`, empty = off) exposed as the Jinja global
  `docs_url`. `templates/_docs.html`: `_TOPICS` (topic → anchor, label),
  `docs_link(topic)` and `docs_home()`. Placed at the end of existing text:
  merge sheet (merging), Kinds help and a kind's *A kind of* hint when the
  Kinds section isn't shown (kinds), staple help (staples), Manage →
  Ingredients help (catalogue), Categories help (categories), dietary tags
  lead and type help (conflicts), receipt sheet privacy text (receipts),
  recipe unlinked note (links, after *Link it* with a middle dot), new-version
  confirmation (versions), import and photo leads (import, photo), Usage lead
  (usage). *Help ↗* in the nav foot. `.sr-only` added for "(opens the docs)".
- The site's docs gained matching anchors (`categories`, `staples`, `links`,
  `which-one`, `kinds`, `or-links`, `merging`, `retiring`, `conflicts`,
  `import`, `photo`) — deploy the site before the app.
- **SW cache** v32.

Tested on a throwaway DB: the seed sets the three pairs; every page with a
link renders it with an anchor that exists on the docs page; the versions
link appears on a refinable recipe; with `MY_KITCHEN_DOCS_URL=""` no docs
link or Help appears. Playwright at 390px, no JS errors.
