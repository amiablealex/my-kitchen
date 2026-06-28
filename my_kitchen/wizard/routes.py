import re
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    current_app, abort, flash, jsonify,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Ingredient, Category, Generation, Recipe, RecipeIngredient, User,
    SECTION_CHOICES, DEFAULT_MEAL_TYPE, MEAL_TYPES, MEAL_TYPE_NAMES,
    meal_type_takes_cuisine,
)
from ..llm.service import start_generation, combined_dietary
# Reuse the manage blueprint's ingredient-creation validation rather than
# duplicating the name/category/staple handling (Phase 4a add-and-link). One-way
# import — manage.routes doesn't import wizard, so there's no cycle.
from ..manage.routes import _parse_ingredient_form, _name_taken

wizard_bp = Blueprint("wizard", __name__, url_prefix="/cook")

CUISINES = ["Italian", "Mediterranean", "British", "Asian", "Surprise me"]
TIME_BANDS = [("quick", "Quick (under 30 min)"), ("relaxed", "Relaxed (30–75 min)")]
SECTIONS = SECTION_CHOICES

# A running generation older than this is treated as dead (no reaper process —
# the check lives in the poll + the idempotency guard). Phase 12.
STALE_AFTER_SECONDS = 5 * 60


def fresh_wizard():
    return {
        "selected_ingredient_ids": [],
        "meal_type": DEFAULT_MEAL_TYPE,
        "cuisine": "Surprise me",
        "time_band": "quick",
        "cooking_for_user_ids": [],
        "guest_count": 0,
    }


def derived_servings(w):
    return len(w.get("cooking_for_user_ids") or []) + int(w.get("guest_count") or 0)


def _generation_age_seconds(gen):
    """Seconds since the row was created. created_at is written by models.utcnow
    (timezone-AWARE UTC), but SQLite hands DateTime columns back NAIVE (UTC
    wall-clock) on re-query — and the thread + poll both re-query. So compare
    against whichever clock matches the value we actually got, never assume one."""
    created = gen.created_at
    if created is None:
        return 0.0
    if created.tzinfo is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC
    else:
        now = datetime.now(timezone.utc)                       # aware UTC
    return (now - created).total_seconds()


def _is_stale(gen):
    """A still-"running" row older than the cap is treated as dead."""
    return _generation_age_seconds(gen) > STALE_AFTER_SECONDS


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
    return redirect(url_for("wizard.step_ingredients"))


@wizard_bp.route("/ingredients", methods=["GET", "POST"])
def step_ingredients():
    w = get_wizard()
    if request.method == "POST":
        ids = request.form.getlist("ingredient_ids")
        w["selected_ingredient_ids"] = [int(x) for x in ids if x.isdigit()]
        save_wizard(w)
        return redirect(url_for("wizard.step_cuisine"))

    # Live read of current stock on every render, so a round-trip to /stock
    # (via the "Stock not right?" link) is reflected the moment they return.
    in_stock = Ingredient.query.filter_by(in_stock=True, is_staple=False, is_active=True).all()
    lanes = []
    for section_key, section_label in SECTIONS:
        items = sorted([i for i in in_stock if i.category.section == section_key], key=lambda i: i.name.lower())
        lanes.append((section_label, items))
    return render_template(
        "wizard/step_ingredients.html",
        lanes=lanes, selected=set(w["selected_ingredient_ids"]),
        any_in_stock=bool(in_stock),
    )


@wizard_bp.route("/cuisine", methods=["GET", "POST"])
def step_cuisine():
    w = get_wizard()
    if request.method == "POST":
        meal_type = request.form.get("meal_type", DEFAULT_MEAL_TYPE)
        if meal_type not in MEAL_TYPE_NAMES:
            meal_type = DEFAULT_MEAL_TYPE
        w["meal_type"] = meal_type
        # Server is authoritative on cuisine. A non-cuisine meal type forces
        # cuisine to None (stored NULL) no matter what the cosmetically-hidden
        # cuisine radios submitted; a cuisine-bearing type takes the choice.
        if meal_type_takes_cuisine(meal_type):
            choice = request.form.get("cuisine", "Surprise me")
            w["cuisine"] = choice if choice in CUISINES else "Surprise me"
        else:
            w["cuisine"] = None
        save_wizard(w)
        return redirect(url_for("wizard.step_time"))
    return render_template(
        "wizard/step_cuisine.html",
        meal_types=MEAL_TYPES,
        current_meal_type=w.get("meal_type", DEFAULT_MEAL_TYPE),
        cuisines=CUISINES,
        current_cuisine=w.get("cuisine") or "Surprise me",
    )


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
        if total > 20:
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
        selected=selected, meal_type=w.get("meal_type", DEFAULT_MEAL_TYPE),
        cuisine=w["cuisine"], time_label=time_label,
        servings=len(cooking_for_ids) + guests,
        cooking_for_users=cooking_for_users, guest_count=guests,
        allergies=allergies, preferences=preferences,
    )


@wizard_bp.route("/generate", methods=["POST"])
def generate():
    w = get_wizard()
    # Synchronous pre-flight guard — runs BEFORE any row is created.
    if derived_servings(w) < 1:
        flash("Let me know who's eating before I cook.", "error")
        return redirect(url_for("wizard.step_cooking_for"))

    # Session idempotency. A double-submit (despite the disabled button) resumes
    # the SAME wait rather than starting a second generation. Only a still-running,
    # non-stale generation from this session is resumed; a finished, failed, or
    # stale one falls through to a fresh start.
    existing_id = session.get("active_generation_id")
    if existing_id is not None:
        existing = db.session.get(Generation, existing_id)
        if (existing is not None
                and (existing.status or "done") == "running"
                and not _is_stale(existing)):
            return redirect(url_for("wizard.generating", generation_id=existing.id))

    time_label = dict(TIME_BANDS).get(w["time_band"], w["time_band"])
    # Capture the real app object for the thread's app-context push — never let
    # the background thread reach for current_app / the request session.
    app = current_app._get_current_object()
    generation_id = start_generation(app, w, time_label, user_id=current_user.id)
    session["active_generation_id"] = generation_id
    session.modified = True
    return redirect(url_for("wizard.generating", generation_id=generation_id))


@wizard_bp.route("/generating/<int:generation_id>")
def generating(generation_id):
    gen = db.session.get(Generation, generation_id)
    if gen is None:
        abort(404)
    # NULL status = legacy/complete; if already finished, skip the wait entirely.
    if (gen.status or "done") == "done":
        return redirect(url_for("wizard.choice", generation_id=gen.id))
    # status_url + choice_url are built server-side so the polling JS works under
    # the HA ingress sub-path (the JS must never hardcode "/cook/status/...").
    return render_template(
        "wizard/generating.html",
        generation_id=gen.id,
        status_url=url_for("wizard.status", generation_id=gen.id),
    )


@wizard_bp.route("/status/<int:generation_id>")
def status(generation_id):
    """JSON poll target. redirect_url is a server-built url_for value (ingress
    safe). NULL status counts as done. Includes the stale-job guard: a row stuck
    "running" past the cap is flipped to "error" here (no separate reaper)."""
    gen = db.session.get(Generation, generation_id)
    if gen is None:
        return jsonify(
            status="error",
            error="That generation has gone missing — please try again.",
            redirect_url=None,
        ), 404

    st = gen.status or "done"

    if st == "running":
        if _is_stale(gen):
            # Persist the flip so history stays clean and the idempotency guard
            # (CP2) sees it as not-running. A zombie thread that finishes later
            # is harmless: it last-writes "done" with two real recipes.
            gen.status = "error"
            gen.error = gen.error or (
                "That took longer than expected, so I stopped waiting. "
                "Please try again."
            )
            db.session.commit()
            return jsonify(status="error", error=gen.error, redirect_url=None)
        return jsonify(status="running", error=None, redirect_url=None)

    if st == "done":
        return jsonify(
            status="done",
            error=None,
            redirect_url=url_for("wizard.choice", generation_id=gen.id),
        )

    # error
    return jsonify(status="error", error=gen.error or "Generation failed.", redirect_url=None)


@wizard_bp.route("/choice/<int:generation_id>")
def choice(generation_id):
    gen = db.session.get(Generation, generation_id)
    if gen is None:
        abort(404)
    # A still-running, non-stale generation lands back on the wait page rather
    # than 404-ing. Legacy NULL-status rows fall through (treated as done).
    if (gen.status or "done") == "running" and not _is_stale(gen):
        return redirect(url_for("wizard.generating", generation_id=gen.id))
    if len(gen.recipes) < 2:
        abort(404)
    return render_template("wizard/choice.html", recipes=gen.recipes)


@wizard_bp.route("/choose/<int:recipe_id>", methods=["POST"])
def choose(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    # /choose only makes sense for an AI recipe (the two-up choice screen). A
    # user/imported recipe has no generation and no sibling — guard the deref.
    if recipe.generation is None:
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
    # If an allergy was among the brief's combined dietary tags, show a caveat.
    # Re-derived from current tags (no snapshot stored) — consistent with the
    # spec's "an LLM is not a safety guarantee" honesty.
    # Allergy caveat applies only to AI recipes — they carry the brief's
    # cooking-for users via their generation. User/imported recipes have
    # generation_id NULL, so no generation and no caveat. This is the first
    # place a recipe can lack a generation, so the deref is guarded here.
    if recipe.generation is not None:
        allergies, _ = combined_dietary(recipe.generation.cooking_for_user_ids or [])
    else:
        allergies = []
    # The inline link editor (Phase 4a) needs the live catalogue to search
    # (active incl. staples, excl. retired) and the categories for add-and-link.
    # Built only for structured recipes — legacy row-less ones aren't editable.
    link_catalogue, categories = [], []
    if recipe.ingredients:
        link_catalogue = [
            {"id": i.id, "name": i.name}
            for i in Ingredient.query.filter_by(is_active=True)
                                     .order_by(db.func.lower(Ingredient.name)).all()
        ]
        categories = Category.query.order_by(
            Category.display_order, Category.name
        ).all()
    return render_template(
        "wizard/recipe.html", recipe=recipe, favourited=favourited,
        allergy_caveat=bool(allergies),
        link_catalogue=link_catalogue, categories=categories,
    )


def _recipe_ingredient_or_404(recipe_id, ri_id):
    """Fetch a RecipeIngredient, enforcing that it belongs to the given recipe.
    Guards the recipe-scoped link endpoints — a ri_id from another recipe 404s
    rather than being silently editable via a mismatched URL."""
    ri = db.session.get(RecipeIngredient, ri_id)
    if ri is None or ri.recipe_id != recipe_id:
        abort(404)
    return ri


@wizard_bp.route("/recipe/<int:recipe_id>/ingredient/<int:ri_id>/link", methods=["POST"])
def recipe_ingredient_link(recipe_id, ri_id):
    """Re-link or unlink one ingredient line. Body: ingredient_id (an active
    catalogue id to link), or empty/absent to unlink (ingredient_id -> NULL).
    A manual link/unlink is authoritative — no re-resolution is triggered, and
    the change is shared across the household (no per-user scoping)."""
    ri = _recipe_ingredient_or_404(recipe_id, ri_id)
    raw = (request.form.get("ingredient_id") or "").strip()
    if raw == "":
        ri.ingredient_id = None
        db.session.commit()
        return jsonify(ri_id=ri.id, ingredient_id=None, name=None)
    try:
        ing_id = int(raw)
    except (TypeError, ValueError):
        return jsonify(error="invalid", message="That ingredient isn’t valid."), 400
    ing = db.session.get(Ingredient, ing_id)
    if ing is None or not ing.is_active:
        # Never link to a missing or retired ingredient — the picker only offers
        # active ones, so this is a stale-page / tampered-request guard.
        return jsonify(error="invalid", message="That ingredient isn’t available."), 400
    ri.ingredient_id = ing.id
    db.session.commit()
    return jsonify(ri_id=ri.id, ingredient_id=ing.id, name=ing.name)


@wizard_bp.route("/recipe/<int:recipe_id>/ingredient/<int:ri_id>/add-and-link", methods=["POST"])
def recipe_ingredient_add_and_link(recipe_id, ri_id):
    """Create a NEW catalogue ingredient and link this line to it, in one action.
    Reuses manage's _parse_ingredient_form + _name_taken so the validation and
    category/staple handling can't drift. Faithful to manage on a name clash:
    if the name already exists we refuse and point the user at the picker (the
    existing ingredient is searchable there) rather than silently linking it.
    New ingredients default in_stock=False / is_active=True, matching seed +
    manage.ingredient_add."""
    ri = _recipe_ingredient_or_404(recipe_id, ri_id)
    data, error = _parse_ingredient_form()
    if error:
        return jsonify(error="validation", message=error), 400
    if _name_taken(data["name"]):
        return jsonify(
            error="exists",
            message=f'“{data["name"]}” is already in your catalogue — '
                    "search for it above to link it.",
        ), 400
    ing = Ingredient(
        name=data["name"], category_id=data["category_id"],
        is_staple=data["is_staple"], in_stock=False, is_active=True,
    )
    db.session.add(ing)
    try:
        db.session.flush()  # assign ing.id before linking
        ri.ingredient_id = ing.id
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            error="exists", message=f'“{data["name"]}” already exists.'
        ), 400
    return jsonify(ri_id=ri.id, ingredient_id=ing.id, name=ing.name)


# --------------------------------------------------------------------------
# Create / edit a recipe by hand (Phase 4b). No LLM, no resolver: the user
# picks each ingredient line from the catalogue (already linked). Saved as a
# normal Recipe with source="user", generation_id=NULL. The same template +
# JS power both create and edit.
# --------------------------------------------------------------------------

def _collect_indices(prefix, field):
    """Sorted unique row indices i for which f'{prefix}-{i}-{field}' was posted.
    Lets the dynamic add/remove rows submit under index-keyed names without
    needing a contiguous range — gaps from removed rows are fine, and ascending
    index == on-screen order (rows are only appended, never reordered)."""
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)-{re.escape(field)}$")
    idxs = set()
    for k in request.form.keys():
        m = pat.match(k)
        if m:
            idxs.add(int(m.group(1)))
    return sorted(idxs)


def _parse_steps(prefix, with_timer):
    """Parse prep/cook/tips rows into the existing *_steps_json shape. Rows with
    no text are dropped. Tips carry no timer (with_timer=False)."""
    steps = []
    for i in _collect_indices(prefix, "text"):
        title = (request.form.get(f"{prefix}-{i}-title") or "").strip()
        text = (request.form.get(f"{prefix}-{i}-text") or "").strip()
        if not text:
            continue
        step = {"title": title, "text": text}
        if with_timer:
            raw = (request.form.get(f"{prefix}-{i}-timer") or "").strip()
            timer = None
            if raw:
                try:
                    timer = int(raw)
                except ValueError:
                    timer = None
                if timer is not None and timer < 0:
                    timer = None
            step["timer_minutes"] = timer
        steps.append(step)
    return steps


def _parse_ingredient_lines():
    """Parse the picked ingredient rows. Each must link to an active catalogue
    ingredient (the form only lets you pick or add-and-pick). raw_text is the
    *catalogue* name (server-trusted, not the client-sent label). Returns
    (lines, error); fully-blank rows are skipped."""
    lines = []
    for i in _collect_indices("ing", "ingredient_id"):
        raw_id = (request.form.get(f"ing-{i}-ingredient_id") or "").strip()
        amount = (request.form.get(f"ing-{i}-amount") or "").strip()
        unit = (request.form.get(f"ing-{i}-unit") or "").strip()
        to_buy = request.form.get(f"ing-{i}-to_buy") == "on"
        name = (request.form.get(f"ing-{i}-name") or "").strip()
        if not raw_id and not amount and not unit and not name:
            continue  # blank row — ignore
        if not raw_id:
            return None, "Every ingredient line must be linked to a catalogue ingredient."
        try:
            ing_id = int(raw_id)
        except ValueError:
            return None, "An ingredient line had an invalid catalogue link."
        ing = db.session.get(Ingredient, ing_id)
        if ing is None or not ing.is_active:
            return None, "An ingredient line is linked to an unavailable ingredient."
        lines.append({
            "ingredient_id": ing.id,
            "raw_text": ing.name,
            "amount": amount or None,
            "unit": unit or None,
            "to_buy": to_buy,
        })
    return lines, None


def _save_recipe_from_form(recipe=None):
    """Create (recipe=None) or update a source='user' recipe in place. Writes the
    structured recipe_ingredients rows AND ingredients_json (display parity with
    AI recipes / keeps the 'still written' invariant). Returns (recipe, error)."""
    title = (request.form.get("title") or "").strip()
    blurb = (request.form.get("blurb") or "").strip()
    intro = (request.form.get("intro") or "").strip()
    meal_type = request.form.get("meal_type") or DEFAULT_MEAL_TYPE
    if meal_type not in MEAL_TYPE_NAMES:
        meal_type = DEFAULT_MEAL_TYPE
    try:
        servings = int(request.form.get("servings", ""))
    except (TypeError, ValueError):
        servings = 0

    prep = _parse_steps("prep", True)
    cook = _parse_steps("cook", True)
    tips = _parse_steps("tips", False)
    lines, line_err = _parse_ingredient_lines()

    if not title:
        return None, "Please give the recipe a title."
    if servings < 1:
        return None, "Servings must be at least 1."
    if line_err:
        return None, line_err
    if not lines:
        return None, "Add at least one ingredient."
    if not cook:
        return None, "Add at least one cooking step."

    ingredients_json = [
        {"item": ln["raw_text"], "amount": ln["amount"],
         "unit": ln["unit"], "to_buy": ln["to_buy"]}
        for ln in lines
    ]

    creating = recipe is None
    if creating:
        recipe = Recipe(source="user", generation_id=None,
                        created_by_user_id=current_user.id)
        db.session.add(recipe)

    recipe.title = title
    recipe.blurb = blurb or None
    recipe.intro = intro or None
    recipe.servings = servings
    recipe.meal_type = meal_type
    recipe.prep_steps_json = prep
    recipe.cook_steps_json = cook
    recipe.tips_json = tips or None
    recipe.ingredients_json = ingredients_json

    # Replace-all the structured rows; delete-orphan removes the previous set on
    # edit. position == list order (no reordering UI, so it mirrors on-screen).
    recipe.ingredients = [
        RecipeIngredient(
            ingredient_id=ln["ingredient_id"], raw_text=ln["raw_text"],
            amount=ln["amount"], unit=ln["unit"], to_buy=ln["to_buy"], position=pos,
        )
        for pos, ln in enumerate(lines)
    ]

    db.session.commit()
    return recipe, None


def _collect_prefill_from_form():
    """Lenient gather of everything typed, so a validation error re-renders the
    form with the user's input intact (no validation, blanks kept)."""
    def steps(prefix, with_timer):
        out = []
        for i in _collect_indices(prefix, "text"):
            out.append({
                "title": request.form.get(f"{prefix}-{i}-title") or "",
                "text": request.form.get(f"{prefix}-{i}-text") or "",
                "timer": (request.form.get(f"{prefix}-{i}-timer") or "") if with_timer else "",
            })
        return out
    ings = []
    for i in _collect_indices("ing", "ingredient_id"):
        ings.append({
            "ingredient_id": request.form.get(f"ing-{i}-ingredient_id") or "",
            "name": request.form.get(f"ing-{i}-name") or "",
            "amount": request.form.get(f"ing-{i}-amount") or "",
            "unit": request.form.get(f"ing-{i}-unit") or "",
            "to_buy": request.form.get(f"ing-{i}-to_buy") == "on",
        })
    return {
        "title": request.form.get("title") or "",
        "blurb": request.form.get("blurb") or "",
        "intro": request.form.get("intro") or "",
        "servings": request.form.get("servings") or "",
        "meal_type": request.form.get("meal_type") or DEFAULT_MEAL_TYPE,
        "prep": steps("prep", True),
        "cook": steps("cook", True),
        "tips": steps("tips", False),
        "ingredients": ings,
    }


def _recipe_to_prefill(recipe):
    """Existing recipe -> the same prefill shape the JS hydrates from (edit GET)."""
    def steps(items, with_timer):
        out = []
        for s in (items or []):
            row = {"title": s.get("title") or "", "text": s.get("text") or ""}
            if with_timer:
                t = s.get("timer_minutes")
                row["timer"] = str(t) if t else ""
            out.append(row)
        return out
    ings = []
    for ri in recipe.ingredients:  # ordered by position
        ings.append({
            "ingredient_id": str(ri.ingredient_id) if ri.ingredient_id else "",
            "name": ri.ingredient.name if ri.ingredient else ri.raw_text,
            "amount": ri.amount or "",
            "unit": ri.unit or "",
            "to_buy": bool(ri.to_buy),
        })
    return {
        "title": recipe.title or "",
        "blurb": recipe.blurb or "",
        "intro": recipe.intro or "",
        "servings": str(recipe.servings or ""),
        "meal_type": recipe.meal_type or DEFAULT_MEAL_TYPE,
        "prep": steps(recipe.prep_steps_json, True),
        "cook": steps(recipe.cook_steps_json, True),
        "tips": steps(recipe.tips_json, False),
        "ingredients": ings,
    }


def _form_context(mode, recipe=None, from_form=False):
    if from_form:
        prefill = _collect_prefill_from_form()
    elif recipe is not None:
        prefill = _recipe_to_prefill(recipe)
    else:
        prefill = {"title": "", "blurb": "", "intro": "", "servings": "2",
                   "meal_type": DEFAULT_MEAL_TYPE,
                   "prep": [], "cook": [], "tips": [], "ingredients": []}
    link_catalogue = [
        {"id": i.id, "name": i.name}
        for i in Ingredient.query.filter_by(is_active=True)
                                 .order_by(db.func.lower(Ingredient.name)).all()
    ]
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    action = (url_for("wizard.recipe_edit", recipe_id=recipe.id)
              if (mode == "edit" and recipe is not None)
              else url_for("wizard.recipe_new"))
    return {
        "mode": mode, "recipe": recipe, "form_action": action,
        "prefill": prefill, "link_catalogue": link_catalogue,
        "categories": categories, "meal_types": MEAL_TYPE_NAMES,
    }


@wizard_bp.route("/recipe/new", methods=["GET", "POST"])
def recipe_new():
    if request.method == "POST":
        recipe, error = _save_recipe_from_form(None)
        if error:
            flash(error, "error")
            return render_template("wizard/recipe_form.html",
                                   **_form_context("new", from_form=True))
        flash("Recipe created.", "success")
        return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
    return render_template("wizard/recipe_form.html", **_form_context("new"))


@wizard_bp.route("/recipe/<int:recipe_id>/edit", methods=["GET", "POST"])
def recipe_edit(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    # Only hand-created recipes are editable here. AI recipes' links are edited
    # inline on the recipe page (Phase 4a); their bodies aren't hand-editable.
    if recipe.source != "user":
        flash("Only recipes you've created can be edited here.", "error")
        return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
    if request.method == "POST":
        saved, error = _save_recipe_from_form(recipe)
        if error:
            flash(error, "error")
            return render_template("wizard/recipe_form.html",
                                   **_form_context("edit", recipe=recipe, from_form=True))
        flash("Recipe saved.", "success")
        return redirect(url_for("wizard.recipe", recipe_id=saved.id))
    return render_template("wizard/recipe_form.html",
                           **_form_context("edit", recipe=recipe))


@wizard_bp.route("/recipe/ingredient/add", methods=["POST"])
def recipe_ingredient_add():
    """Create a NEW catalogue ingredient for the create/edit picker and return its
    id (no row to link yet — distinct from recipe_ingredient_add_and_link, which
    links an existing line). Reuses manage's validation so it can't drift."""
    data, error = _parse_ingredient_form()
    if error:
        return jsonify(error="validation", message=error), 400
    if _name_taken(data["name"]):
        return jsonify(error="exists",
                       message=f'“{data["name"]}” is already in your catalogue — '
                               "search for it above."), 400
    ing = Ingredient(name=data["name"], category_id=data["category_id"],
                     is_staple=data["is_staple"], in_stock=False, is_active=True)
    db.session.add(ing)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="exists", message=f'“{data["name"]}” already exists.'), 400
    return jsonify(ingredient_id=ing.id, name=ing.name)


@wizard_bp.route("/recipe/<int:recipe_id>/favourite", methods=["POST"])
def toggle_favourite(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    if recipe in current_user.favourite_recipes:
        current_user.favourite_recipes.remove(recipe)
        msg = "Removed from favourites."
    else:
        current_user.favourite_recipes.append(recipe)
        msg = "Added to favourites."
    db.session.commit()
    flash(msg, "success")
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
