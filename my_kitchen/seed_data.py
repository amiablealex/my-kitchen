"""Shared seed routines for the `seed` and `first-run-seed` CLI commands.

Import-light (models only) so it runs in the HA add-on first-run path too. The
catalogue *data* lives in ``seed_catalogue.py`` (a zero-import pure-data module)
so it can be the single source of truth for BOTH this seed and the DB-free
resolver eval fixture — neither can drift from the other.
"""
import secrets

from .extensions import db
from . import models
from .seed_catalogue import CATEGORIES, INGREDIENTS


def seed_reference_data():
    """Idempotently seed starter categories + ingredients. Returns True if it
    added anything, False if catalogue data was already present.

    in_stock is seeded to equal is_staple: staples are assumed always available;
    core items start out-of-stock and the household toggles real stock in the UI.
    """
    if models.Category.query.first() or models.Ingredient.query.first():
        return False
    cats = {}
    for name, section, order in CATEGORIES:
        c = models.Category(name=name, section=section, display_order=order)
        db.session.add(c)
        cats[name] = c
    db.session.flush()
    for name, cat_name, staple in INGREDIENTS:
        db.session.add(models.Ingredient(
            name=name, category=cats[cat_name],
            is_staple=staple, in_stock=staple,
        ))
    db.session.commit()
    return True


def ensure_first_user(name="Home Cook", password=None):
    """Create the first household user if none exists. Returns (name, password)
    when created (password generated if not supplied), else None."""
    if models.User.query.first():
        return None
    if password is None:
        password = secrets.token_urlsafe(12)
    user = models.User(name=name, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return (name, password)
