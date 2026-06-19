from flask import Blueprint, render_template, request, jsonify, abort

from ..extensions import db
from ..models import Ingredient
from .service import in_stock_groups

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


@stock_bp.route("/")
def index():
    """Standalone pantry view: in-stock items only, grouped by category.
    The editing UI/logic lives in the shared stock/_editor.html partial."""
    return render_template("stock/index.html", groups=in_stock_groups())


@stock_bp.route("/<int:ingredient_id>/remove", methods=["POST"])
def remove(ingredient_id):
    """Take an item out of stock (in_stock = False). Idempotent: removing an
    already-out item is a harmless no-op. Replaces the old flip-style toggle —
    on a pantry list 'remove' is never ambiguous about which way it goes."""
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    ing.in_stock = False
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
