"""Shared stock-editing logic for the /stock route.

The "pantry view": only what's actually IN STOCK, grouped by category.
Staples (assumed always available) and retired ingredients are excluded from the
pantry itself. The catalogue search, however, returns matches in ANY state so the
add-to-stock UI can render each correctly and never dead-ends.
"""
from ..extensions import db
from ..models import Category, Ingredient


def in_stock_groups():
    """[(category, [ingredients]) ...] for in-stock, active, non-staple items."""
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
