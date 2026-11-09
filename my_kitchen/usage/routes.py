from flask import Blueprint, render_template
from flask_login import current_user

from .service import dashboard

usage_bp = Blueprint("usage", __name__, url_prefix="/usage")


@usage_bp.route("/")
def index():
    """Household-wide model usage: calls, tokens, estimated cost, and today's
    headroom against the limits (Phase 25)."""
    return render_template("usage/index.html", **dashboard(current_user.id))
