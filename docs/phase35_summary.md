# Phase 35 — recipe from a photo (0.35.0)

Fifth of the input-side arc (`plan_phases_31-36.md`). One additive
migration. Reuses Phase 34's importer, prompt and review form.

## Multi-page: one call, not per-page reads
Every page goes to the AI in **one call**, numbered, so a recipe split across
pages (ingredients on one, the method over the page turn, a sauce box on the
next) is read whole. Reading pages separately would need merge logic that
breaks exactly where pages split mid-step or mid-list. Up to
`PHOTO_MAX_PAGES` (4). No reordering: the prompt says the pages may be out of
order.

## Flow
*Add a recipe* gains **From a photo** (camera icon, orange like the other
import option, since its recipes get the same dot), shown only when
`provider_reads_images()`. It isn't tied to `receipt_scanning`, since recipe
photos carry no personal data, and there's no framing step.

`wizard.recipe_import_photo` (`recipe_photo.html` + `static/photo_import.js`):
*Add a page* (a multiple file input: gallery picks several, the camera adds
one at a time) → each photo shrunk on a canvas (long edge 1600px, JPEG 0.85)
→ numbered thumbnails with × to remove → an optional **Which recipe?** field
for a page with several → *Read the recipe (N pages)*. On submit the shrunk
pages go into the form's real file input via `DataTransfer` and the form posts
normally, so the review form loads as the next page. A browser without
`DataTransfer` gets a calm message. Server: household cap
(`import_blocked_reason`), `_image_mime` (shared from `stock.routes`) per
page, then `import_recipe(images=…, which=…)`. Photos are held in memory only.

## Importer
`restructure(…, images, which)`: photos use **`LLM_MODEL`** (reads
handwriting better); links and text keep the Lite model list. `build_prompt`
for photos states the page count and either the fenced "which recipe" or an
instruction to take the recipe that runs across the photos (else the most
complete one). The system prompt gains a photo rule: pages may be out of
order, ignore other recipes sharing a page, read handwriting carefully, and
write `[unclear]` rather than guess.

## How it came in
New nullable `recipes.import_method` (`link` | `text` | `photo`; migration
`d7f3b2a96c18`), set when an import is saved (`IMPORT_METHODS`; a URL always
means `link`). The recipe page's meta line says "from a photo" (plain text)
where a web import has its "from host" link; the print view says "From a
photo"; the review note says "From your photos." 0.34 imports have NULL and
show as before.

## Small things
New `photo_camera` icon. The nav highlights Recipes on the photo page.
`.form .photo-*` selectors beat the form's label and list defaults. The mock
provider returns a fixed recipe for photos, titled with the "which" hint or
the page count.

`sw.js` cache → v22.
