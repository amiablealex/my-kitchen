from urllib.parse import urlparse

from flask import Blueprint, render_template, request, jsonify, abort

from ..extensions import db
from ..models import Ingredient
from .service import in_stock_groups, search_addable

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


def _safe_return(target):
    """Accept a return-to target only if it's an internal path (open-redirect
    guard, same spirit as the auth `next` check): no scheme, no host, must start
    with a single '/'. Lets the wizard round-trip through /stock and back without
    /stock being able to bounce anyone off-site."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/") or target.startswith("//"):
        return None
    return target


@stock_bp.route("/")
def index():
    """Standalone pantry view: in-stock items only, grouped by category.
    The editing UI/logic lives in the shared stock/_editor.html partial.

    `return_to` (validated) lets a caller — currently the cook wizard's
    ingredient step — round-trip here for stock maintenance and get a link back."""
    return render_template(
        "stock/index.html",
        groups=in_stock_groups(),
        return_to=_safe_return(request.args.get("return_to")),
    )


@stock_bp.route("/search")
def search():
    q = request.args.get("q", "")
    results = search_addable(q)
    return render_template(
        "stock/_search_results.html", results=results, query=q.strip()
    )


@stock_bp.route("/<int:ingredient_id>/add", methods=["POST"])
def add(ingredient_id):
    ing = db.session.get(Ingredient, ingredient_id)
    if ing is None:
        abort(404)
    ing.in_stock = True
    db.session.commit()
    return jsonify(id=ing.id, in_stock=ing.in_stock)


@stock_bp.route("/<int:ingredient_id>/remove", methods=["POST"])
def remove(ingredient_id):
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
