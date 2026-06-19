"""Shared stock-editing logic, used by BOTH the standalone /stock route and
the wizard's /cook/stock step so the two surfaces stay identical.

The "pantry view": only what's actually IN STOCK, grouped by category.
Staples (assumed always available) and retired ingredients are excluded
entirely — they never appear in either surface. No schema involved; this is
purely a filtered/grouped read of the existing rows.
"""
from ..extensions import db
from ..models import Category, Ingredient


def in_stock_groups():
    """[(category, [ingredients]) ...] for in-stock, active, non-staple items.

    Ordered by the category's display_order then name; ingredients sorted
    case-insensitively within each. Empty categories are omitted so a surface
    only ever shows lanes that have something in them.
    """
    categories = Category.query.order_by(
        Category.display_order, Category.name
    ).all()
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


def search_addable(query, limit=25):
    """Ingredients you could add to stock that match `query`.

    The addable set = active, non-staple, NOT already in stock (an in-stock item
    is already in the pantry; a staple is assumed; a retired item is hidden).
    Matching is a case-insensitive substring, consistent with the case-insensitive
    duplicate guards elsewhere. A blank query returns nothing (rather than dumping
    the whole catalogue). Results are alphabetical, capped at `limit`.
    """
    q = (query or "").strip()
    if not q:
        return []
    # Escape LIKE wildcards in user input so "100%" / "a_b" match literally.
    esc = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{esc}%"
    return (
        Ingredient.query
        .filter(
            Ingredient.is_active.is_(True),
            Ingredient.is_staple.is_(False),
            Ingredient.in_stock.is_(False),
            db.func.lower(Ingredient.name).like(pattern, escape="\\"),
        )
        .order_by(db.func.lower(Ingredient.name))
        .limit(limit)
        .all()
    )
