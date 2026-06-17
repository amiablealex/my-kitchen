from flask import Blueprint, render_template

from ..models import Generation

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("/")
def index():
    """Generations newest-first. Each is one of three states:
    chosen (a recipe was picked), unchosen (two recipes, none picked),
    or error/incomplete (no recipes — failed generation)."""
    generations = Generation.query.order_by(Generation.created_at.desc()).all()
    rows = []
    for gen in generations:
        if gen.recipes:
            chosen = next((r for r in gen.recipes if r.was_chosen), None)
            status = "chosen" if chosen else "unchosen"
        else:
            chosen = None
            status = "error"
        rows.append({"gen": gen, "status": status, "chosen": chosen, "recipes": gen.recipes})
    return render_template("history/index.html", rows=rows)
