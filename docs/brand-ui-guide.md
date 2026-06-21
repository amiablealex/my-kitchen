# My Kitchen — Brand & UI Guide (v0.1)

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
- **Self-host the fonts** (all open-source / OFL — no Google CDN dependency) so it works offline on the LAN / in HA.
- Contrast rule: rainbow/accent colour only on large display text; body stays `--text` on `--grape`.

## 5. Iconography
- **First pass: use a clean open icon set, not bespoke icons** — fastest, consistent, scalable, material-aligned, self-hostable as SVG. Candidates: **Material Symbols (Rounded)**, Phosphor, Lucide, Tabler. *Proposed: Material Symbols Rounded.* **No emojis** (per brief).
- Nav icons needed: Home, Lets Cook, Stock/Pantry, Recipes (history), Favourites, Manage (ingredients/categories/equipment/dietary), Household/Users, Settings.
- **Bespoke icons / mascot logo: deferred** to production iteration — too heavy for a "that'll do" pass.

## 6. Logo
For now the logo **is the app name** set in the bubble display font with the rainbow treatment — lightweight, on-brand, scalable. A bespoke illustrated mark is later polish.

## 7. Layout & navigation
- Borrow **Music Assistant's pattern, not its stack**: a collapsible left nav drawer/rail on desktop that collapses to a **bottom nav bar** (or hamburger drawer) on mobile. (MA is a Vue SPA; we stay server-rendered Jinja — see §10.)
- A shared **app shell**: nav + top bar (page title) + content slot, inherited by every route.
- Mobile: bottom nav for primary destinations (Home, Lets Cook, Stock, Recipes), overflow/drawer for the rest (Manage, Household, Settings).
- Touch targets ≥ 48px; primary actions thumb-reachable.

## 8. Components (style once, reuse everywhere)
- **Buttons:** primary (accent-filled), secondary (outline), and the hero "Lets Cook" CTA. Friendly corner radius.
- **Cards / surfaces:** `--surface`, rounded, subtle elevation — recipe cards, pantry groups, manage rows.
- **Forms / inputs:** high-contrast, large tap targets, clear focus states.
- **Wizard step indicator:** four connected dots in accents 1–4, current step emphasised.
- **Pantry rows:** item + note + remove; the search-to-add field.
- **Recipe display:** rainbow **title**, energetic **intro** block, **ingredients** (extras marked "you may need to buy"), **prep**, **cook**, optional **tips**; the two-card **choice screen** with blurbs; the **allergy caveat** as a gentle but visible notice.
- **Empty states** (empty pantry → "update stock →") and a friendly **generating** state for the synchronous wait ("cooking up your recipes…").
- **States:** focus, hover (desktop), disabled (the double-submit guard).

## 9. Motion
Minimal and lightweight — subtle transitions (nav open/close, button press), no heavy animation. Keep it snappy on a Pi and inside the HA app.

## 10. Technical approach
- **Stay server-rendered Jinja. No SPA, no bundler, no build step.** (MA's SPA stack would be a rewrite against the project's goals.)
- **Design tokens** as CSS custom properties in one `:root` block (palette, type, radius, spacing) — re-brand in one place.
- One global stylesheet (+ optional small per-area files), **mobile-first** media queries.
- **Self-host fonts + icons** (offline-friendly on the LAN / in HA).
- **PWA:** web manifest + simple service worker + app icons → installable on Pixel/iPhone, and the basis of the standalone-app feel (the deferred PWA item lands here).
- **Preserve ingress-safety:** `url_for`, relative assets, ProxyFix — so it works embedded in HA *and* standalone, MA's dual-mode.
- **Fold in the UTC→local-time fix** (History + Favourites) while the templates are open.

## 11. Scope for this pass
**In:** tokens; app shell + responsive nav; restyle of all existing screens via shared components; wizard step dots; recipe-display polish; PWA basics; local-time fix.
**Deferred to production iteration:** bespoke icons / mascot logo; a light theme / HA-theme matching; fine micro-interactions; deep per-screen polish.

## 12. Open choices to confirm
1. App name: **My Kitchen** (confirmed as the starting name).
2. Display + body fonts (proposed: **Grandstander + Figtree**, both uncommon and self-hostable).
3. Icon set (proposed: **Material Symbols Rounded**).
4. Single dark-grape theme for now (recommended; light/HA-theme matching later).
