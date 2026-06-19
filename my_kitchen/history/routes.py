from flask import Blueprint, render_template, request

from ..extensions import db
from ..models import Generation, Recipe, User

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("/")
def index():
    """Generations newest-first, optionally filtered to one cook
    (created_by_user_id via ?user=<id>). Each is one of three states:
    chosen (a recipe was picked), unchosen (two recipes, none picked),
    or error/incomplete (no recipes — failed generation)."""
    user_id = request.args.get("user", type=int)
    q = Generation.query
    if user_id:
        q = q.filter(Generation.created_by_user_id == user_id)
    generations = q.order_by(Generation.created_at.desc()).all()
    rows = []
    for gen in generations:
        if gen.recipes:
            chosen = next((r for r in gen.recipes if r.was_chosen), None)
            status = "chosen" if chosen else "unchosen"
        else:
            chosen = None
            status = "error"
        rows.append({"gen": gen, "status": status, "chosen": chosen, "recipes": gen.recipes})
    # All users (incl. retired — they still hold history) drive the filter dropdown.
    users = User.query.order_by(db.func.lower(User.name)).all()
    return render_template("history/index.html", rows=rows, users=users, selected_user_id=user_id)


@history_bp.route("/favourites")
def favourites():
    """Flagged recipes, newest-first — the quick-access subset (spec section 6)."""
    recipes = Recipe.query.filter_by(is_favourite=True).order_by(Recipe.created_at.desc()).all()
    return render_template("history/favourites.html", recipes=recipes)
