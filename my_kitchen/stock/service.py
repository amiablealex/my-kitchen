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
