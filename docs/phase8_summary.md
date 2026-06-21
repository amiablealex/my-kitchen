# Phase 6 — UI Restyle & Branding (summary)

> Docs run one ahead of the roadmap: this covers **roadmap Phase 5** (UI restyle & branding).
> **Status:** Done — deployed to the Pi and committed. Driven by `brand-ui-guide.md`.
> **Scope discipline:** look-and-feel only, with a single logic change (the local-time filter). **No schema change.**

The proven skeleton is now a coherent, branded, mobile-first app — installable as a PWA. Built as five testable checkpoints (CP1 → CP4), each deployed and confirmed before the next.

## What shipped

- **CP1 — Foundations.** Design tokens in one `:root` block (palette, the four accents, type scale, radius/spacing, the `--rainbow` gradient). Self-hosted **variable fonts** (Grandstander + Figtree, woff2). Inline-SVG **icon macro** (`_icons.html`: Material Symbols Rounded paths + a hand-authored solid star). **App shell** (`base.html`): responsive nav — desktop left rail collapsing to a mobile drawer + bottom nav (Music Assistant's *pattern*, plain Jinja) — top bar, and active-state derived purely from `request.endpoint`. Rainbow logo.
- **CP2 — Component library** (appended to `app.css`). Buttons + the gradient hero "Lets Cook" CTA, cards, the `.form` treatment (auto-stacks the existing `<label>…<input></label>` markup), tappable `.option` rows, the reusable **list-row** component (+ desktop grid), badges, the wizard **step-dots** (`_components.html`), pantry styling, choice cards, recipe display, notices, empty states, generating overlay. Landing page restyled as the showcase.
- **CP3 — Screen cascade** (templates only).
  - *3a — cook flow:* four wizard steps + step-dots, review + the **generating overlay**, choice screen, the marquee recipe display (rainbow title, intro, "(you may need to buy)", timer chips, tips, allergy caveat as a notice), error.
  - *3b — stock + manage:* stock heading/back-link; all four catalogue screens converted **table → list-rows** with badges; add/edit forms; delete-guards and confirm dialogs preserved.
  - *3c — household / history / login:* users + edit (dietary tags as option rows, retired read-only branch), history (generation cards, gold ★ markers, filter), favourites, branded login.
- **CP4 — PWA + local-time.** Web manifest + service worker + **rainbow pot/stove app icons** (192/512/180) + Apple meta. A `localdt` Jinja filter (`APP_TIMEZONE`, default `Europe/London`, BST handled by `zoneinfo`) replaced the UTC timestamps in History/Favourites.

## Key decisions

- **Rainbow signature is confined** to large display text (logo, recipe titles) via gradient-clipped *live* text — never images, never body/nav/small text.
- **Icons:** a curated inline-SVG set, not the whole Material Symbols font — lighter, offline, colourable via `currentColor`.
- **Tables → one reusable list-row component** (no per-screen table CSS); desktop multi-column grid only where it aids scanning (categories, dietary tags).
- **Single global stylesheet** grown across checkpoints; plain CSS custom properties, no build step.
- **Local-time as a reusable filter**, not per-template; naive DB datetimes treated as UTC.
- **App icon:** pot/stove glyph in the brand rainbow on grape (replaced an initial "MK" monogram that didn't represent the app).

## Learnings / gotchas

- **Jinja scope:** a top-level `{% set %}` in the base leaks into child content blocks — naming the nav-state var `active` clobbered views passing an `active` *list* (crash on `/users` and `/manage/ingredients`). Renamed to `nav_active`. Separately, **macros don't capture template-local vars** → the active value must be passed in as a parameter.
- **CSS specificity:** a bare-button baseline written as `button:not(.x):not(.y):not(.z)` is specificity 0-3-1 and beats component classes like `.btn--primary`. Wrapping it in `:where(…)` zeroes it so any single class wins.
- **Icons in JS-delegated buttons** break click delegation (`event.target` becomes the `<svg>`), so the stock add/remove buttons were kept text-only.
- **Sub-path / ingress safety:** the manifest uses relative `start_url`/`scope` (`../`) and the SW is registered via `url_for`, so both resolve under HA ingress. **Service workers only run in a secure context** (HTTPS or localhost) — a no-op over a plain-HTTP LAN address, fully active over HTTPS (HA ingress with TLS). Installability still works on iOS via the manifest.
- **MuPDF's SVG gradient fill is unreliable** — the rainbow icon was produced by rendering the glyph as a mask and compositing a PIL-built gradient through it.

## Deferred (production iteration)

Bespoke icons / mascot logo; a light theme / HA-theme matching; fine micro-interactions; deep per-screen polish; a **root-scoped service worker** for true offline app-shell (the current SW is `/static/`-scoped, so it caches assets, not page navigations).

## Files

- **New:** `static/css/app.css`, `static/fonts/{grandstander,figtree}-var.woff2`, `static/icons/icon-{192,512,180}.png`, `static/manifest.webmanifest`, `static/sw.js`, `templates/_icons.html`, `templates/_components.html`.
- **Changed:** `templates/base.html` (the shell) and all screen templates; `__init__.py` (the `localdt` filter); `config.py` (`APP_TIMEZONE`); `requirements.txt` (`tzdata`).

## Watch items / next

- PWA install + SW require **HTTPS** — test via the HTTPS HA URL; re-add to home screen to refresh the cached icon after the icon change.
- Next up is **roadmap Phase 6 — async generation**, the main remaining technical-debt item; rising generation latency (richer output on `gemini-3.5-flash`) is the trigger to bring it forward.
