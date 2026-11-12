"""Shared stock-editing logic for the /stock route.

The "pantry view": only what's actually IN STOCK, grouped by category.
Staples (assumed always available) and retired ingredients are excluded from the
pantry itself. The catalogue search, however, returns matches in ANY state so the
add-to-stock UI can render each correctly and never dead-ends.
"""
import re

from ..extensions import db
from ..models import Category, Ingredient
from ..resolver import build_index, resolve_with_index
from ..resolver.aliases import ALIASES
from ..resolver.db import load_catalogue


def in_stock_groups():
    """[(category, [ingredients]) ...] for in-stock, active, non-staple items."""
    categories = Category.query.order_by(*Category.ordering()).all()
    groups = []
    for cat in categories:
        items = sorted(
            [i for i in cat.ingredients
             if i.in_stock and i.is_active and not i.is_staple],
            key=lambda i: i.name.lower(),
        )
        if items:
            groups.append((cat, items))
    return groups


def search_catalogue(query, limit=25):
    """Active ingredients matching `query`, whatever their stock/staple state.

    Unlike a pure "addable" search, this includes in-stock and staple matches, so
    the stock page can label each (add / already in stock / staple) and never
    dead-ends — searching a staple shows it as a staple instead of appearing
    absent. Blank query returns nothing. Alphabetical, capped at `limit`.
    """
    q = (query or "").strip()
    if not q:
        return []
    # Escape LIKE wildcards so "100%" / "a_b" match literally.
    esc = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{esc}%"
    return (
        Ingredient.query
        .filter(
            Ingredient.is_active.is_(True),
            db.func.lower(Ingredient.name).like(pattern, escape="\\"),
        )
        .order_by(db.func.lower(Ingredient.name))
        .limit(limit)
        .all()
    )


# --- Quick-add from a list (Phase 32) -----------------------------------------
# A pasted list can be long (an order email); past this it's not a stock update.
LIST_MAX_ITEMS = 80

_SPLIT = re.compile(r"[\n,;]+")
_BULLET = re.compile(r"^\s*(?:[-*•·]+|\d+[.)])\s+")
_PRICE = re.compile(r"(?:£\s*)?-?\d+\.\d{2}\s*[A-Z]?\s*$")   # trailing "£1.25", "1.25 A"
# Receipt/order furniture that isn't an item. First-word match, case-blind.
_NOT_ITEMS = {"total", "subtotal", "sub-total", "balance", "change", "cash", "card",
              "visa", "mastercard", "amex", "vat", "savings", "saving", "clubcard",
              "nectar", "points", "delivery", "bag", "bags", "carrier"}
_MULTI = re.compile(r"^\s*\d+\s*[x×@]\s*|\s*[x×]\s*\d+\s*$", re.I)  # "2 x milk", "milk x2"


def split_list(text):
    """Raw text -> cleaned item lines, in order, de-duplicated (case-blind).
    Splits on line breaks, commas and semicolons; strips bullets, numbering,
    trailing prices and multipliers. Lines with no letters are dropped."""
    out, seen = [], set()
    for part in _SPLIT.split(text or ""):
        line = _BULLET.sub("", part)
        line = _PRICE.sub("", line)
        line = _MULTI.sub("", line).strip(" \t-–—:.")
        if not re.search(r"[A-Za-z]", line):
            continue
        if line.split()[0].lower().strip(":") in _NOT_ITEMS:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= LIST_MAX_ITEMS:
            break
    return out


def classify(entries):
    """Matched lines -> the stock sheet's contents. Every id is checked here
    against the live catalogue, whoever proposed it (the resolver or an AI).

    entries: [{text, id|None, guess, category_id, loose}]. `loose` marks a
    fuzzy resolver hit, which is not trusted onto a staple.

    Returns {matched, unplaced, already, staples}:
      matched  — [{id, name, section, raw}] to stock; `raw` is the line as
                 written, only when it differs from the name (the sheet shows
                 it, and an unticked guess drops to "Needs a hand").
      unplaced — [{text, guess, category_id}] lines nobody could place. A loose
                 hit on a staple lands here too: "peppers" -> Black pepper
                 would otherwise be silently skipped as a staple.
      already  — count already in stock; staples — count of staple hits
                 (assumed always available, so nothing to do).
    """
    by_id = {i.id: i for i in Ingredient.query.filter_by(is_active=True)}
    matched, unplaced, seen, seen_text = [], [], set(), set()
    already = staples = 0
    for e in entries:
        ing = by_id.get(e.get("id"))
        if ing is None or (ing.is_staple and e.get("loose")):
            key = e["text"].lower()
            if key not in seen_text:
                seen_text.add(key)
                unplaced.append({"text": e["text"], "guess": e.get("guess") or e["text"],
                                 "category_id": e.get("category_id")})
            continue
        if ing.id in seen:
            continue
        seen.add(ing.id)
        if ing.is_staple:
            staples += 1
        elif ing.in_stock:
            already += 1
        else:
            matched.append({
                "id": ing.id, "name": ing.name, "section": ing.category.section,
                "raw": e["text"] if e["text"].lower() != ing.name.lower() else "",
            })
    return {"matched": matched, "unplaced": unplaced, "already": already, "staples": staples}


def parse_list(text, ai_match=None):
    """A pasted/typed list -> the stock sheet's contents. The resolver places
    what it can, locally. If `ai_match` is given (a callable taking the
    leftover lines and returning entries, or None on failure), ONLY the lines
    the resolver couldn't place are sent to it (Phase 33); a failure just
    leaves them for "Needs a hand"."""
    lines = split_list(text)
    index = build_index(load_catalogue(), ALIASES)
    staple_ids = {i.id for i in Ingredient.query.filter_by(is_active=True, is_staple=True)}
    placed, leftover = [], []
    for line in lines:
        res = resolve_with_index(line, index)
        loose = res.method == "fuzzy"
        entry = {"text": line, "id": res.ingredient_id, "guess": line,
                 "category_id": None, "loose": loose}
        unsure = res.ingredient_id is None or (loose and res.ingredient_id in staple_ids)
        (leftover if unsure else placed).append(entry)
    if leftover and ai_match is not None:
        ai_entries = ai_match([e["text"] for e in leftover])
        if ai_entries is not None:
            leftover = ai_entries
    return classify(placed + leftover)


def sheet_catalogue():
    """What "Needs a hand" can search: active, non-staple ingredients (staples
    are assumed, never stocked). [{id, name, section}], alphabetical."""
    rows = (Ingredient.query.filter_by(is_active=True, is_staple=False)
            .order_by(db.func.lower(Ingredient.name)).all())
    return [{"id": i.id, "name": i.name, "section": i.category.section} for i in rows]


def set_stock(ids, in_stock):
    """Set in_stock on the given active, non-staple ingredients. Returns the ids
    that actually changed, so Undo flips exactly those back."""
    if not ids:
        return []
    rows = Ingredient.query.filter(
        Ingredient.id.in_(ids), Ingredient.is_active.is_(True),
        Ingredient.is_staple.is_(False), Ingredient.in_stock.isnot(in_stock),
    ).all()
    for r in rows:
        r.in_stock = in_stock
    db.session.commit()
    return [r.id for r in rows]
