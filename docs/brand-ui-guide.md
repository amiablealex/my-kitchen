# My Kitchen — Brand & UI Guide (v0.2)

The visual companion to `recipe-app-spec.md`. It defines the look, feel and front-end approach for the Phase 5 restyle. Scope is a **first-pass "that'll do" baseline** good enough for household use and sharing progress online; fine-tuning is ongoing in production.

---

## 1. Philosophy
- **Playful as a signature, not the whole surface.** The personality — rainbow "bubble" headers, bright accents — lives on display headers, the logo and recipe titles. Body text, forms, nav and cards stay calm, clean and highly legible. Get this ratio right and it's distinctive *and* readable; get it wrong (bubble everything) and it reads as a toy.
- **Lightweight & maintainable.** Design tokens + shared layout + reusable components. Plain CSS, **no build step**, server-rendered Jinja stays. Don't over-develop styling that becomes a burden to maintain.
- **Mobile-first, desktop-capable.** Primary use is the Home Assistant companion app on phones (Pixel 9a, iPhone 16); desktop must be fully functional too.
- **At home in Home Assistant.** Material-*inspired* conventions (cards, rounded corners, clear elevation, big touch targets) and an MA-style nav, delivered without MA's SPA stack.

## 2. Principles
- Restraint with the playful element — one signature, not everywhere.
- Systematic: tokens → components → screens. Style once, cascade everywhere.
- Legibility first: bright tones for large text/accents only; body text stays high-contrast.
- Touch-first: works one-handed at the hob; primary actions thumb-reachable.

## 3. Colour palette

**Core (locked):**
| Token | Hex | Use |
|---|---|---|
| `--grape` (background) | `#3B1058` | App background |
| `--accent-1` (teal) | `#56D0BB` | Wizard step 1; accents/buttons |
| `--accent-2` (lime) | `#B1E46D` | Wizard step 2; accents/buttons |
| `--accent-3` (orange) | `#FE9B46` | Wizard step 3; accents/buttons |
| `--accent-4` (pink) | `#FF5F91` | Wizard step 4; accents/buttons |

**Derived (suggested — tune freely):**
| Token | Hex | Use |
|---|---|---|
| `--surface` | `#4A1A6B` | Raised cards / grouped rows |
| `--surface-2` | `#5A2A7E` | Higher elevation, hover |
| `--text` | `#F5F0FA` | Primary text (near-white, lilac tint) |
| `--text-muted` | `#C9B8DC` | Secondary text |
| `--divider` | `rgba(255,255,255,0.12)` | Borders / dividers |
| success / warning / danger / info | lime / orange / pink / teal | Map semantics onto the four accents |

**Wizard step dots** map 1→4 onto accents 1→4 — and onto the four *input* steps (ingredients → cuisine → time → cooking-for).

**Rainbow header treatment:** a warm→cool spectrum (red/pink through to violet), tuned bright so every stop reads on the grape, using the four accents as anchors. Suggested stops:
`#FF5F91` (pink) → `#FE9B46` (orange) → `#FFD24A` (yellow) → `#B1E46D` (lime) → `#56D0BB` (teal) → `#5AB0FF` (sky) → `#B488FF` (violet).
Applied as a gradient (or per-letter colour) on large display headers / logo / recipe titles **only** — never on body or small text.

## 4. Typography
- **Display / "bubble"** (headers, logo, recipe titles): a rounded, friendly display face with character — deliberately *not* the usual rounded defaults (Fredoka et al.). *Proposed: **Grandstander*** (variable weight, playful, genuinely uncommon). Alternatives: **Mochiy Pop One** (very bubbly), **Baloo 2**, or **Bagel Fat One** for a logo-only flourish. The rainbow treatment applies here.
- **Body / UI**: clean, highly readable, slightly distinctive — steering clear of the ubiquitous Inter / Nunito / Roboto. *Proposed: **Figtree*** (friendly rounded terminals, pairs with the display, very legible). Alternatives: **Lexend** (legibility-engineered), **Hanken Grotesk** (more character).
- One display + one body; a small type scale (display / h2 / h3 / body / small).
- **Scale (0.28):** root 14px; body 1rem. Display steps down harder than body because Grandstander reads large: `--fs-display` clamp(1.8rem, 6.5vw, 2.6rem), recipe title clamp(1.75rem, 7vw, 2.6rem), h1 1.45rem, h2 1.2rem. Touch targets stay in px (44px minimum), so shrinking type never shrinks a tap target.
- **Self-host the fonts** (all open-source / OFL — no Google CDN dependency) so it works offline on the LAN / in HA.
- Contrast rule: rainbow/accent colour only on large display text; body stays `--text` on `--grape`.

## 5. Iconography
- **First pass: use a clean open icon set, not bespoke icons** — fastest, consistent, scalable, material-aligned, self-hostable as SVG. Candidates: **Material Symbols (Rounded)**, Phosphor, Lucide, Tabler. *Proposed: Material Symbols Rounded.* **No emojis** (per brief).
- Nav icons needed: Home, Lets Cook, Stock/Pantry, Recipes (history), Favourites, Manage (ingredients/categories/equipment/dietary), Household/Users, Settings.
- **Bespoke icons / mascot logo: deferred** to production iteration — too heavy for a "that'll do" pass.

## 6. Logo
The four-quadrant **pinwheel** (teal, lime, orange, pink, clockwise from 12) beside the rainbow wordmark (0.27.2). The pinwheel also marks anything AI: @kitchen, AI-generated recipes, the Cook destination.

## 7. Layout & navigation
- Borrow **Music Assistant's pattern, not its stack**: a collapsible left nav drawer/rail on desktop that collapses to a **bottom nav bar** (or hamburger drawer) on mobile. (MA is a Vue SPA; we stay server-rendered Jinja — see §10.)
- A shared **app shell**: nav + top bar (page title) + content slot, inherited by every route.
- Mobile: bottom nav for primary destinations (Home, Lets Cook, Stock, Recipes), overflow/drawer for the rest (Manage, Household, Settings).
- Touch targets ≥ 48px; primary actions thumb-reachable.

## 8. Components — "Petals" (0.28)

**The shape.** A petal is a rounded rectangle with **one sharp corner, bottom-left** (`--petal-sm` / `--petal` / `--petal-lg`). Pressing a button flips the sharp corner to top-left (`--petal-flip*`); that's the house tap feel. Surfaces (cards, groups, notices, notes, dialogs) are petals too. Plain pills stay for chips that aren't selected, tags and the version trail.

**The rule.** *Buttons and chips are plain petals; beads only mark things.* A bead is a small filled petal holding an icon. It appears on notices and flashes, home tiles, the active nav item, group headers and menu items. It never appears inside a button.

**Colour belongs to things (`--k`).** Each destination owns an accent, used by the drawer, bottom bar and home tiles alike: Home teal, Cook the pinwheel, Stock lime, Recipes orange, Favourites pink, Manage/Household/Usage teal (`.k-<key>`). Notices take theirs from their kind (success lime, warning orange, error pink, info teal). Bead fill is `var(--kbg, var(--k))`; only Cook sets `--kbg`. Don't define `--kbg` at `:root`: a root value resolves once and stops the `.k-*` classes changing it.

- **Buttons:** primary = the one teal fill (`.btn--primary`). Secondary = tonal `--surface-2` fill, icon in `--k` (`.btn--secondary`). Tertiary = teal text only (`.btn--ghost`), used for Edit tags, Edit links, Cancel and the like. Danger is a pink tint. `.btn--grow` (label left, icon right) and `.btn--square` (icon-only, 48px) make the wizard's Back + Continue. **No outline buttons anywhere.**
- **Options / chips:** the native radio/checkbox stays in the DOM but is hidden. A picked option fills **solid** in `--pick` with a drawn tick and goes sharp-cornered. The wizard sets `--pick` per step (2 lime, 3 orange, 4 pink); step 1's lanes use their section colour.
- **No left-border stripes.** Every former stripe (flash, notice, intro, groups, lanes, toast, nav) is now a bead. The one deliberate exception is the **@kitchen reply**, which keeps its teal quote line because it reads as a reply in a thread.
- **Groups:** petal card, header bead in the group colour (AI group = pinwheel), count in a small pill.
- **Recipe rows:** one line of title, one of meta (`9 Nov · Italian · [clock] relaxed · [person] 2`, as icons). The cook is a small tinted initial that leads the meta line, so titles keep the full width. Unchosen pairs are a single "Pick one" row. Recipe rows carry no actions (archive lives on the recipe page); only a failed attempt, which has no page, gets a × to clear it.
- **Recipe page:** the version trail ends in a dashed **+ New version** node that opens the refine panel underneath it. Submitting always opens a **confirmation dialog** that quotes the instruction, says the current version is kept, and points plain questions to @kitchen. Serves + Favourite share a line. Print/share, Edit recipe and Archive live in the top bar's **⋯ overflow menu** (`{% block topbar_actions %}`).
- **Wizard:** four connected step dots in accents 1–4, current step emphasised. Every step is `.wizard-step` with a sticky, right-aligned **dock** (Back + Continue) just above the bottom bar; short steps centre their body. The review page puts its Generate button in the *Make something new* card, beside the request it sends.
- **Choice screen:** numbered beads (1 teal, 2 pink) plus comparison tags; one right-aligned *Cook this* per card. *Neither one?* folds away because choosing is the main action.
- **Stock:** items are chips (solid = in stock); catalogue matches are dashed chips (tap to add). Tap an item to note it; × removes it. This mirrors the wizard, where you pick from the same items.
- **Wizard step 1 (0.29.2):** the same chips, picked in their lane colour. A search row (pill field + *Edit stock*) filters lanes and staples together. Catalogue matches that aren't in stock appear under a **hollow bead** (*Not in stock*, i.e. not here yet) as the stock page's add chips, with a line saying a tap stocks it household-wide. *Edit stock* is a submit, so picks survive the trip; the stock page then shows a docked *Back to your picks*.
- **People (0.29.3):** each person has a colour from a fixed set of seven (`USER_COLOURS`: teal, lime, sun, orange, pink, lilac, sky), carried as `--u` by `.u-<key>`. Their mark is their initial on a petal (`_person.html` → `person_mark`): tinted and small in meta lines and note heads, solid and large in Household and the person header. Unchosen falls back to the old id rotation. Dietary tag colours: allergies pink, dislikes orange, diets lime; teal stays the action colour.
- **Manage index:** grouped lists (Kitchen, People) of bead rows with a count and an arrow, not tiles. Household is a People entry, not a nav item.
- **Manage lists (0.29.4):** no buttons on list rows. A plain name is a chip (`link_chip`); a thing with something to say is a row with a meta line and an arrow (`link_row`). Either opens the item's page: `edit-head` (name + one meta line), the form, a docked Save. Destructive actions live behind ⋯ (`danger_form`). On/off and pick-one fields are option chips (`toggle_chip`, `section_chips`), picked in the colour of what they mean.
- **Confirm:** anything destructive uses `data-confirm` / `data-confirm-title` / `data-confirm-ok` on the form; `confirm.js` shows the app's dialog with a pink bead. Never `confirm()`.
- **Category tree (0.29.5):** sections are coloured groups; categories hang off a 2px trunk in the section colour (55% mix), with `├`-style branches and a rounded `└` on the last node, which is always the inline *Add a category*. One number per node (ingredients); the section header carries the total.
- **Empty states** and the **generating** state as before (polka panel, bouncing four-colour dots).
- **States:** focus (3px teal outline, including options via `:has(input:focus-visible)`), hover (desktop), disabled (the double-submit guard).

## 9. Motion
Minimal and lightweight — subtle transitions (nav open/close, button press), no heavy animation. Keep it snappy on a Pi and inside the HA app.

## 10. Technical approach
- **Stay server-rendered Jinja. No SPA, no bundler, no build step.** (MA's SPA stack would be a rewrite against the project's goals.)
- **Design tokens** as CSS custom properties in one `:root` block (palette, type, radius, spacing) — re-brand in one place.
- One global stylesheet (+ optional small per-area files), **mobile-first** media queries.
- **Self-host fonts + icons** (offline-friendly on the LAN / in HA).
- **PWA:** web manifest + simple service worker + app icons → installable on Pixel/iPhone, and the basis of the standalone-app feel (the deferred PWA item lands here). `sw.js` serves `/static/` cache-first, so **bump its `CACHE` name whenever CSS/JS changes** or installed phones keep the old files.
- **Preserve ingress-safety:** `url_for`, relative assets, ProxyFix — so it works embedded in HA *and* standalone, MA's dual-mode.
- **Fold in the UTC→local-time fix** (History + Favourites) while the templates are open.

## 11. Scope for this pass
**In:** tokens; app shell + responsive nav; restyle of all existing screens via shared components; wizard step dots; recipe-display polish; PWA basics; local-time fix.
**Deferred to production iteration:** bespoke icons / mascot logo; a light theme / HA-theme matching; fine micro-interactions; deep per-screen polish.

## 12. Settled
1. App name **My Kitchen**; fonts **Grandstander + Figtree**; icons **Material Symbols Rounded** (inline SVG macro); single dark-grape theme.
2. Petals component language and the bead rule (0.28); explored on a design canvas as directions A (beads), B (keycaps, rejected as too bulky) and C (petals), then A×C hybrids.
