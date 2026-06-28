"""Deterministic recipe suggestions for the cook wizard (Phase 18).

Given the wizard's session state at the review step, find saved recipes the
household can cook RIGHT NOW that fit the brief. Pure DB + Python — NO LLM and
NO resolver call. This is the keystone payoff: every recipe's ingredient lines
are linked to the catalogue (recipe_ingredients.ingredient_id), so cookability
is a real structured check, not the old free-text guess.

A saved Recipe R is suggested iff ALL hold:
  * PROVENANCE — R is a chosen AI recipe (source='ai' AND was_chosen) OR any
    non-AI recipe (user / imported). The unchosen AI sibling was passed over by
    the household and is hidden from History, so it isn't suggested either.
  * MEAL-TYPE — R.meal_type == wizard meal_type (always set; defaults Dinner).
    An untagged recipe (meal_type NULL) makes no claim -> excluded.
  * CUISINE — if the wizard cuisine is the "Any"/Surprise sentinel or None, or
    the meal type is non-cuisine-bearing -> no cuisine constraint. Otherwise
    R.cuisine == wizard cuisine; untagged (NULL) -> excluded.
  * COOKABLE — every REQUIRED line (to_buy=False) is satisfiable from stock: an
    unlinked required line excludes R (can't confirm); a staple is assumed
    available; otherwise the linked ingredient must be in_stock AND is_active
    (retired -> excluded). to_buy lines are ignored (optional extras).
  * MUST-USE — every wizard must-use ingredient id appears among R's linked
    ingredient ids.

NOT filtered by: time band (display-only badge), cooking-for / allergies /
preferences (the allergy machinery stays on the generate path), or servings.

Newest-first. Household-scale bank: the cheap columns (provenance, meal_type,
and cuisine when constrained) are SQL-filtered; cookability + must-use run in
Python for clarity.
"""

from ..extensions import db
from ..models import Recipe, SURPRISE_ME, meal_type_takes_cuisine


def _cuisine_constrained(meal_type, cuisine):
    """True when a concrete cuisine must match. The 'Any'/Surprise sentinel and
    None mean 'no preference'; a non-cuisine meal type carries no cuisine."""
    if cuisine is None or cuisine == SURPRISE_ME:
        return False
    return meal_type_takes_cuisine(meal_type)


def _is_cookable(recipe):
    """Every required (non-to_buy) line must be satisfiable from current stock.
    Unlinked required line -> not cookable (can't confirm). Staple -> assumed
    available. Otherwise the linked ingredient must be in stock and active.
    A recipe with no required lines is vacuously cookable (theoretical: legacy
    row-less recipes carry meal_type NULL and are already excluded upstream)."""
    for line in recipe.ingredients:
        if line.to_buy:
            continue  # optional extra — never blocks cookability
        ing = line.ingredient
        if ing is None:
            return False  # required but unlinked — can't confirm
        if ing.is_staple:
            continue  # assumed always available
        if not (ing.in_stock and ing.is_active):
            return False
    return True


def _covers_must_use(recipe, must_use_ids):
    """Every must-use id appears among the recipe's linked ingredient ids."""
    if not must_use_ids:
        return True
    linked = {li.ingredient_id for li in recipe.ingredients if li.ingredient_id is not None}
    return set(must_use_ids).issubset(linked)


def suggest_recipes(meal_type, cuisine, must_use_ids, limit=None):
    """Saved recipes the household can cook now that fit the brief, newest-first.
    Pure DB + Python; no LLM, no resolver. `meal_type` is always set (the wizard
    defaults Dinner); `cuisine` may be a real cuisine, the Surprise sentinel, or
    None; `must_use_ids` is the wizard's selected_ingredient_ids (may be empty)."""
    q = Recipe.query.filter(
        db.or_(Recipe.source != "ai", Recipe.was_chosen.is_(True)),
        Recipe.meal_type == meal_type,
    )
    if _cuisine_constrained(meal_type, cuisine):
        q = q.filter(Recipe.cuisine == cuisine)
    q = q.order_by(Recipe.created_at.desc(), Recipe.id.desc())

    out = []
    for r in q.all():
        if not _covers_must_use(r, must_use_ids):
            continue
        if not _is_cookable(r):
            continue
        out.append(r)
        if limit is not None and len(out) >= limit:
            break
    return out
