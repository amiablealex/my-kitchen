from urllib.parse import urlparse

from flask import (Blueprint, abort, current_app, flash, jsonify, render_template,
                   request)
from flask_login import current_user

from ..extensions import db
from ..models import Category, Ingredient
from ..llm import receipt as receipt_reader
from ..llm.providers import provider_is_cloud, provider_reads_images
from ..usage.service import read_blocked_reason
from .service import (
    classify, in_stock_groups, parse_list, search_catalogue, set_stock, sheet_catalogue,
)

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
        sheet_catalogue=sheet_catalogue(),
        receipt_enabled=receipt_enabled(),
        cloud_ai=provider_is_cloud(current_app.config),
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
    # The confirmation sheet's "Add as new" (Phase 32) creates WITHOUT stocking:
    # stocking happens when the sheet is confirmed, so Cancel stocks nothing.
    stock_it = (request.form.get("stock") or "1") != "0"
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
        # The id lets the confirmation sheet simply use the existing item.
        return jsonify(ok=False, message=f'"{existing.name}" is already in your catalogue.',
                       id=existing.id, name=existing.name, is_staple=existing.is_staple,
                       in_stock=bool(existing.in_stock), section=existing.category.section), 409
    ing = Ingredient(
        name=name, category_id=category_id, is_staple=is_staple,
        in_stock=stock_it and not is_staple,
    )
    db.session.add(ing)
    db.session.commit()
    if is_staple and stock_it:
        flash(
            f'Added "{ing.name}" as a staple — assumed always available, '
            "so it won't appear in your stock list.",
            "info",
        )
    return jsonify(ok=True, id=ing.id, name=ing.name, is_staple=ing.is_staple,
                   in_stock=bool(ing.in_stock), section=ing.category.section)


def receipt_enabled():
    """The receipt button shows only when the household allows it AND the
    provider's models read images — hidden, never a "may not work" note."""
    cfg = current_app.config
    return bool(cfg.get("RECEIPT_SCANNING")) and provider_reads_images(cfg)


@stock_bp.route("/parse", methods=["POST"])
def parse():
    """A typed or pasted list -> the confirmation sheet's contents (Phase 32).
    Lines the resolver can't place get one AI matching call (Phase 33) when
    today's limits allow; only those lines are sent, as text."""
    def ai_match(lines):
        if read_blocked_reason(current_user.id):
            return None
        res = receipt_reader.read(current_app.config, current_user.id, lines=lines)
        return res["lines"] if res["ok"] else None
    return jsonify(parse_list(request.form.get("text", ""), ai_match=ai_match))


def _image_mime(data):
    """The photo's type from its first bytes — never trust the filename."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@stock_bp.route("/receipt", methods=["POST"])
def receipt():
    """Read the framed part of a receipt photo (Phase 33). The browser has
    already cropped it to the item lines and shrunk it; it's held in memory
    for the one call and never written anywhere."""
    if not receipt_enabled():
        abort(404)
    blocked = read_blocked_reason(current_user.id)
    if blocked:
        return jsonify(ok=False, message=blocked)
    upload = request.files.get("image")
    data = upload.read() if upload else b""
    mime = _image_mime(data)
    if not mime:
        return jsonify(ok=False, message="That doesn't look like a photo. Try another one?"), 400
    res = receipt_reader.read(current_app.config, current_user.id, image=(data, mime))
    del data, upload
    if not res["ok"]:
        current_app.logger.warning("receipt read failed: %s", res["error"])
        return jsonify(ok=False, message="The receipt couldn't be read just now. Try again, "
                                         "or paste the receipt text into search instead.")
    if not res["lines"]:
        return jsonify(ok=False, message="No food items found in that. Is the frame over "
                                         "the item lines?")
    return jsonify(ok=True, **classify(res["lines"]))


@stock_bp.route("/bulk", methods=["POST"])
def bulk():
    """Mark several ingredients in or out of stock at once — the sheet's
    confirm, and its Undo. JSON {ids: [...], in_stock: bool}. Staples and
    retired ingredients are ignored. Returns the ids that changed."""
    data = request.get_json(silent=True) or {}
    try:
        ids = [int(i) for i in data.get("ids") or []]
    except (TypeError, ValueError):
        return jsonify(ok=False, message="Bad ingredient list."), 400
    changed = set_stock(ids, bool(data.get("in_stock")))
    return jsonify(ok=True, changed=changed)
