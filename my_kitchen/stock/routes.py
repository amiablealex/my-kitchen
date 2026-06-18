from flask import Blueprint, render_template, request, jsonify, abort

from ..extensions import db
from ..models import Category, Ingredient

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


@stock_bp.route("/")
def index():
    """Stock list grouped by category. Core items shown per the spec;
    staples gathered into a separate collapsible section."""
    categories = Category.query.order_by(Category.display_order).all()
    core_groups = []
    staple_groups = []
    for cat in categories:
        items = sorted([i for i in cat.ingredients if i.is_active], key=lambda i: i.name.lower())
        core = [i for i in items if not i.is_staple]
        staples = [i for i in items if i.is_staple]
        if core:
            core_groups.append((cat, core))
        if staples:
            staple_groups.append((cat, staples))
    return render_template(
        "stock/index.html",
        core_groups=core_groups,
        staple_groups=staple_groups,
    )


@stock_bp.route("/<int:ingredient_id>/toggle", methods=["POST"])
def toggle(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    ing.in_stock = not ing.in_stock
    db.session.commit()
    return jsonify(id=ing.id, in_stock=ing.in_stock)


@stock_bp.route("/<int:ingredient_id>/note", methods=["POST"])
def note(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    note_val = (request.form.get("note") or "").strip()
    ing.note = note_val or None
    db.session.commit()
    return jsonify(id=ing.id, note=ing.note or "")
