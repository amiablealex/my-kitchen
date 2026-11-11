from urllib.parse import urlparse

from flask import Blueprint, render_template, request, jsonify, abort, flash

from ..extensions import db
from ..models import Category, Ingredient
from .service import in_stock_groups, search_catalogue

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


def _safe_return(target):
    """Accept a return-to target only if it's an internal path (open-redirect
    guard): no scheme, no host, must start with a single '/'."""
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
    return render_template(
        "stock/index.html",
        groups=in_stock_groups(),
        categories=Category.query.order_by(*Category.ordering()).all(),
        return_to=_safe_return(request.args.get("return_to")),
    )


@stock_bp.route("/search")
def search():
    q = request.args.get("q", "")
    results = search_catalogue(q)
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


@stock_bp.route("/create", methods=["POST"])
def create():
    """Create a brand-new catalogue ingredient and stock it in one step — the
    inline 'add as new' path when a catalogue search finds nothing. A staple is
    created but not stocked (staples are assumed, never in the pantry list)."""
    name = (request.form.get("name") or "").strip()
    category_id = request.form.get("category_id", type=int)
    is_staple = (request.form.get("is_staple") or "").lower() in ("on", "true", "1", "yes")
    if not name:
        return jsonify(ok=False, message="Give the ingredient a name."), 400
    if category_id is None or db.session.get(Category, category_id) is None:
        return jsonify(ok=False, message="Pick a category."), 400
    existing = (
        Ingredient.query
        .filter(db.func.lower(Ingredient.name) == name.lower())
        .first()
    )
    if existing is not None:
        return jsonify(ok=False, message=f'"{existing.name}" is already in your catalogue.'), 409
    ing = Ingredient(
        name=name, category_id=category_id, is_staple=is_staple, in_stock=not is_staple
    )
    db.session.add(ing)
    db.session.commit()
    if is_staple:
        flash(
            f'Added "{ing.name}" as a staple — assumed always available, '
            "so it won't appear in your stock list.",
            "info",
        )
    return jsonify(ok=True, id=ing.id, name=ing.name, is_staple=ing.is_staple)
