from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    current_app, abort,
)
from flask_login import current_user

from ..extensions import db
from ..models import Category, Ingredient, Generation, Recipe, SECTION_CHOICES
from ..llm.service import run_generation

wizard_bp = Blueprint("wizard", __name__, url_prefix="/cook")

CUISINES = ["Italian", "Mediterranean", "British", "Asian", "Surprise me"]
TIME_BANDS = [("quick", "Quick (under 30 min)"), ("relaxed", "Relaxed (30–75 min)")]
SECTIONS = SECTION_CHOICES


def fresh_wizard():
    return {"selected_ingredient_ids": [], "cuisine": "Surprise me", "time_band": "quick", "servings": 2}


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
    get_wizard()
    categories = Category.query.order_by(Category.display_order).all()
    core_groups = []
    for cat in categories:
        items = sorted([i for i in cat.ingredients if not i.is_staple and i.is_active], key=lambda i: i.name.lower())
        if items:
            core_groups.append((cat, items))
    return render_template("wizard/step_stock.html", core_groups=core_groups)


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
        return redirect(url_for("wizard.step_servings"))
    return render_template("wizard/step_time.html", time_bands=TIME_BANDS, current=w["time_band"])


@wizard_bp.route("/servings", methods=["GET", "POST"])
def step_servings():
    w = get_wizard()
    if request.method == "POST":
        try:
            servings = int(request.form.get("servings", 2))
        except (TypeError, ValueError):
            servings = 2
        w["servings"] = max(1, min(servings, 20))
        save_wizard(w)
        return redirect(url_for("wizard.review"))
    return render_template("wizard/step_servings.html", current=w["servings"])


@wizard_bp.route("/review")
def review():
    w = get_wizard()
    ids = w["selected_ingredient_ids"] or [0]
    selected = Ingredient.query.filter(Ingredient.id.in_(ids)).all()
    time_label = dict(TIME_BANDS).get(w["time_band"], w["time_band"])
    return render_template("wizard/review.html", selected=selected,
                           cuisine=w["cuisine"], time_label=time_label, servings=w["servings"])


@wizard_bp.route("/generate", methods=["POST"])
def generate():
    w = get_wizard()
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
    return render_template("wizard/recipe.html", recipe=recipe)
