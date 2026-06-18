"""My Kitchen — household user management (Phase 2, auth pass).

In-app CRUD for the people who can log in: list, add, edit (incl. rename),
retire/reactivate, and set passwords. There is no public/self-registration —
users are only ever created here or via the create-user CLI.

Users are retired (is_active=False), never hard-deleted: generations carry a
created_by_user_id FK, so deleting a user would sever history attribution.
Retiring blocks login (and force-logs-out a mid-session user, per the auth
gate) while keeping every history link intact and reactivatable.

Assigning dietary tags to users comes in the next pass.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User

users_bp = Blueprint("users", __name__, url_prefix="/users")


def _name_taken(name, exclude_id=None):
    """Case-insensitive duplicate check — matches the login route's
    case-insensitive name lookup, so 'home cook' and 'Home Cook' can't coexist."""
    q = User.query.filter(db.func.lower(User.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    return q.first() is not None


def _passwords_ok(password, confirm):
    """Validate a password/confirm pair. Returns (ok, error_message)."""
    if not password:
        return False, "Password cannot be empty."
    if password != confirm:
        return False, "Passwords don't match."
    return True, None


@users_bp.route("/")
def index():
    all_users = User.query.order_by(User.name).all()
    active = [u for u in all_users if u.is_active]
    retired = [u for u in all_users if not u.is_active]
    return render_template("users/index.html", active=active, retired=retired)


@users_bp.route("/add", methods=["POST"])
def add():
    name = (request.form.get("name") or "").strip()
    password = request.form.get("password") or ""
    confirm = request.form.get("password_confirm") or ""
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("users.index"))
    if _name_taken(name):
        flash(f'"{name}" already exists.', "error")
        return redirect(url_for("users.index"))

    user = User(name=name, is_active=True)
    # Password optional at creation: blank means "create now, set it later"
    # (same as the create-user CLI). If either field is filled, validate the pair.
    if password or confirm:
        ok, err = _passwords_ok(password, confirm)
        if not ok:
            flash(err, "error")
            return redirect(url_for("users.index"))
        user.set_password(password)

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'"{name}" already exists.', "error")
        return redirect(url_for("users.index"))

    if user.password_hash:
        flash(f'Added "{name}" — they can log in now.', "success")
    else:
        flash(f'Added "{name}". Set a password before they can log in.', "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
def edit(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("users.edit", user_id=user.id))
        if _name_taken(name, exclude_id=user.id):
            flash(f'"{name}" already exists.', "error")
            return redirect(url_for("users.edit", user_id=user.id))
        user.name = name
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(f'"{name}" already exists.', "error")
            return redirect(url_for("users.edit", user_id=user.id))
        flash(f'Saved "{user.name}".', "success")
        return redirect(url_for("users.index"))
    return render_template("users/edit.html", user=user)


@users_bp.route("/<int:user_id>/password", methods=["POST"])
def set_password(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    password = request.form.get("password") or ""
    confirm = request.form.get("password_confirm") or ""
    ok, err = _passwords_ok(password, confirm)
    if not ok:
        flash(err, "error")
        return redirect(url_for("users.edit", user_id=user.id))
    user.set_password(password)
    db.session.commit()
    flash(f'Password updated for "{user.name}".', "success")
    return redirect(url_for("users.edit", user_id=user.id))


@users_bp.route("/<int:user_id>/retire", methods=["POST"])
def retire(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You can't retire your own account while you're logged in. "
              "Ask the other household member to do it, or use the CLI.", "error")
        return redirect(url_for("users.index"))
    user.is_active = False
    db.session.commit()
    flash(f'Retired "{user.name}" — they can no longer log in, but their history '
          'is kept and they can be reactivated any time.', "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:user_id>/activate", methods=["POST"])
def activate(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    user.is_active = True
    db.session.commit()
    flash(f'Reactivated "{user.name}".', "success")
    return redirect(url_for("users.index"))
