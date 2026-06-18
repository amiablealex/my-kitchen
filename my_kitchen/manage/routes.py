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
from ..models import Category, Ingredient

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
    return render_template(
        "manage/ingredients.html",
        categories=cats, active=active, retired=retired,
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
