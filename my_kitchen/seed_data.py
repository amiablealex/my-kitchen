"""Shared seed routines for the `seed` and `first-run-seed` CLI commands.

Import-light (models only) so it runs in the HA add-on first-run path too.
"""
import secrets

from .extensions import db
from . import models

# (name, section, display_order)
_CATEGORIES = [
    ("Protein", "protein", 1),
    ("Carbohydrate", "carb", 2),
    ("Vegetable", "veg", 3),
    ("Dairy", "other", 4),
    ("Spice", "other", 5),
    ("Oil", "other", 6),
    ("Pantry", "other", 7),
]

# (name, category, is_staple, in_stock)
_INGREDIENTS = [
    ("Chicken breast", "Protein", False, True),
    ("Salmon fillet", "Protein", False, False),
    ("Eggs", "Protein", False, True),
    ("Tofu", "Protein", False, False),
    ("Rice", "Carbohydrate", False, True),
    ("Pasta", "Carbohydrate", False, True),
    ("Potatoes", "Carbohydrate", False, True),
    ("Onion", "Vegetable", False, True),
    ("Carrot", "Vegetable", False, True),
    ("Broccoli", "Vegetable", False, False),
    ("Spinach", "Vegetable", False, False),
    ("Tomato", "Vegetable", False, True),
    ("Milk", "Dairy", False, True),
    ("Cheddar cheese", "Dairy", False, True),
    ("Butter", "Dairy", False, True),
    ("Salt", "Spice", True, True),
    ("Black pepper", "Spice", True, True),
    ("Cumin", "Spice", True, True),
    ("Paprika", "Spice", True, True),
    ("Olive oil", "Oil", True, True),
    ("Vegetable oil", "Oil", True, True),
    ("Plain flour", "Pantry", True, True),
    ("Stock cubes", "Pantry", True, True),
]


def seed_reference_data():
    """Idempotently seed starter categories + ingredients. Returns True if it
    added anything, False if catalogue data was already present."""
    if models.Category.query.first() or models.Ingredient.query.first():
        return False
    cats = {}
    for name, section, order in _CATEGORIES:
        c = models.Category(name=name, section=section, display_order=order)
        db.session.add(c)
        cats[name] = c
    db.session.flush()
    for name, cat_name, staple, in_stock in _INGREDIENTS:
        db.session.add(models.Ingredient(
            name=name, category=cats[cat_name],
            is_staple=staple, in_stock=in_stock,
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
