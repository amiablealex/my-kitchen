from datetime import datetime, timezone

from .extensions import db


# The four fixed wizard lanes. Category *names* are freely configurable, but a
# category must map to one of these sections (spec section 3). Single source of
# truth, shared by the cook wizard (lane grouping) and the category manager.
SECTION_CHOICES = [
    ("protein", "Protein"),
    ("carb", "Carb"),
    ("veg", "Veg"),
    ("other", "Other"),
]
SECTION_KEYS = {key for key, _ in SECTION_CHOICES}


def utcnow():
    """Timezone-aware UTC now; works on 3.11 and avoids the 3.12 utcnow() deprecation."""
    return datetime.now(timezone.utc)


# --- association table for users <-> dietary tags (Phase 1; empty in the MVP) ---
user_dietary_tags = db.Table(
    "user_dietary_tags",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("dietary_tags.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=True)  # populated in Phase 1 (auth)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    dietary_tags = db.relationship(
        "DietaryTag", secondary=user_dietary_tags, backref="users"
    )


class DietaryTag(db.Model):
    __tablename__ = "dietary_tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    # type: "preference" | "allergy"  (string for create_all flexibility)
    type = db.Column(db.String, nullable=False, default="preference")


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    # section: "protein" | "carb" | "veg" | "other"  (the four fixed wizard lanes)
    section = db.Column(db.String, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    ingredients = db.relationship("Ingredient", backref="category")


class Ingredient(db.Model):
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    is_staple = db.Column(db.Boolean, default=False, nullable=False)
    in_stock = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    note = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Equipment(db.Model):
    __tablename__ = "equipment"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)


class Generation(db.Model):
    __tablename__ = "generations"
    id = db.Column(db.Integer, primary_key=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    cuisine = db.Column(db.String, nullable=True)
    # time_band: "quick" | "relaxed"
    time_band = db.Column(db.String, nullable=True)
    servings = db.Column(db.Integer, nullable=True)
    cooking_for_user_ids = db.Column(db.JSON, nullable=True)
    guest_count = db.Column(db.Integer, default=0, nullable=False)
    selected_ingredient_ids = db.Column(db.JSON, nullable=True)
    creative_seed = db.Column(db.String, nullable=True)
    model = db.Column(db.String, nullable=True)
    raw_prompt = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)

    recipes = db.relationship("Recipe", backref="generation")


class Recipe(db.Model):
    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.Integer, db.ForeignKey("generations.id"), nullable=False)
    title = db.Column(db.String, nullable=False)
    blurb = db.Column(db.String, nullable=True)
    servings = db.Column(db.Integer, nullable=True)
    # ingredients_json: [{item, amount, unit, to_buy}]
    ingredients_json = db.Column(db.JSON, nullable=True)
    # prep_steps_json / cook_steps_json: [{title, text, timer_minutes}]
    prep_steps_json = db.Column(db.JSON, nullable=True)
    cook_steps_json = db.Column(db.JSON, nullable=True)
    was_chosen = db.Column(db.Boolean, default=False, nullable=False)
    is_favourite = db.Column(db.Boolean, default=False, nullable=False)
    raw_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
