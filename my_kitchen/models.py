from datetime import datetime, timezone

from .extensions import db

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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

# Dietary tag types (spec section 3): an allergy is a hard, must-never-include
# exclusion; a preference is a soft steer. Single source of truth, shared by the
# tag manager form and the brief-building split. Mirrors SECTION_CHOICES.
TAG_TYPE_CHOICES = [
    ("allergy", "Allergy (hard exclusion)"),
    ("preference", "Preference (soft steer)"),
]
TAG_TYPE_KEYS = {key for key, _ in TAG_TYPE_CHOICES}

# Meal types for the cook wizard (Phase 11). Hardcoded single source of truth —
# the DB-backed configurable version is deferred to the keystone phase. Each
# entry carries a `takes_cuisine` flag: cuisine-bearing types show the cuisine
# control and feed a cuisine line into the brief; non-cuisine types hide it and
# force cuisine to None (so a future "meal-type + cuisine" query stays clean).
# Lives here (not in wizard/routes.py) so llm/service.py can import the flag
# without a circular import — same pattern as SECTION_CHOICES above.
MEAL_TYPES = [
    ("Breakfast", True),
    ("Lunch", True),
    ("Dinner", True),
    ("Snack", True),
    ("Side dish", True),
    ("Dessert", False),
    ("Baking", False),
    ("Sauce or dressing", False),
]
MEAL_TYPE_NAMES = [name for name, _ in MEAL_TYPES]
DEFAULT_MEAL_TYPE = "Dinner"
_MEAL_TYPE_TAKES_CUISINE = {name: takes for name, takes in MEAL_TYPES}

# Cuisines (Phase 17). Kept here, not in wizard/routes.py, so llm/service.py can
# import the normaliser without a circular import (same reason as MEAL_TYPES).
# CUISINES are the real, taggable cuisines; the wizard additionally offers
# "Surprise me" — an open-choice request, NOT a tag.
CUISINES = ["Italian", "Mediterranean", "British", "Asian"]
SURPRISE_ME = "Surprise me"
WIZARD_CUISINES = CUISINES + [SURPRISE_ME]


def recipe_cuisine_from(value):
    """Map a generation's requested cuisine to a recipe cuisine TAG. 'Surprise me'
    and None/'' aren't real cuisines -> None; a concrete one is kept (validated
    against CUISINES so a stray value can't become a bogus tag)."""
    if not value or value == SURPRISE_ME:
        return None
    return value if value in CUISINES else None


def meal_type_takes_cuisine(name):
    """True if the meal type carries a cuisine. Unknown names default to True
    (never accidentally suppress cuisine for an unrecognised value — callers
    validate the name against MEAL_TYPE_NAMES separately)."""
    return _MEAL_TYPE_TAKES_CUISINE.get(name, True)

def utcnow():
    """Timezone-aware UTC now; works on 3.11 and avoids the 3.12 utcnow() deprecation."""
    return datetime.now(timezone.utc)


# --- association table for users <-> dietary tags (Phase 1; empty in the MVP) ---
user_dietary_tags = db.Table(
    "user_dietary_tags",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("dietary_tags.id"), primary_key=True),
)

# --- association table for users <-> favourited recipes ---
# Favourites are per-user: recipes are shared objects (two per generation, either
# viewable by anyone), so a flag on the recipe can't say *who* favourited it.
# This join is the relationship — mirrors user_dietary_tags.
recipe_favourites = db.Table(
    "recipe_favourites",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id"), primary_key=True),
)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    dietary_tags = db.relationship(
        "DietaryTag", secondary=user_dietary_tags, backref="users"
    )

    # Per-user favourites. backref gives Recipe.favourited_by (the users who
    # favourited that recipe), used to render the star state per logged-in user.
    favourite_recipes = db.relationship(
        "Recipe", secondary=recipe_favourites, backref="favourited_by"
    )

    # UserMixin supplies is_authenticated / is_anonymous / get_id(). Our own
    # is_active *column* shadows UserMixin's always-True version — exactly what
    # we want: Flask-Login's login_user() refuses a user whose is_active is
    # False, so a retired user can't log in.
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)


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
    # meal_type: e.g. "Dinner" (default) or "Dessert". Nullable parallel to
    # cuisine (Phase 11). recipes.meal_type belongs to the later keystone
    # migration — NOT here.
    meal_type = db.Column(db.String, nullable=True)
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
    # status: "running" | "done" | "error" (Phase 12, async generation). The
    # Generation row IS the job — no separate jobs table. NULL means a legacy,
    # pre-Phase-12 row: it predates async and is already complete, so every
    # status branch MUST treat NULL as "done" (historical rows still render in
    # history/choice). Set "running" by the synchronous starter, then "done" or
    # "error" by the background thread (or by the poll's stale guard).
    status = db.Column(db.String, nullable=True)

    recipes = db.relationship("Recipe", backref="generation")
    # Read-only link to the cook. The created_by_user_id FK column already
    # exists, so this is ORM-level only — no migration, and autogenerate won't
    # report a schema diff from it.
    created_by = db.relationship("User")

class Recipe(db.Model):
    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    # generation_id is NULLABLE from the keystone (Phase 3b): AI recipes carry one,
    # but user-created and imported recipes (later phases) have no generation.
    generation_id = db.Column(db.Integer, db.ForeignKey("generations.id"), nullable=True)
    title = db.Column(db.String, nullable=False)
    blurb = db.Column(db.String, nullable=True)
    # intro: energetic context paragraph (the why / culinary framing). Phase 4b.
    intro = db.Column(db.Text, nullable=True)
    servings = db.Column(db.Integer, nullable=True)
    # ingredients_json: [{item, amount, unit, to_buy}]. Stays the DISPLAY source
    # in 3b — the new recipe_ingredients rows are the structured/queryable mirror,
    # not yet shown on the recipe page (that's the user-created-recipes phase).
    ingredients_json = db.Column(db.JSON, nullable=True)
    # prep_steps_json / cook_steps_json: [{title, text, timer_minutes}]
    prep_steps_json = db.Column(db.JSON, nullable=True)
    cook_steps_json = db.Column(db.JSON, nullable=True)
    # tips_json: optional [{title, text}] — finishing touches / serving / troubleshooting. Phase 4b.
    tips_json = db.Column(db.JSON, nullable=True)
    was_chosen = db.Column(db.Boolean, default=False, nullable=False)
    raw_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    # --- Keystone meta (Phase 3b) ---
    # source: provenance — "ai" | "user" | "imported". NOT NULL; every recipe is
    # "ai" this phase and the write path sets it explicitly. Added via the
    # temp-server_default-then-drop Alembic pattern so the migration is safe on a
    # populated table; the steady-state column carries no DB default, keeping the
    # write path authoritative (an unset source fails loudly — desirable).
    source = db.Column(db.String, nullable=False)
    # meal_type: copied FORWARD from the generation at write time so post-3b
    # recipes are suggestion-ready. Nullable (legacy generations; user/imported
    # provenance later). recipes.meal_type is owned here, not on generations.
    meal_type = db.Column(db.String, nullable=True)
    # cuisine: the recipe's cuisine TAG (Phase 17). Nullable — not every recipe has
    # one (non-cuisine meal types, "Surprise me" generations, or simply untagged).
    # For AI recipes, copied forward from the generation at write time. Editable on
    # the recipe page + the create/edit form; gated by meal type (only cuisine-
    # bearing meal types keep it).
    cuisine = db.Column(db.String, nullable=True)
    # time_band: the recipe's "quick" | "relaxed" tag (Phase 18). DISPLAY ONLY —
    # it drives the suggestion card's time badge and is NEVER part of the
    # suggestions match query. Nullable: AI recipes copy it forward from the
    # generation; user recipes set it on the create/edit form ("no time" = NULL);
    # legacy / imported rows may have none.
    time_band = db.Column(db.String, nullable=True)
    # created_by_user_id: the recipe's author. For AI recipes = the generation's
    # cook. Nullable FK (user/imported provenance comes later).
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Structured, catalogue-linked ingredient lines (Phase 3b). order_by position
    # so the collection mirrors the recipe's ingredient order; delete-orphan so a
    # deleted recipe takes its lines with it (recipe_id is NOT NULL — no orphans).
    ingredients = db.relationship(
        "RecipeIngredient",
        backref="recipe",
        order_by="RecipeIngredient.position",
        cascade="all, delete-orphan",
    )
    # Read-only link to the author. The created_by_user_id FK column carries the
    # value; this is ORM-level only, so it reports no schema diff.
    author = db.relationship("User")


class RecipeIngredient(db.Model):
    """One ingredient line of a recipe, linked (when resolved) to the catalogue.

    Keystone Phase 3b — the migration that makes ingredients a first-class,
    joinable table. ``raw_text`` preserves the AI's original ingredient string for
    display; ``ingredient_id`` is the resolver's catalogue link, NULL when
    unmatched (off-catalogue, or a genuine catalogue gap — both degrade
    gracefully). ``amount``/``unit``/``to_buy``/``position`` are copied verbatim
    from the AI output. ``amount`` is stored as text on purpose: the model emits
    it untouched (``"a splash"``, ``"½"``, ``2``), so a numeric column would lose
    or reject those — ``raw_text`` plus a string amount/unit preserve display
    fidelity. This table is the authoritative structured source the user-created
    recipes phase makes editable, and the suggestions query later joins on
    ``ingredient_id``.
    """
    __tablename__ = "recipe_ingredients"
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"), nullable=True)
    raw_text = db.Column(db.String, nullable=False)
    amount = db.Column(db.String, nullable=True)
    unit = db.Column(db.String, nullable=True)
    to_buy = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, nullable=False)

    # Read-only link to the catalogue ingredient (None when unmatched).
    ingredient = db.relationship("Ingredient")
