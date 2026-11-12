# Phase 33 — receipt scanning (0.33.0)

Third of the input-side arc (`plan_phases_31-36.md`). One additive migration;
a new, separate prompt (the sealed generation prompt is untouched).

## Privacy design
The cook frames the item lines; the browser crops and shrinks; only the crop
is uploaded. Local OCR (Tesseract) was considered and dropped: weakest exactly
on phone photos of thermal receipts, and an annoying feature isn't worth the
claim. The image is read into memory for one provider call and never written
or logged. User-facing copy never names a provider or model ("A cloud AI
model reads this photo…", every time, above the photo button). `DOCS.md` has
the fuller note, including free-tier data use.

## Flow
- `stock/_editor.html`: a receipt icon at the right of the search field,
  rendered only when `receipt_enabled()` — `RECEIPT_SCANNING` (add-on option
  `receipt_scanning`, default true) **and** `provider_reads_images(cfg)`
  (`IMAGE_PROVIDERS` = mock, gemini, anthropic). Hidden, never a "may not
  work" note. `stock.receipt` 404s under the same check.
- `stock/_receipt.html` + `static/receipt.js`: pick (a visually hidden file
  input in a label, so iOS opens the picker) → frame (two bars with pointer
  capture, `MIN_GAP` 8%, default 6%–94%) → canvas crop at full width, long
  edge ≤ 2000px, JPEG 0.85 → multipart POST with `X-CSRFToken`.
- `stock.receipt`: limit check (`read_blocked_reason`), magic-byte type check
  (JPEG/PNG/WebP), `llm/receipt.read()`, then `classify()`. Synchronous, like
  @kitchen. Results open in the Phase 32 stock sheet, titled "Found on your
  receipt"; confirm reloads with the same Undo toast as a pasted list.

## Reading (`llm/receipt.py`)
One prompt for both inputs: a photo, or pasted lines. The user prompt lists
the active catalogue as `id: name` (staples included, so they're recognised
and quietly skipped) and the category names. The model returns
`{"lines": [{text, id, guess, category}]}`, one entry per food line; non-food,
prices, totals and payment lines are skipped by instruction. `_clean()`
nulls any id not in the active catalogue and maps the category name to an id.
`LLM_MODEL`, temperature 0.1, thinking "low", 6000 max tokens. The mock
provider returns a canned read (three catalogue items, one not-in-catalogue
guess, one unreadable line; pasted lines echo back unmatched).

## Classification (`stock/service.classify`)
Split out of `parse_list` so the resolver and the AI share it. Every id is
verified against the live catalogue whoever proposed it. Unplaced lines carry
`guess` and `category_id`. In the sheet, a guess that differs from the line
reads as "Dragon fruit?"; opening it pre-fills the search with the guess and
pre-selects the category, and when nothing in the catalogue matches, *Add as
new* opens by itself. New names get a leading capital.

## Pasted lists (`stock.parse`)
`parse_list(text, ai_match=…)`: the resolver places what it can locally;
only the lines it couldn't place (or loosely matched to a staple) go to one
`read(lines=…)` call, as text, when today's limits allow. A failure or a
reached limit just leaves them for Needs a hand. The list button reads
"Reading…" meanwhile.

## Accounting
New `ai_calls` table (`AiCall`: user, kind `receipt` | `match`, model,
tokens, status, created_at — nothing it read). Migration `b8d2e41f7a35`.
`limits_today` gains `reads` / `reads_limit`; household counts include
ai_calls. `LIMIT_RECEIPT_READS_PER_USER_DAY` (option
`limit_receipt_reads_per_user_day`, default 10). `/usage` shows a meter and
the rows ("Receipt", "List match"). `MAX_CONTENT_LENGTH` 6 MB backstop.

## Eval
`flask receipt-eval FOLDER`: photos + `expected.json` (`{"photo.jpg":
["Milk", …]}`) in a folder **outside the repo**. Prints found / missed /
wrong per photo, what would go to Needs a hand, and an overall rate. Crop the
photos to the item lines first, as the app would. Uses the configured
provider and counts towards today's usage.

`sw.js` cache → v19.
