from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    current_app, abort, flash,
)
from flask_login import current_user

from ..extensions import db
from ..models import Ingredient, Generation, Recipe, User, SECTION_CHOICES
from ..llm.service import run_generation, combined_dietary
from ..stock.service import in_stock_groups

wizard_bp = Blueprint("wizard", __name__, url_prefix="/cook")

CUISINES = ["Italian", "Mediterranean", "British", "Asian", "Surprise me"]
TIME_BANDS = [("quick", "Quick (under 30 min)"), ("relaxed", "Relaxed (30–75 min)")]
SECTIONS = SECTION_CHOICES


def fresh_wizard():
    return {
        "selected_ingredient_ids": [],
        "cuisine": "Surprise me",
        "time_band": "quick",
        "cooking_for_user_ids": [],
        "guest_count": 0,
    }


def derived_servings(w):
    """Servings = selected household members + guests. Tolerant of old-shape
    sessions (pre-CP2) that lack the cooking-for keys: they read as 0."""
    return len(w.get("cooking_for_user_ids") or []) + int(w.get("guest_count") or 0)


def get_wizard():
    w = session.get("wizard")
    if not w:
        w = fresh_wizard()
        session["wizard"] = w
    return w


def save_wizard(w):
    session["wizard"] = w
    session.modified = True


@wizard_bp.route("/")
def start():
    session["wizard"] = fresh_wizard()
    session.modified = True
    return redirect(url_for("wizard.step_stock"))


@wizard_bp.route("/stock")
def step_stock():
    # Ensure the wizard session dict exists (tolerant of old-shape sessions).
    get_wizard()
    # Same shared pantry view as /stock: in-stock, active, non-staple items only,
    # with remove + search-to-add. The wizard just wraps it in step chrome below.
    return render_template("wizard/step_stock.html", groups=in_stock_groups())


@wizard_bp.route("/ingredients", methods=["GET", "POST"])
def step_ingredients():
    w = get_wizard()
    if request.method == "POST":
        ids = request.form.getlist("ingredient_ids")
        w["selected_ingredient_ids"] = [int(x) for x in ids if x.isdigit()]
        save_wizard(w)
        return redirect(url_for("wizard.step_cuisine"))

    in_stock = Ingredient.query.filter_by(in_stock=True, is_staple=False, is_active=True).all()
    lanes = []
    for section_key, section_label in SECTIONS:
        items = sorted([i for i in in_stock if i.category.section == section_key], key=lambda i: i.name.lower())
        lanes.append((section_label, items))
    return render_template("wizard/step_ingredients.html", lanes=lanes, selected=set(w["selected_ingredient_ids"]))


@wizard_bp.route("/cuisine", methods=["GET", "POST"])
def step_cuisine():
    w = get_wizard()
    if request.method == "POST":
        choice = request.form.get("cuisine", "Surprise me")
        w["cuisine"] = choice if choice in CUISINES else "Surprise me"
        save_wizard(w)
        return redirect(url_for("wizard.step_time"))
    return render_template("wizard/step_cuisine.html", cuisines=CUISINES, current=w["cuisine"])


@wizard_bp.route("/time", methods=["GET", "POST"])
def step_time():
    w = get_wizard()
    if request.method == "POST":
        choice = request.form.get("time_band", "quick")
        w["time_band"] = choice if choice in dict(TIME_BANDS) else "quick"
        save_wizard(w)
        return redirect(url_for("wizard.step_cooking_for"))
    return render_template("wizard/step_time.html", time_bands=TIME_BANDS, current=w["time_band"])


@wizard_bp.route("/cooking-for", methods=["GET", "POST"])
def step_cooking_for():
    w = get_wizard()
    if request.method == "POST":
        raw_ids = [int(x) for x in request.form.getlist("cooking_for_user_ids") if x.isdigit()]
        # Only currently-active users are valid covers; silently drop any id that
        # isn't active (e.g. retired between page-load and submit).
        active_ids = {u.id for u in User.query.filter_by(is_active=True).all()}
        user_ids = [i for i in raw_ids if i in active_ids]
        try:
            guests = int(request.form.get("guest_count", 0))
        except (TypeError, ValueError):
            guests = 0
        guests = max(0, guests)
        total = len(user_ids) + guests
        if total < 1:
            flash("Choose at least one person, or add a guest or two.", "error")
            return redirect(url_for("wizard.step_cooking_for"))
        if total > 20:  # match the old servings ceiling; trim guests, keep people
            guests = max(0, 20 - len(user_ids))
        w["cooking_for_user_ids"] = user_ids
        w["guest_count"] = guests
        save_wizard(w)
        return redirect(url_for("wizard.review"))

    active_users = User.query.filter_by(is_active=True).order_by(db.func.lower(User.name)).all()
    return render_template(
        "wizard/step_cooking_for.html",
        users=active_users,
        selected=set(w.get("cooking_for_user_ids") or []),
        guest_count=w.get("guest_count") or 0,
    )


@wizard_bp.route("/review")
def review():
    w = get_wizard()
    ids = w["selected_ingredient_ids"] or [0]
    selected = Ingredient.query.filter(Ingredient.id.in_(ids)).all()
    time_label = dict(TIME_BANDS).get(w["time_band"], w["time_band"])
    cooking_for_ids = w.get("cooking_for_user_ids") or []
    cooking_for_users = (
        User.query.filter(User.id.in_(cooking_for_ids)).order_by(db.func.lower(User.name)).all()
        if cooking_for_ids else []
    )
    guests = int(w.get("guest_count") or 0)
    allergies, preferences = combined_dietary(cooking_for_ids)
    return render_template(
        "wizard/review.html",
        selected=selected, cuisine=w["cuisine"], time_label=time_label,
        servings=len(cooking_for_ids) + guests,
        cooking_for_users=cooking_for_users, guest_count=guests,
        allergies=allergies, preferences=preferences,
    )


@wizard_bp.route("/generate", methods=["POST"])
def generate():
    w = get_wizard()
    if derived_servings(w) < 1:
        # Old-shape session, or someone reached /generate without the cooking-for
        # step. Send them to pick who's eating rather than generate for nobody.
        flash("Let me know who's eating before I cook.", "error")
        return redirect(url_for("wizard.step_cooking_for"))
    time_label = dict(TIME_BANDS).get(w["time_band"], w["time_band"])
    # The login gate guarantees an authenticated user here.
    gen, error = run_generation(current_app.config, w, time_label, user_id=current_user.id)
    if error:
        return render_template("wizard/error.html", error=error)
    return redirect(url_for("wizard.choice", generation_id=gen.id))


@wizard_bp.route("/choice/<int:generation_id>")
def choice(generation_id):
    gen = db.session.get(Generation, generation_id)
    if gen is None or len(gen.recipes) < 2:
        abort(404)
    return render_template("wizard/choice.html", recipes=gen.recipes)


@wizard_bp.route("/choose/<int:recipe_id>", methods=["POST"])
def choose(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    for sib in recipe.generation.recipes:
        sib.was_chosen = (sib.id == recipe.id)
    db.session.commit()
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id))


@wizard_bp.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    favourited = recipe in current_user.favourite_recipes
    return render_template("wizard/recipe.html", recipe=recipe, favourited=favourited)


@wizard_bp.route("/recipe/<int:recipe_id>/favourite", methods=["POST"])
def toggle_favourite(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    # Per-user: toggle this recipe in/out of the current user's favourites only.
    if recipe in current_user.favourite_recipes:
        current_user.favourite_recipes.remove(recipe)
        msg = "Removed from favourites."
    else:
        current_user.favourite_recipes.append(recipe)
        msg = "Added to favourites."
    db.session.commit()
    flash(msg, "success")
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
