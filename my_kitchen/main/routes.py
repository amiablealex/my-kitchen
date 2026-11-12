from flask import Blueprint, render_template, jsonify, session
from flask_login import current_user

from ..models import Ingredient
from ..wizard.suggestions import cookable_now
from .hero import pick_line

main_bp = Blueprint("main", __name__)

# How many "you could make" cards the home page shows; the count line still
# says the full number.
HOME_COOKABLE_CARDS = 10


@main_bp.route("/")
def index():
    items = [
        i.name for i in Ingredient.query.filter_by(
            in_stock=True, is_active=True, is_staple=False)
    ]
    name = getattr(current_user, "name", None) if current_user.is_authenticated else None
    idx, hero_line = pick_line(name=name, items=items, avoid=session.get("hero_last"))
    session["hero_last"] = idx
    cookable = cookable_now()
    return render_template(
        "index.html",
        hero_line=hero_line,
        cookable=cookable[:HOME_COOKABLE_CARDS],
        cookable_count=len(cookable),
    )


@main_bp.route("/healthz")
def healthz():
    return jsonify(status="ok")
