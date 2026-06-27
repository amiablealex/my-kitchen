"""Dormant DB-backed wrapper (Phase 3a).

In 3b this loads the live catalogue (active ``Ingredient`` rows -> ``(id, name)``)
plus the curated ``ALIASES`` constant and delegates to ``core.resolve``. It is
NOT called anywhere in 3a — the resolver's only 3a consumer is the eval harness,
which injects a DB-free fixture. Defined now so 3b inherits a stable surface.

``models`` is imported lazily (inside the functions) so importing this module
stays import-light — no app/DB context needed just to reach the pure core.
"""
from .aliases import ALIASES
from .core import resolve, ResolveResult, UNMATCHED  # noqa: F401  (re-exported for 3b)


def load_catalogue():
    """Live catalogue as ``[(ingredient_id, name), ...]`` for resolution.

    Includes staples (they are valid resolution targets — e.g. "extra virgin
    olive oil" -> Olive oil) and excludes only retired (``is_active=False``)
    ingredients. Requires an app/DB context.
    """
    from ..models import Ingredient
    rows = Ingredient.query.filter_by(is_active=True).all()
    return [(i.id, i.name) for i in rows]


def resolve_text(free_text):
    """Resolve free text against the LIVE catalogue + curated aliases.

    DORMANT in 3a — wired into the ingestion / recipe paths in 3b. Requires an
    app/DB context.
    """
    return resolve(free_text, load_catalogue(), ALIASES)
