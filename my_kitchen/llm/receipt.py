"""Reading a receipt, or matching pasted list lines, to the catalogue (Phase 33).

Two inputs, one prompt:
  * a photo — the part of a receipt the cook framed. The browser crops and
    shrinks it, so the server only ever receives the framed item lines. The
    image is passed straight to the provider and never stored or logged.
  * text — pasted list lines the deterministic resolver couldn't place (only
    those: never the whole paste).

The model returns one entry per food line: the line as written, the catalogue
id it IS (or null), a short plain guess and a suggested category. The server
then verifies every id (stock/service.classify) and the cook confirms in the
stock sheet. AI proposes, server verifies, human reviews.

Kept apart from prompt.py, so the sealed generation prompt is untouched. Each
call is recorded as an AiCall row (tokens only — nothing it read).
"""
import json

from ..extensions import db
from ..models import AiCall, Category, Ingredient
from .providers import ProviderError, get_provider

RECEIPT_MAX_TOKENS = 6000     # a long receipt is ~40 lines; thinking counts too
RECEIPT_TEMPERATURE = 0.1     # reading, not writing
MAX_LINES = 80                # cap on entries kept from one reply
MAX_TEXT_LINES = 40           # cap on pasted lines sent in one call

SYSTEM_PROMPT = """You are the RECEIPT READER in a household's recipe app. You are given \
either a photo of part of a shopping receipt, or lines a cook pasted from a shopping list \
or order. Find the food and drink items that were bought and match each one to the \
household's ingredient catalogue.

Rules:
- One entry per food or drink item, in the order they appear. Skip everything else: prices, \
quantities, multibuy and discount lines, totals, payment and card details, loyalty points, \
bags, and non-food products (toiletries, cleaning, household, pet). Also skip ready meals \
and snacks that aren't cooking ingredients.
- "text": the line as written, abbreviations and all, without the price.
- "id": the catalogue id of the ingredient this item IS, or null. Match the ingredient, \
not the brand, size or pack: "TSCO BRIT SEMI SKIM MILK 2.272L" is Milk; "WR BNLSS CHKN \
THIGH" is Chicken thigh. Choose the most specific entry that fits (Red onion, not Onion, \
for red onions). If no entry is clearly the same ingredient, use null. Never force a near \
miss: sweet peppers are not black pepper.
- "guess": a short plain name for the item in UK English, lower case except proper nouns, \
e.g. "chicken thighs", "greek yoghurt". Null only if you genuinely can't tell what it is.
- "category": when "id" is null and you have a guess, the best category from the list \
given; otherwise null.
- The same ingredient bought twice is one entry.
- If the photo isn't a receipt, or nothing is readable, return {"lines": []}.

Return JSON only, in exactly this shape:
{"lines": [{"text": "...", "id": 12, "guess": "...", "category": null}]}"""


def build_prompt(catalogue, categories, lines=None):
    """catalogue: [(id, name)]; categories: [name]; lines: pasted text lines,
    or None for a photo."""
    out = ["CATALOGUE (id: name):"]
    out += [f"{i}: {n}" for i, n in catalogue]
    out += ["", "CATEGORIES: " + ", ".join(categories), ""]
    if lines is None:
        out.append("The photo shows part of a receipt.")
    else:
        out.append("LINES pasted by the cook, between the markers:")
        out.append("<<<")
        out += [ln.replace("<<<", "").replace(">>>", "") for ln in lines[:MAX_TEXT_LINES]]
        out.append(">>>")
    return "\n".join(out)


def _clean(data, active_ids, categories):
    """The model's JSON -> [{text, id, guess, category_id}]. Unknown ids
    become null (the line goes to "Needs a hand"); unknown categories drop."""
    cat_ids = {c.name.lower(): c.id for c in categories}
    out = []
    entries = data.get("lines") if isinstance(data, dict) else None
    for e in (entries or [])[:MAX_LINES]:
        if not isinstance(e, dict):
            continue
        text = str(e.get("text") or "").strip()[:120]
        guess = str(e.get("guess") or "").strip()[:60] or None
        if not (text or guess):
            continue
        try:
            iid = int(e["id"]) if e.get("id") is not None else None
        except (TypeError, ValueError):
            iid = None
        out.append({
            "text": text or guess,
            "id": iid if iid in active_ids else None,
            "guess": guess,
            "category_id": cat_ids.get(str(e.get("category") or "").strip().lower()),
        })
    return out


def read(cfg, user_id, image=None, lines=None):
    """One call on LLM_MODEL. image: (bytes, mime) for a receipt photo, or
    lines: [str] for pasted text. Returns {ok, lines, error}; ok=False only
    when the call itself failed. Always records an AiCall row."""
    kind = "receipt" if image is not None else "match"
    catalogue_rows = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.name).all()
    categories = Category.query.order_by(*Category.ordering()).all()
    prompt = build_prompt([(i.id, i.name) for i in catalogue_rows],
                          [c.name for c in categories],
                          None if image is not None else lines)
    call = AiCall(user_id=user_id, kind=kind, status="error")
    result = {"ok": False, "lines": [], "error": None}
    provider = None
    try:
        provider = get_provider(cfg, max_tokens=RECEIPT_MAX_TOKENS, temperature=RECEIPT_TEMPERATURE)
        call.model = f"{provider.name}:{provider.model}"
        text = provider.generate(SYSTEM_PROMPT, prompt, json_mode=True, thinking="low",
                                 images=[image] if image is not None else None)
        data = json.loads((text or "").strip().removeprefix("```json").removesuffix("```"))
        result["lines"] = _clean(data, {i.id for i in catalogue_rows}, categories)
        result["ok"] = True
        call.status = "done"
    except (ProviderError, ValueError) as e:
        result["error"] = str(e)
    finally:
        usage = (getattr(provider, "last_usage", None) or {}) if provider else {}
        call.input_tokens = usage.get("input")
        call.output_tokens = usage.get("output")
        db.session.add(call)
        db.session.commit()
    return result
