"""Catalogue management UI (Phase 1).

A single-user, unstyled CRUD area for the kitchen catalogue:
ingredients (this checkpoint), then categories and equipment.

Stock state (in_stock / note) is NOT edited here — that stays on the stock
list. This area manages the catalogue itself: what ingredients exist, what
category they're in, whether they're staples, and whether they're active.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
)
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Category, Ingredient, Equipment, DietaryTag,
    SECTION_CHOICES, SECTION_KEYS, TAG_TYPE_CHOICES, TAG_TYPE_KEYS,
)

manage_bp = Blueprint("manage", __name__, url_prefix="/manage")


@manage_bp.route("/")
def index():
    return render_template("manage/index.html")


# ---------------------------------------------------------------- ingredients

def _ordered_categories():
    return Category.query.order_by(Category.display_order, Category.name).all()


def _name_taken(name, exclude_id=None):
    """Case-insensitive duplicate check (friendlier than the raw unique index)."""
    q = Ingredient.query.filter(db.func.lower(Ingredient.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(Ingredient.id != exclude_id)
    return q.first() is not None


def _parse_ingredient_form():
    """Pull + validate the shared add/edit fields. Returns (data, error)."""
    name = (request.form.get("name") or "").strip()
    category_id = request.form.get("category_id", type=int)
    is_staple = request.form.get("is_staple") == "on"
    if not name:
        return None, "Name is required."
    if category_id is None or db.session.get(Category, category_id) is None:
        return None, "Please choose a valid category."
    return {"name": name, "category_id": category_id, "is_staple": is_staple}, None


@manage_bp.route("/ingredients")
def ingredients():
    cats = _ordered_categories()
    all_items = Ingredient.query.order_by(Ingredient.name).all()
    active = [i for i in all_items if i.is_active]
    retired = [i for i in all_items if not i.is_active]
    # ?name= pre-fills the add form, for the "add a new ingredient" hand-off
    # from the stock search box.
    prefill_name = (request.args.get("name") or "").strip()
    return render_template(
        "manage/ingredients.html",
        categories=cats, active=active, retired=retired,
        prefill_name=prefill_name,
    )


@manage_bp.route("/ingredients/add", methods=["POST"])
def ingredient_add():
    data, error = _parse_ingredient_form()
    if error:
        flash(error, "error")
        return redirect(url_for("manage.ingredients"))
    if _name_taken(data["name"]):
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.ingredients"))
    db.session.add(Ingredient(
        name=data["name"], category_id=data["category_id"],
        is_staple=data["is_staple"], in_stock=False, is_active=True,
    ))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.ingredients"))
    flash(f'Added "{data["name"]}".', "success")
    return redirect(url_for("manage.ingredients"))


@manage_bp.route("/ingredients/<int:ingredient_id>/edit", methods=["GET", "POST"])
def ingredient_edit(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    if request.method == "POST":
        data, error = _parse_ingredient_form()
        if error:
            flash(error, "error")
            return redirect(url_for("manage.ingredient_edit", ingredient_id=ing.id))
        if _name_taken(data["name"], exclude_id=ing.id):
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.ingredient_edit", ingredient_id=ing.id))
        ing.name = data["name"]
        ing.category_id = data["category_id"]
        ing.is_staple = data["is_staple"]
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.ingredient_edit", ingredient_id=ing.id))
        flash(f'Saved "{ing.name}".', "success")
        return redirect(url_for("manage.ingredients"))
    return render_template("manage/ingredient_edit.html",
                           ing=ing, categories=_ordered_categories())


@manage_bp.route("/ingredients/<int:ingredient_id>/retire", methods=["POST"])
def ingredient_retire(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    ing.is_active = False
    db.session.commit()
    flash(f'Retired "{ing.name}" — hidden from the stock list and the cook wizard, '
          'kept in history. Reactivate it any time.', "success")
    return redirect(url_for("manage.ingredients"))


@manage_bp.route("/ingredients/<int:ingredient_id>/activate", methods=["POST"])
def ingredient_activate(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    ing.is_active = True
    db.session.commit()
    flash(f'Reactivated "{ing.name}".', "success")
    return redirect(url_for("manage.ingredients"))


@manage_bp.route("/ingredients/<int:ingredient_id>/delete", methods=["POST"])
def ingredient_delete(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    name = ing.name
    db.session.delete(ing)
    db.session.commit()
    flash(f'Permanently deleted "{name}".', "success")
    return redirect(url_for("manage.ingredients"))


# ----------------------------------------------------------------- categories

def _category_name_taken(name, exclude_id=None):
    q = Category.query.filter(db.func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(Category.id != exclude_id)
    return q.first() is not None


def _next_display_order():
    highest = db.session.query(db.func.max(Category.display_order)).scalar()
    return (highest or 0) + 1


def _parse_category_form():
    """Pull + validate the shared add/edit fields. Returns (data, error)."""
    name = (request.form.get("name") or "").strip()
    section = (request.form.get("section") or "").strip()
    order_raw = request.form.get("display_order", type=int)
    if not name:
        return None, "Name is required."
    if section not in SECTION_KEYS:
        return None, "Please choose a valid section."
    display_order = order_raw if order_raw is not None else _next_display_order()
    return {"name": name, "section": section, "display_order": display_order}, None


@manage_bp.route("/categories")
def categories():
    cats = Category.query.order_by(Category.display_order, Category.name).all()
    # ingredient counts (active + retired) drive the delete guard + display
    counts = {c.id: len(c.ingredients) for c in cats}
    return render_template(
        "manage/categories.html",
        categories=cats, counts=counts,
        sections=SECTION_CHOICES, next_order=_next_display_order(),
    )


@manage_bp.route("/categories/add", methods=["POST"])
def category_add():
    data, error = _parse_category_form()
    if error:
        flash(error, "error")
        return redirect(url_for("manage.categories"))
    if _category_name_taken(data["name"]):
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.categories"))
    db.session.add(Category(**data))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.categories"))
    flash(f'Added "{data["name"]}".', "success")
    return redirect(url_for("manage.categories"))


@manage_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
def category_edit(category_id):
    cat = db.session.get(Category, category_id)
    if cat is None:
        abort(404)
    if request.method == "POST":
        data, error = _parse_category_form()
        if error:
            flash(error, "error")
            return redirect(url_for("manage.category_edit", category_id=cat.id))
        if _category_name_taken(data["name"], exclude_id=cat.id):
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.category_edit", category_id=cat.id))
        cat.name = data["name"]
        cat.section = data["section"]
        cat.display_order = data["display_order"]
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.category_edit", category_id=cat.id))
        flash(f'Saved "{cat.name}".', "success")
        return redirect(url_for("manage.categories"))
    return render_template(
        "manage/category_edit.html",
        cat=cat, sections=SECTION_CHOICES, ingredient_count=len(cat.ingredients),
    )


@manage_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def category_delete(category_id):
    cat = db.session.get(Category, category_id)
    if cat is None:
        abort(404)
    # Guard: ingredients.category_id is NOT NULL, so a category with any
    # ingredients (active OR retired) can't be deleted without orphaning them.
    n = len(cat.ingredients)
    if n:
        flash(
            f'Can\u2019t delete "{cat.name}" \u2014 it still has {n} '
            f'ingredient{"s" if n != 1 else ""} (including any retired ones). '
            "Move them to another category or remove them first.",
            "error",
        )
        return redirect(url_for("manage.categories"))
    name = cat.name
    db.session.delete(cat)
    db.session.commit()
    flash(f'Deleted "{name}".', "success")
    return redirect(url_for("manage.categories"))


# ------------------------------------------------------------------ equipment

def _equipment_name_taken(name, exclude_id=None):
    """Courtesy case-insensitive duplicate check. Equipment names aren't a DB
    unique constraint (free text by design), but exact dupes are just clutter."""
    q = Equipment.query.filter(db.func.lower(Equipment.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(Equipment.id != exclude_id)
    return q.first() is not None


@manage_bp.route("/equipment")
def equipment():
    items = Equipment.query.order_by(Equipment.name).all()
    return render_template("manage/equipment.html", items=items)


@manage_bp.route("/equipment/add", methods=["POST"])
def equipment_add():
    name = (request.form.get("name") or "").strip()
    is_available = request.form.get("is_available") == "on"
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("manage.equipment"))
    if _equipment_name_taken(name):
        flash(f'"{name}" is already in your equipment list.', "error")
        return redirect(url_for("manage.equipment"))
    db.session.add(Equipment(name=name, is_available=is_available))
    db.session.commit()
    flash(f'Added "{name}".', "success")
    return redirect(url_for("manage.equipment"))


@manage_bp.route("/equipment/<int:equipment_id>/edit", methods=["GET", "POST"])
def equipment_edit(equipment_id):
    item = db.session.get(Equipment, equipment_id)
    if item is None:
        abort(404)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        is_available = request.form.get("is_available") == "on"
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("manage.equipment_edit", equipment_id=item.id))
        if _equipment_name_taken(name, exclude_id=item.id):
            flash(f'"{name}" is already in your equipment list.', "error")
            return redirect(url_for("manage.equipment_edit", equipment_id=item.id))
        item.name = name
        item.is_available = is_available
        db.session.commit()
        flash(f'Saved "{item.name}".', "success")
        return redirect(url_for("manage.equipment"))
    return render_template("manage/equipment_edit.html", item=item)


@manage_bp.route("/equipment/<int:equipment_id>/toggle", methods=["POST"])
def equipment_toggle(equipment_id):
    item = db.session.get(Equipment, equipment_id)
    if item is None:
        abort(404)
    item.is_available = not item.is_available
    db.session.commit()
    state = "available" if item.is_available else "unavailable"
    flash(f'Marked "{item.name}" {state}.', "success")
    return redirect(url_for("manage.equipment"))


@manage_bp.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
def equipment_delete(equipment_id):
    item = db.session.get(Equipment, equipment_id)
    if item is None:
        abort(404)
    name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f'Deleted "{name}".', "success")
    return redirect(url_for("manage.equipment"))

# -------------------------------------------------------------- dietary tags

def _tag_name_taken(name, exclude_id=None):
    """Case-insensitive duplicate check, consistent with ingredients/categories
    and the users name guard."""
    q = DietaryTag.query.filter(db.func.lower(DietaryTag.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(DietaryTag.id != exclude_id)
    return q.first() is not None


def _parse_tag_form():
    """Pull + validate the shared add/edit fields. Returns (data, error)."""
    name = (request.form.get("name") or "").strip()
    type_ = (request.form.get("type") or "").strip()
    if not name:
        return None, "Name is required."
    if type_ not in TAG_TYPE_KEYS:
        return None, "Please choose a valid type."
    return {"name": name, "type": type_}, None


@manage_bp.route("/dietary-tags")
def dietary_tags():
    tags = DietaryTag.query.order_by(DietaryTag.type, db.func.lower(DietaryTag.name)).all()
    # how many users each tag is assigned to — drives the delete confirmation
    counts = {t.id: len(t.users) for t in tags}
    return render_template(
        "manage/dietary_tags.html",
        tags=tags, counts=counts, types=TAG_TYPE_CHOICES,
    )


@manage_bp.route("/dietary-tags/add", methods=["POST"])
def dietary_tag_add():
    data, error = _parse_tag_form()
    if error:
        flash(error, "error")
        return redirect(url_for("manage.dietary_tags"))
    if _tag_name_taken(data["name"]):
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.dietary_tags"))
    db.session.add(DietaryTag(**data))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.dietary_tags"))
    flash(f'Added "{data["name"]}".', "success")
    return redirect(url_for("manage.dietary_tags"))


@manage_bp.route("/dietary-tags/<int:tag_id>/edit", methods=["GET", "POST"])
def dietary_tag_edit(tag_id):
    tag = db.session.get(DietaryTag, tag_id)
    if tag is None:
        abort(404)
    if request.method == "POST":
        data, error = _parse_tag_form()
        if error:
            flash(error, "error")
            return redirect(url_for("manage.dietary_tag_edit", tag_id=tag.id))
        if _tag_name_taken(data["name"], exclude_id=tag.id):
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.dietary_tag_edit", tag_id=tag.id))
        tag.name = data["name"]
        tag.type = data["type"]
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(f'"{data["name"]}" already exists.', "error")
            return redirect(url_for("manage.dietary_tag_edit", tag_id=tag.id))
        flash(f'Saved "{tag.name}".', "success")
        return redirect(url_for("manage.dietary_tags"))
    return render_template(
        "manage/dietary_tag_edit.html",
        tag=tag, types=TAG_TYPE_CHOICES, user_count=len(tag.users),
    )


@manage_bp.route("/dietary-tags/<int:tag_id>/delete", methods=["POST"])
def dietary_tag_delete(tag_id):
    tag = db.session.get(DietaryTag, tag_id)
    if tag is None:
        abort(404)
    # Unlike categories (NOT NULL FK) and users (history attribution), a tag has
    # no immutable historical dependency: generations store user ids, not a tag
    # snapshot. So hard delete is safe — SQLAlchemy clears the user_dietary_tags
    # join rows for us as the tag is removed.
    name = tag.name
    db.session.delete(tag)
    db.session.commit()
    flash(f'Deleted "{name}".', "success")
    return redirect(url_for("manage.dietary_tags"))
