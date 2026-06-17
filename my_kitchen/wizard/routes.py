from flask import (
    Blueprint, render_template, request, redirect, url_for, session
)

from ..models import Category, Ingredient

wizard_bp = Blueprint("wizard", __name__, url_prefix="/cook")

# MVP-hardcoded option lists (made configurable in a later phase).
CUISINES = ["Italian", "Mediterranean", "British", "Asian", "Surprise me"]
TIME_BANDS = [("quick", "Quick (under 30 min)"), ("relaxed", "Relaxed (30–75 min)")]
SECTIONS = [("protein", "Protein"), ("carb", "Carb"), ("veg", "Veg"), ("other", "Other")]


def fresh_wizard():
    return {
        "selected_ingredient_ids": [],
        "cuisine": "Surprise me",
        "time_band": "quick",
        "servings": 2,
    }


def get_wizard():
    """Return the current wizard state, initialising defaults if absent.
    Keeps direct access to a later step from crashing."""
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
    """Begin a fresh cook flow (clears any prior in-progress wizard)."""
    session["wizard"] = fresh_wizard()
    session.modified = True
    return redirect(url_for("wizard.step_stock"))


@wizard_bp.route("/stock")
def step_stock():
    """Step 1 — stock check. Reuses the stock toggle/note endpoints + stock.js."""
    get_wizard()
    categories = Category.query.order_by(Category.display_order).all()
    core_groups = []
    for cat in categories:
        items = sorted(
            [i for i in cat.ingredients if not i.is_staple],
            key=lambda i: i.name.lower(),
        )
        if items:
            core_groups.append((cat, items))
    return render_template("wizard/step_stock.html", core_groups=core_groups)


@wizard_bp.route("/ingredients", methods=["GET", "POST"])
def step_ingredients():
    """Step 2 — choose in-stock core ingredients, grouped into the four lanes."""
    w = get_wizard()
    if request.method == "POST":
        ids = request.form.getlist("ingredient_ids")
        w["selected_ingredient_ids"] = [int(x) for x in ids if x.isdigit()]
        save_wizard(w)
        return redirect(url_for("wizard.step_cuisine"))

    in_stock = Ingredient.query.filter_by(in_stock=True, is_staple=False).all()
    lanes = []
    for section_key, section_label in SECTIONS:
        items = sorted(
            [i for i in in_stock if i.category.section == section_key],
            key=lambda i: i.name.lower(),
        )
        lanes.append((section_label, items))
    selected = set(w["selected_ingredient_ids"])
    return render_template("wizard/step_ingredients.html", lanes=lanes, selected=selected)


@wizard_bp.route("/cuisine", methods=["GET", "POST"])
def step_cuisine():
    """Step 3 — cuisine."""
    w = get_wizard()
    if request.method == "POST":
        choice = request.form.get("cuisine", "Surprise me")
        w["cuisine"] = choice if choice in CUISINES else "Surprise me"
        save_wizard(w)
        return redirect(url_for("wizard.step_time"))
    return render_template("wizard/step_cuisine.html", cuisines=CUISINES, current=w["cuisine"])


@wizard_bp.route("/time", methods=["GET", "POST"])
def step_time():
    """Step 4 — time band."""
    w = get_wizard()
    if request.method == "POST":
        choice = request.form.get("time_band", "quick")
        w["time_band"] = choice if choice in dict(TIME_BANDS) else "quick"
        save_wizard(w)
        return redirect(url_for("wizard.step_servings"))
    return render_template("wizard/step_time.html", time_bands=TIME_BANDS, current=w["time_band"])


@wizard_bp.route("/servings", methods=["GET", "POST"])
def step_servings():
    """Step 5 — servings (the simple 'cooking for' proxy in the MVP)."""
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
    """Pre-generate summary — proves the collected brief round-tripped."""
    w = get_wizard()
    ids = w["selected_ingredient_ids"] or [0]
    selected = Ingredient.query.filter(Ingredient.id.in_(ids)).all()
    time_label = dict(TIME_BANDS).get(w["time_band"], w["time_band"])
    return render_template(
        "wizard/review.html",
        selected=selected,
        cuisine=w["cuisine"],
        time_label=time_label,
        servings=w["servings"],
    )


@wizard_bp.route("/generate", methods=["POST"])
def generate():
    """Stub for CP4. The LLM call, choice screen, and recipe display land in CP5."""
    return render_template("wizard/generate_stub.html")
