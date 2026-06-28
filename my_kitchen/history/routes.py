from flask import Blueprint, render_template, request
from flask_login import current_user
from datetime import datetime

from ..extensions import db
from ..models import Generation, Recipe, User

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("/")
def index():
    """A merged, newest-first list of the recipe bank: AI generations (chosen /
    unchosen / error, as before) plus hand-created (source='user') recipes, which
    have no generation. The Cook filter works for both — generations carry the
    cook on created_by_user_id, and user recipes carry the author on the same
    column on the recipe row — so each source is filtered on its own table."""
    user_id = request.args.get("user", type=int)
    source = (request.args.get("source") or "").strip().lower()
    if source not in ("ai", "user"):
        source = ""  # any other value == no source filter

    # Source filter is read-side only: it just decides which tables contribute.
    # "ai" -> generations only; "user" -> user recipes only; "" -> both. Composes
    # with the Cook filter (AND), which each table still applies on its own column.
    generations = []
    if source != "user":
        gq = Generation.query
        if user_id:
            gq = gq.filter(Generation.created_by_user_id == user_id)
        generations = gq.all()

    user_recipes = []
    if source != "ai":
        rq = Recipe.query.filter(Recipe.source == "user")
        if user_id:
            rq = rq.filter(Recipe.created_by_user_id == user_id)
        user_recipes = rq.all()

    rows = []
    for gen in generations:
        if gen.recipes:
            chosen = next((r for r in gen.recipes if r.was_chosen), None)
            status = "chosen" if chosen else "unchosen"
        else:
            chosen = None
            status = "error"
        rows.append({"kind": "generation", "sort_at": gen.created_at,
                     "gen": gen, "status": status, "chosen": chosen,
                     "recipes": gen.recipes})
    for r in user_recipes:
        rows.append({"kind": "user", "sort_at": r.created_at, "recipe": r})

    rows.sort(key=lambda row: row["sort_at"] or datetime.min, reverse=True)

    users = User.query.order_by(db.func.lower(User.name)).all()
    fav_ids = {r.id for r in current_user.favourite_recipes}
    return render_template("history/index.html", rows=rows, users=users,
                           selected_user_id=user_id, selected_source=source,
                           fav_ids=fav_ids)


@history_bp.route("/favourites")
def favourites():
    """The logged-in user's favourites, newest-first (spec section 6, corrected
    to be per-user)."""
    recipes = (Recipe.query
               .filter(Recipe.favourited_by.any(id=current_user.id))
               .order_by(Recipe.created_at.desc()).all())
    return render_template("history/favourites.html", recipes=recipes)
