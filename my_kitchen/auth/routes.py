from urllib.parse import urlparse, urljoin

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
)
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db, login_manager
from ..models import User

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    # Loaded fresh from the DB each request, so an is_active flip takes effect
    # immediately (see the gate below).
    return db.session.get(User, int(user_id))


def _safe_next(target):
    """Open-redirect guard: only allow a same-host relative target."""
    if not target:
        return None
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    if test.scheme in ("http", "https") and ref.netloc == test.netloc:
        return target
    return None


@auth_bp.before_app_request
def require_login():
    """App-wide gate: every request needs a logged-in user, except the login
    view, the health check, and static assets. This is why individual views
    don't need @login_required."""
    if request.endpoint is None or request.endpoint == "static":
        return  # unmatched routes (404s, favicon) flow to the normal handler
    if request.endpoint in {"auth.login", "main.healthz"}:
        return
    if not current_user.is_authenticated:
        nxt = request.full_path.rstrip("?") if request.method == "GET" else None
        return redirect(url_for("auth.login", next=nxt))
    if not current_user.is_active:
        # Retired mid-session: drop them out with a clear message.
        logout_user()
        flash("Your account has been deactivated.", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    next_raw = request.values.get("next")  # args on GET, form field on POST

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter(db.func.lower(User.name) == name.lower()).first()
        if user is None or not user.check_password(password):
            flash("Wrong name or password.", "error")
            return redirect(url_for("auth.login", next=next_raw))
        if not user.is_active:
            flash("That account has been deactivated.", "error")
            return redirect(url_for("auth.login"))
        login_user(user)
        flash(f"Welcome back, {user.name}.", "success")
        return redirect(_safe_next(next_raw) or url_for("main.index"))

    return render_template("auth/login.html", next=next_raw or "")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
