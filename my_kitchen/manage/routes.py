"""Catalogue management UI (Phase 1).

A single-user, unstyled CRUD area for the kitchen catalogue:
ingredients (this checkpoint), then categories and equipment.

Stock state (in_stock / note) is NOT edited here — that stays on the stock
list. This area manages the catalogue itself: what ingredients exist, what
category they're in, whether they're staples, and whether they're active.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify,
)
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Category, Ingredient, Equipment, DietaryTag, User,
    SECTION_CHOICES, SECTION_KEYS, TAG_TYPE_CHOICES, TAG_TYPE_KEYS, TAG_TYPE_HINTS,
)

manage_bp = Blueprint("manage", __name__, url_prefix="/manage")


@manage_bp.route("/")
def index():
    # A count beside each entry, so the page says something before you tap.
    counts = dict(
        ingredients=Ingredient.query.filter_by(is_active=True).count(),
        categories=Category.query.count(),
        equipment=Equipment.query.count(),
        tags=DietaryTag.query.count(),
        people=User.query.filter_by(is_active=True).count(),
    )
    return render_template("manage/index.html", counts=counts)


# ---------------------------------------------------------------- ingredients

def _ordered_categories():
    return Category.query.order_by(*Category.ordering()).all()


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
    all_items = Ingredient.query.order_by(db.func.lower(Ingredient.name)).all()
    active = [i for i in all_items if i.is_active]
    retired = [i for i in all_items if not i.is_active]
    # ?name= pre-fills the add form, for the "add a new ingredient" hand-off
    # from the stock search box.
    prefill_name = (request.args.get("name") or "").strip()
    return render_template(
        "manage/ingredients.html",
        categories=cats, sections=SECTION_CHOICES, active=active, retired=retired,
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
    flash(f'Added "{data["name"]}" — now assign it to someone on the Household '
          'page, or it won\'t reach any recipe.', "success")
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
                           ing=ing, categories=_ordered_categories(), sections=SECTION_CHOICES)


BULK_ACTIONS = {"move", "staple", "standard", "retire", "restore"}


@manage_bp.route("/ingredients/bulk", methods=["POST"])
def ingredients_bulk():
    """Several ingredients at once, from the list's select mode (0.30.0).
    Body: {"action": "move"|"staple"|"standard"|"retire"|"restore",
           "ids": [...], "category_id": n (move only),
           "previous": [{"id", "category_id", "is_staple", "is_active"}] (restore only)}.
    Returns the message for the toast plus each item's previous state, which
    the page hands back as "restore" if you tap Undo."""
    body = request.get_json(silent=True) or {}
    action = body.get("action")
    if action not in BULK_ACTIONS:
        return jsonify(ok=False, error="Unknown action."), 400

    if action == "restore":
        prev = body.get("previous") or []
        by_id = {int(p["id"]): p for p in prev if isinstance(p, dict) and str(p.get("id", "")).isdigit()}
        items = Ingredient.query.filter(Ingredient.id.in_(by_id)).all() if by_id else []
        valid_cats = {c.id for c in Category.query.all()}
        for ing in items:
            p = by_id[ing.id]
            if p.get("category_id") in valid_cats:
                ing.category_id = p["category_id"]
            ing.is_staple = bool(p.get("is_staple"))
            ing.is_active = bool(p.get("is_active"))
        db.session.commit()
        return jsonify(ok=True, message="Undone.")

    try:
        ids = [int(i) for i in body.get("ids") or []]
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Bad request."), 400
    items = Ingredient.query.filter(Ingredient.id.in_(ids)).all() if ids else []
    if not items:
        return jsonify(ok=False, error="Nothing selected."), 400
    previous = [{"id": i.id, "category_id": i.category_id,
                 "is_staple": i.is_staple, "is_active": i.is_active} for i in items]
    n = len(items)
    noun = "ingredient" if n == 1 else "ingredients"

    if action == "move":
        cat = db.session.get(Category, body.get("category_id") or 0)
        if cat is None:
            return jsonify(ok=False, error="Choose a category."), 400
        for i in items:
            i.category_id = cat.id
        message = f"Moved {n} {noun} to {cat.name}."
    elif action == "staple":
        for i in items:
            i.is_staple = True
        message = f"{n} {noun} made staple{'s' if n != 1 else ''}."
    elif action == "standard":
        for i in items:
            i.is_staple = False
        message = f"{n} {noun} moved back to standard stock."
    else:  # retire
        for i in items:
            i.is_active = False
        message = f"Retired {n} {noun}."
    db.session.commit()
    return jsonify(ok=True, message=message, previous=previous)


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


def _next_display_order(section):
    """End of the given section. display_order is a position WITHIN a section
    (0.30.0); the order itself is set by dragging on the category tree."""
    highest = (db.session.query(db.func.max(Category.display_order))
               .filter(Category.section == section).scalar())
    return (highest or 0) + 1


def _parse_category_form():
    """Pull + validate the shared add/edit fields. Returns (data, error)."""
    name = (request.form.get("name") or "").strip()
    section = (request.form.get("section") or "").strip()
    if not name:
        return None, "Name is required."
    if section not in SECTION_KEYS:
        return None, "Please choose a valid section."
    return {"name": name, "section": section}, None


@manage_bp.route("/categories")
def categories():
    cats = Category.query.order_by(*Category.ordering()).all()
    # ingredient counts (active + retired) drive the delete guard + display
    counts = {c.id: len(c.ingredients) for c in cats}
    return render_template(
        "manage/categories.html",
        categories=cats, counts=counts,
        sections=SECTION_CHOICES,
        section_totals={k: sum(counts[c.id] for c in cats if c.section == k) for k, _ in SECTION_CHOICES},
        examples={"protein": "Fish", "carb": "Grains", "veg": "Leaves", "other": "Baking"},
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
    db.session.add(Category(display_order=_next_display_order(data["section"]), **data))
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
        if data["section"] != cat.section:
            # Moving section: it joins the end of its new section.
            cat.display_order = _next_display_order(data["section"])
            cat.section = data["section"]
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


@manage_bp.route("/categories/reorder", methods=["POST"])
def categories_reorder():
    """Save one section's order from the tree's reorder mode (0.30.0).
    Body: {"section": "carb", "ids": [3, 9, 7, 8]}. The ids must be exactly
    that section's categories, so a stale page can't drop or steal one; they
    are renumbered 1..n."""
    body = request.get_json(silent=True) or {}
    section = body.get("section")
    ids = body.get("ids")
    if section not in SECTION_KEYS or not isinstance(ids, list):
        return jsonify(ok=False, error="Bad request."), 400
    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Bad request."), 400
    cats = {c.id: c for c in Category.query.filter_by(section=section).all()}
    if sorted(ids) != sorted(cats):
        return jsonify(ok=False, error="This section changed elsewhere. Reload and try again."), 409
    for pos, cid in enumerate(ids, start=1):
        cats[cid].display_order = pos
    db.session.commit()
    return jsonify(ok=True)


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
    tags = DietaryTag.query.order_by(db.func.lower(DietaryTag.name)).all()
    # how many users each tag is assigned to — drives the delete confirmation
    counts = {t.id: len(t.users) for t in tags}
    # Group in TAG_TYPE_CHOICES order — the constant IS the display order, so the
    # template never names a type. An unrecognised value falls into "preference",
    # mirroring combined_dietary()'s fallback so the page and the brief agree
    # about where a stray type lands rather than silently hiding the tag.
    by_type = {key: [] for key, _ in TAG_TYPE_CHOICES}
    for t in tags:
        by_type.get(t.type, by_type["preference"]).append(t)
    groups = [(key, label, by_type[key]) for key, label in TAG_TYPE_CHOICES]
    # Active users only, for the assign-on-create checkboxes. Retired users are
    # excluded deliberately: they can't be cooked for, and users/routes.py
    # refuses to change a retired user's tags — offering them here would create
    # state that the Household page then won't let you edit.
    active_users = User.query.filter_by(is_active=True).order_by(
        db.func.lower(User.name)
    ).all()
    return render_template(
        "manage/dietary_tags.html",
        groups=groups, counts=counts,
        types=TAG_TYPE_CHOICES, hints=TAG_TYPE_HINTS,
        users=active_users,
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

    # Assign-on-create. A tag assigned to nobody reaches no brief at all, which
    # is the trap this closes: creating and assigning were two screens apart and
    # people stopped after the first. Parsed here rather than in _parse_tag_form
    # because the EDIT form deliberately has no assignment controls — that stays
    # on the Household page, where you edit one person's whole set at once.
    #
    # Ids are re-filtered against active users server-side: the checkbox list is
    # only a UI, and a stale page could post an id that's since been retired.
    requested_ids = {int(x) for x in request.form.getlist("user_ids") if x.isdigit()}
    assignees = (
        User.query.filter(User.id.in_(requested_ids), User.is_active.is_(True)).all()
        if requested_ids else []
    )

    tag = DietaryTag(**data)
    tag.users = assignees  # backref of User.dietary_tags — writes the join rows
    db.session.add(tag)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'"{data["name"]}" already exists.', "error")
        return redirect(url_for("manage.dietary_tags"))

    if assignees:
        names = ", ".join(sorted(u.name for u in assignees))
        flash(f'Added "{data["name"]}" and assigned it to {names}.', "success")
    else:
        flash(f'Added "{data["name"]}" — assign it to someone on the Household '
              'page, or it won\'t reach any recipe.', "success")
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
        tag=tag, types=TAG_TYPE_CHOICES, hints=TAG_TYPE_HINTS,
        user_count=len(tag.users),
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
