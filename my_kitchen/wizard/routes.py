import json
import random
import re
import threading
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    current_app, abort, flash, jsonify,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Ingredient, Category, Generation, Recipe, RecipeIngredient, RecipeComment,
    User, SECTION_CHOICES, DEFAULT_MEAL_TYPE, MEAL_TYPES, MEAL_TYPE_NAMES,
    meal_type_takes_cuisine, CUISINES, WIZARD_CUISINES, SURPRISE_ME,
    COMMENT_MAX_CHARS, TAG_TYPE_CHOICES, TAG_TYPE_HINTS, utcnow,
    SPECIAL_REQUEST_MAX_CHARS, KITCHEN_MENTION, QUESTION_MAX_CHARS,
)
from ..llm.importer import ImportProblem, import_recipe
from ..llm.qa import answer_question
from ..llm.service import (
    start_generation, combined_dietary, clean_special_request,
    start_regeneration, start_refine, regenerate_round, recipe_versions,
)
from ..usage.service import (
    generation_blocked_reason, import_blocked_reason, question_blocked_reason, limits_today,
)
from .suggestions import suggest_recipes
from ..stock.service import search_catalogue
# Reuse the manage blueprint's ingredient-creation validation rather than
# duplicating the name/category/staple handling (Phase 4a add-and-link). One-way
# import — manage.routes doesn't import wizard, so there's no cycle.
from ..manage.routes import _parse_ingredient_form, _name_taken

wizard_bp = Blueprint("wizard", __name__, url_prefix="/cook")

TIME_BANDS = [("quick", "Quick (under 30 min)"), ("relaxed", "Relaxed (30–75 min)")]
SECTIONS = SECTION_CHOICES

# Meal types that carry a cuisine (mirrors the wizard hierarchy). Gates the recipe
# cuisine tag in the create/edit form and the inline tag editor. (Phase 17)
CUISINE_MEAL_TYPES = [n for n in MEAL_TYPE_NAMES if meal_type_takes_cuisine(n)]

# A running generation older than this is treated as dead (no reaper process —
# the check lives in the poll + the idempotency guard). Phase 12.
STALE_AFTER_SECONDS = 5 * 60

# Special request (Phase 25): one placeholder is picked per render so the box
# teaches by example without a wall of help text; the chips add text on tap.
SPECIAL_REQUEST_PLACEHOLDERS = [
    "e.g. a proper curry, nothing too fiery",
    "e.g. I'm tired — keep it really simple",
    "e.g. something warming and comforting",
    "e.g. traditional, true to the cuisine",
    "e.g. fresh and light, nothing heavy",
    "e.g. a one-pot I can leave to bubble away",
]
# Two, so they sit on one row on a phone; the rotating placeholder carries the other examples.
SPECIAL_REQUEST_CHIPS = ["Something spicy", "Keep it simple"]


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
        # "Edit stock" is a submit button (0.29.2), so the picks made so far are
        # saved before the hop to /stock and re-ticked on the way back. An item
        # removed from stock meanwhile simply has no chip, so it drops out on
        # the next submit.
        if request.form.get("go") == "stock":
            return redirect(url_for("stock.index", return_to=url_for("wizard.step_ingredients")))
        return redirect(url_for("wizard.step_cuisine"))

    # Live read of current stock on every render, so a round-trip to /stock
    # (via the "Stock not right?" link) is reflected the moment they return.
    in_stock = Ingredient.query.filter_by(in_stock=True, is_staple=False, is_active=True).all()
    lanes = []
    for section_key, section_label in SECTIONS:
        items = sorted([i for i in in_stock if i.category.section == section_key], key=lambda i: i.name.lower())
        lanes.append((section_label, items))

    # Staples are selectable too (Phase 20). Selection means "build the meal
    # around this" — a statement about creative direction, not availability — so
    # excluding staples was conflating the two: "tomato, bread, oregano" is a
    # perfectly good brief. They live in their own drawer rather than in the
    # four lanes because (a) the four sections are a fixed guardrail and folding
    # ~40 spices/oils into "Other" would swamp it, and (b) the app already draws
    # this line everywhere else (stock excludes staples; Manage handles them
    # separately). Grouped by CATEGORY, not section — there's no lane semantics
    # to preserve here and category is the meaningful axis for staples.
    staple_rows = (
        Ingredient.query
        .filter_by(is_staple=True, is_active=True)
        .join(Category, Ingredient.category_id == Category.id)
        .order_by(*Category.ordering(), db.func.lower(Ingredient.name))
        .all()
    )
    staple_groups = []
    for ing in staple_rows:
        if not staple_groups or staple_groups[-1][0] != ing.category.name:
            staple_groups.append((ing.category.name, []))
        staple_groups[-1][1].append(ing)

    selected = set(w["selected_ingredient_ids"])
    return render_template(
        "wizard/step_ingredients.html",
        lanes=lanes, selected=selected,
        any_in_stock=bool(in_stock),
        staple_groups=staple_groups,
        # Surfaced on the closed drawer — a collapsed section must never hide an
        # active selection.
        staple_selected_count=sum(1 for i in staple_rows if i.id in selected),
    )


@wizard_bp.route("/ingredients/catalogue")
def ingredients_catalogue():
    """Fragment for the ingredients step's search: catalogue matches that are NOT
    in stock (active, non-staple), offered as add-to-stock chips. In-stock items
    and staples are already on the page and filtered client-side. (0.29.2)"""
    q = (request.args.get("q") or "").strip()
    results = [i for i in search_catalogue(q, limit=40)
               if not i.in_stock and not i.is_staple][:12]
    return render_template("wizard/_catalogue.html", results=results, query=q)


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
            w["cuisine"] = choice if choice in WIZARD_CUISINES else "Surprise me"
        else:
            w["cuisine"] = None
        save_wizard(w)
        return redirect(url_for("wizard.step_time"))
    return render_template(
        "wizard/step_cuisine.html",
        meal_types=MEAL_TYPES,
        current_meal_type=w.get("meal_type", DEFAULT_MEAL_TYPE),
        cuisines=WIZARD_CUISINES,
        current_cuisine=w.get("cuisine") or SURPRISE_ME,
        surprise_value=SURPRISE_ME,
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
        tag_types=TAG_TYPE_CHOICES,
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
    allergies, avoid, preferences = combined_dietary(cooking_for_ids)

    meal_type = w.get("meal_type", DEFAULT_MEAL_TYPE)
    cuisine = w["cuisine"]
    # The keystone payoff: deterministic, no-LLM query for saved recipes cookable
    # right now that fit the brief (see wizard/suggestions.py).
    suggestions = suggest_recipes(
        meal_type=meal_type,
        cuisine=cuisine,
        must_use_ids=w.get("selected_ingredient_ids") or [],
    )
    # Display label for the brief summary: the Surprise sentinel reads as "Any"
    # (value/behaviour unchanged); None (non-cuisine meal type) shows no line.
    cuisine_label = None if not cuisine else ("Any" if cuisine == SURPRISE_ME else cuisine)

    return render_template(
        "wizard/review.html",
        selected=selected, meal_type=meal_type,
        # Nothing picked is the LEAST constrained brief (the prompt says "design
        # freely from AVAILABLE + staples"), so the summary says so. (0.29.2)
        any_in_stock=Ingredient.query.filter_by(in_stock=True, is_staple=False, is_active=True).first() is not None,
        cuisine=cuisine, cuisine_label=cuisine_label, time_label=time_label,
        servings=len(cooking_for_ids) + guests,
        cooking_for_users=cooking_for_users, guest_count=guests,
        allergies=allergies, avoid=avoid, preferences=preferences,
        tag_hints=TAG_TYPE_HINTS,
        suggestions=suggestions,
        special_request=w.get("special_request") or "",
        special_request_max=SPECIAL_REQUEST_MAX_CHARS,
        special_request_placeholder=random.choice(SPECIAL_REQUEST_PLACEHOLDERS),
        special_request_chips=SPECIAL_REQUEST_CHIPS,
        limits=limits_today(current_user.id),
    )


def _start_guard(bounce_url):
    """Shared pre-flight for anything that starts a paid model job (generate,
    regenerate, refine). Returns a redirect, or None to go ahead.

    One running job per USER (Phase 25), not just per session: a second tab or
    device resumes the same wait instead of starting another paid call. Checked
    in the DB, so it holds across both gunicorn workers. Then the daily limits
    — a calm explanation and a bounce back, never an error page."""
    running = (Generation.query
               .filter(Generation.created_by_user_id == current_user.id,
                       Generation.status == "running")
               .order_by(Generation.created_at.desc()).first())
    if running is not None and not _is_stale(running):
        return redirect(url_for("wizard.generating", generation_id=running.id))
    blocked = generation_blocked_reason(current_user.id)
    if blocked:
        flash(blocked, "info")
        return redirect(bounce_url)
    return None


def _done_url(gen):
    """Where a finished job lands: a refine goes straight to its one recipe;
    everything else to the two-up choice screen."""
    if gen.kind == "refine" and gen.recipes:
        return url_for("wizard.recipe", recipe_id=gen.recipes[0].id, refined=1)
    return url_for("wizard.choice", generation_id=gen.id)


@wizard_bp.route("/generate", methods=["POST"])
def generate():
    w = get_wizard()
    # Keep the typed request in the wizard state first, so if a guard below
    # bounces the user back to review, their words are still in the box.
    w["special_request"] = clean_special_request(request.form.get("special_request"))
    save_wizard(w)
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

    guard = _start_guard(url_for("wizard.review"))
    if guard is not None:
        return guard

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
        return redirect(_done_url(gen))
    # status_url + choice_url are built server-side so the polling JS works under
    # the HA ingress sub-path (the JS must never hardcode "/cook/status/...").
    return render_template(
        "wizard/generating.html",
        generation_id=gen.id,
        status_url=url_for("wizard.status", generation_id=gen.id),
        mode=gen.kind or "generate",
        retry_url=(url_for("wizard.recipe", recipe_id=gen.source_recipe_id) if gen.kind == "refine"
                   else url_for("wizard.choice", generation_id=gen.parent_generation_id)
                   if gen.kind == "regenerate" else url_for("wizard.review")),
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
            redirect_url=_done_url(gen),
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
    if gen.kind == "refine" and gen.recipes:
        return redirect(_done_url(gen))
    if len(gen.recipes) < 2:
        abort(404)
    rounds_used = regenerate_round(gen)
    rounds_limit = int(current_app.config.get("LIMIT_REGENERATES_PER_BRIEF", 3))
    return render_template(
        "wizard/choice.html", gen=gen, recipes=gen.recipes,
        rounds_left=max(0, rounds_limit - rounds_used),
        special_request_max=SPECIAL_REQUEST_MAX_CHARS,
        limits=limits_today(current_user.id),
    )


@wizard_bp.route("/choice/<int:generation_id>/regenerate", methods=["POST"])
def regenerate(generation_id):
    """"Neither — try again" (Phase 26): a fresh pair from the same brief,
    told what was passed on. The request box is pre-filled with the original
    request and may be edited."""
    parent = db.session.get(Generation, generation_id)
    if parent is None or parent.kind == "refine" or not parent.recipes:
        abort(404)
    back = url_for("wizard.choice", generation_id=parent.id)
    limit = int(current_app.config.get("LIMIT_REGENERATES_PER_BRIEF", 3))
    if regenerate_round(parent) >= limit:
        flash(f"That's {limit} fresh tries from this brief. Try changing the brief "
              "instead — a different ingredient or cuisine opens up new ideas.", "info")
        return redirect(back)
    guard = _start_guard(back)
    if guard is not None:
        return guard
    time_label = dict(TIME_BANDS).get(parent.time_band, parent.time_band or "")
    app = current_app._get_current_object()
    gen_id = start_regeneration(
        app, parent, clean_special_request(request.form.get("special_request")),
        time_label, current_user.id)
    session["active_generation_id"] = gen_id
    session.modified = True
    return redirect(url_for("wizard.generating", generation_id=gen_id))


@wizard_bp.route("/recipe/<int:recipe_id>/refine", methods=["POST"])
def recipe_refine(recipe_id):
    """Refine (Phase 26): one revised version of an AI recipe, from a short
    change request. Only the latest version of a recipe can be refined, which
    keeps its history a straight line."""
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    back = url_for("wizard.recipe", recipe_id=recipe.id)
    if recipe.generation is None or recipe.is_archived:
        abort(400)
    if recipe_versions(recipe)[-1][0].id != recipe.id:
        flash("There's a newer version of this recipe — refine that one instead.", "info")
        return redirect(back)
    instruction = clean_special_request(request.form.get("instruction"))
    if not instruction:
        flash("Tell the kitchen what you'd like to change first.", "info")
        return redirect(back + "#refine")
    guard = _start_guard(back)
    if guard is not None:
        return guard
    time_label = dict(TIME_BANDS).get(recipe.time_band or recipe.generation.time_band, "")
    app = current_app._get_current_object()
    gen_id = start_refine(app, recipe, instruction, time_label, current_user.id)
    session["active_generation_id"] = gen_id
    session.modified = True
    return redirect(url_for("wizard.generating", generation_id=gen_id))


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
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id, fresh=1))


REFINE_CHIPS = ["Make it spicier", "Simpler method", "No extras — use what I've got", "Make it lighter"]


@wizard_bp.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    favourited = recipe in current_user.favourite_recipes
    # Refine lineage (Phase 26): oldest first; the strip only renders past one.
    versions = recipe_versions(recipe)
    is_latest = versions[-1][0].id == recipe.id
    # If an allergy was among the brief's combined dietary tags, show a caveat.
    # Re-derived from current tags (no snapshot stored) — consistent with the
    # spec's "an LLM is not a safety guarantee" honesty.
    # Allergy caveat applies only to AI recipes — they carry the brief's
    # cooking-for users via their generation. User/imported recipes have
    # generation_id NULL, so no generation and no caveat. This is the first
    # place a recipe can lack a generation, so the deref is guarded here.
    if recipe.generation is not None:
        allergies, _, _ = combined_dietary(recipe.generation.cooking_for_user_ids or [])
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
        categories = Category.query.order_by(*Category.ordering()).all()
    # "Used anything up?" (Phase 32): the recipe's linked ingredients that are
    # in stock right now — staples are assumed, so never offered. Deduped,
    # recipe order. Empty -> the line isn't shown.
    used_up_items, seen = [], set()
    for line in recipe.ingredients:
        ing = line.ingredient
        if (ing is None or ing.id in seen or ing.is_staple
                or not (ing.in_stock and ing.is_active)):
            continue
        seen.add(ing.id)
        used_up_items.append({"id": ing.id, "name": ing.name, "section": ing.category.section})
    return render_template(
        "wizard/recipe.html", recipe=recipe, favourited=favourited,
        used_up_items=used_up_items,
        allergy_caveat=bool(allergies),
        link_catalogue=link_catalogue, categories=categories,
        meal_type_names=MEAL_TYPE_NAMES,
        cuisines=CUISINES,
        cuisine_meal_types=CUISINE_MEAL_TYPES,
        cuisine_allowed=bool(recipe.meal_type and meal_type_takes_cuisine(recipe.meal_type)),
        comment_max_chars=COMMENT_MAX_CHARS,
        versions=versions, is_latest=is_latest,
        can_refine=(recipe.generation is not None and is_latest and not recipe.is_archived),
        refine_open=bool(request.args.get("fresh")),
        just_refined=bool(request.args.get("refined")),
        refine_chips=REFINE_CHIPS, refine_max=SPECIAL_REQUEST_MAX_CHARS,
        kitchen_mention=KITCHEN_MENTION,
        stale_answer_ids={c.id for c in recipe.comments
                          if c.is_question and c.answer_status == "pending" and _answer_is_stale(c)},
        questions_left=limits_today(current_user.id)["questions_left"],
    )


@wizard_bp.route("/recipe/<int:recipe_id>/comment", methods=["POST"])
def recipe_comment_add(recipe_id):
    """Post a household note on a recipe (Phase 19).

    Plain form POST -> redirect, not AJAX: unlike the tag/link editors this is a
    page-level submission, so POST-redirect-GET with a #notes anchor lands the
    user back where they posted, uses the standard hidden CSRF field, and needs
    no JS (and so no client-side path construction under HA ingress).
    """
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    body = (request.form.get("body") or "").strip()
    question = _strip_mention(body)
    if question is not None:
        return _ask_kitchen(recipe, question)
    if not body:
        flash("Write something first — an empty note isn't saved.", "error")
    elif len(body) > COMMENT_MAX_CHARS:
        flash(f"That note is too long (max {COMMENT_MAX_CHARS} characters).", "error")
    else:
        db.session.add(RecipeComment(
            recipe_id=recipe.id, user_id=current_user.id, body=body,
        ))
        db.session.commit()
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id, _anchor="notes"))


# --- @kitchen questions (Phase 27) ------------------------------------------
# A note that STARTS with "@kitchen" is a question for the AI. Only the start
# counts, so a note that merely mentions the word can't cost a call by
# accident. The answer is written onto the question's own row by a background
# job; the POST waits a short while for it so the usual case lands answered,
# and anything slower shows "thinking" and the page checks back.
ANSWER_WAIT_SECONDS = 20
ANSWER_STALE_SECONDS = 120
_MENTION_RE = re.compile(r"^\s*" + re.escape(KITCHEN_MENTION) + r"\b[\s,:;.!-]*", re.I)


def _strip_mention(body):
    """The question text if `body` is addressed to @kitchen, else None."""
    m = _MENTION_RE.match(body or "")
    return body[m.end():].strip() if m else None


def _viewing_servings():
    try:
        n = int(request.form.get("viewing_servings") or 0)
    except ValueError:
        return None
    return n if 0 < n <= 200 else None


def _run_answer(comment_id):
    """Start the answer job and wait up to ANSWER_WAIT_SECONDS for it."""
    app = current_app._get_current_object()
    t = threading.Thread(target=answer_question,
                         args=(app, comment_id, _viewing_servings()), daemon=True)
    t.start()
    t.join(timeout=ANSWER_WAIT_SECONDS)


def _ask_kitchen(recipe, question):
    back = url_for("wizard.recipe", recipe_id=recipe.id, _anchor="notes")
    if not question:
        flash(f"Add your question after {KITCHEN_MENTION}.", "info")
        return redirect(back)
    if len(question) > QUESTION_MAX_CHARS:
        flash(f"That question is too long for {KITCHEN_MENTION} "
              f"(max {QUESTION_MAX_CHARS} characters).", "error")
        return redirect(back)
    blocked = question_blocked_reason(current_user.id)
    if blocked:
        flash(blocked, "info")
        return redirect(back)
    c = RecipeComment(recipe_id=recipe.id, user_id=current_user.id, body=question,
                      kind="question", answer_status="pending")
    db.session.add(c)
    db.session.commit()
    _run_answer(c.id)
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id, _anchor=f"note-{c.id}"))


@wizard_bp.route("/recipe/<int:recipe_id>/comment/<int:comment_id>/retry", methods=["POST"])
def recipe_question_retry(recipe_id, comment_id):
    """Ask again after a failed (or stuck) answer. Counts like a new question
    against the per-user limit only in the sense that it's a fresh call, so the
    household limit is checked; the question row itself is reused."""
    c = _recipe_comment_or_404(recipe_id, comment_id)
    if not c.is_question or (c.answer_status == "pending" and not _answer_is_stale(c)):
        return redirect(url_for("wizard.recipe", recipe_id=recipe_id, _anchor=f"note-{c.id}"))
    lim = limits_today(current_user.id)
    if lim["household"] >= lim["household_limit"]:
        flash("The household has reached today's AI limit — try again after midnight.", "info")
        return redirect(url_for("wizard.recipe", recipe_id=recipe_id, _anchor=f"note-{c.id}"))
    c.answer_status = "pending"
    c.answer = None
    c.answered_at = utcnow()  # while pending: when this attempt started (stale guard)
    db.session.commit()
    _run_answer(c.id)
    return redirect(url_for("wizard.recipe", recipe_id=recipe_id, _anchor=f"note-{c.id}"))


def _answer_is_stale(c):
    """A pending answer older than ANSWER_STALE_SECONDS is treated as failed
    (worker restarted mid-answer, say): shown with a retry, never spinning."""
    created = c.answered_at or c.created_at  # a retry restarts the clock
    if created is None:
        return True
    now = datetime.now(timezone.utc)
    if created.tzinfo is None:
        now = now.replace(tzinfo=None)
    return (now - created).total_seconds() > ANSWER_STALE_SECONDS


def _recipe_comment_or_404(recipe_id, comment_id):
    """Fetch a RecipeComment, enforcing that it belongs to the given recipe —
    a comment id from another recipe 404s rather than being deletable via a
    mismatched URL. Mirrors _recipe_ingredient_or_404."""
    comment = db.session.get(RecipeComment, comment_id)
    if comment is None or comment.recipe_id != recipe_id:
        abort(404)
    return comment


@wizard_bp.route("/recipe/<int:recipe_id>/comment/<int:comment_id>/delete", methods=["POST"])
def recipe_comment_delete(recipe_id, comment_id):
    """Delete one's own note. Author-only, and there is deliberately no edit.

    A note is a signed, timestamped statement; another member removing it — or
    anyone silently rewriting it — reads wrong even in a trusting household.
    Delete exists for typos and mis-posts; the correction mechanism for a
    changed opinion is a second note. An author-less note (user_id NULL, only
    possible via a removed user) fails the check and can't be deleted here.
    """
    comment = _recipe_comment_or_404(recipe_id, comment_id)
    if comment.user_id != current_user.id:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("wizard.recipe", recipe_id=recipe_id, _anchor="notes"))


@wizard_bp.route("/recipe/<int:recipe_id>/share")
def recipe_share(recipe_id):
    """Chrome-free render of a recipe for screenshotting / print-to-PDF.

    Export, not publication: same login gate, same instance, no token, no public
    route — the user captures an image and shares that. Deliberately keeps the
    roadmap's 'no community/sharing platform' guardrail intact.
    """
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    if recipe.generation is not None:
        allergies, _, _ = combined_dietary(recipe.generation.cooking_for_user_ids or [])
    else:
        allergies = []
    return render_template(
        "wizard/recipe_share.html", recipe=recipe, allergy_caveat=bool(allergies),
    )


def _export_slug(title):
    """Title -> a lowercase-hyphenated filename stem ("Caramelised 'Assassin's'
    Spaghetti" -> "caramelised-assassins-spaghetti"). The website uses the
    filename as the recipe's URL, so this only has to be a sensible default."""
    text = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    text = re.sub(r"['\u2019]", "", text.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(slug) > 60:
        slug = slug[:60].rsplit("-", 1)[0]
    return slug or "recipe"


def _recipe_export_payload(recipe):
    """One recipe as portable JSON, for publishing on the website.

    The recipe contract plus its tags, and nothing household-specific: no
    notes, no author or cook names, no generation brief, no allergy caveat.
    """
    if recipe.ingredients:
        ingredients = [
            {"amount": ri.amount, "unit": ri.unit, "text": ri.raw_text, "to_buy": bool(ri.to_buy)}
            for ri in recipe.ingredients
        ]
    else:  # legacy row-less recipe, same fallback as the display
        ingredients = [
            {"amount": i.get("amount"), "unit": i.get("unit"), "text": i.get("item"),
             "to_buy": bool(i.get("to_buy"))}
            for i in (recipe.ingredients_json or [])
        ]

    def steps(items, with_timer=True):
        out = []
        for s in items or []:
            row = {"title": s.get("title") or "", "text": s.get("text") or ""}
            if with_timer:
                row["timer_minutes"] = s.get("timer_minutes") or None
            out.append(row)
        return out

    return {
        "format": "my-kitchen-recipe",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).date().isoformat(),
        "source": recipe.source or "ai",
        "title": recipe.title or "",
        "blurb": recipe.blurb or "",
        "intro": recipe.intro or "",
        "servings": recipe.servings,
        "meal_type": recipe.meal_type,
        "cuisine": recipe.cuisine,
        "time_band": recipe.time_band,
        "ingredients": ingredients,
        "prep": steps(recipe.prep_steps_json),
        "cook": steps(recipe.cook_steps_json),
        "tips": steps(recipe.tips_json, with_timer=False),
    }


@wizard_bp.route("/recipe/<int:recipe_id>/export.json")
def recipe_export(recipe_id):
    """Download one recipe as JSON, for the website's recipe pages.

    Same login gate as every other route, and the same export-not-publication
    stance as the share view: the user downloads a file and publishes it
    themselves. Nothing is exposed from the instance.
    """
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    body = json.dumps(_recipe_export_payload(recipe), ensure_ascii=False, indent=2) + "\n"
    return current_app.response_class(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{_export_slug(recipe.title)}.json"'},
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


@wizard_bp.route("/recipe/<int:recipe_id>/tags", methods=["POST"])
def recipe_set_tags(recipe_id):
    """Set a recipe's meal-type / cuisine tags from the inline editor. Works for
    any recipe (AI or user) — tags are a shared property, like ingredient links.
    Cuisine is gated server-side via _normalise_tags, so a stale hidden cuisine
    for a non-cuisine meal type is dropped regardless of what the client sent."""
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    meal_type, cuisine = _normalise_tags(
        request.form.get("meal_type"), request.form.get("cuisine")
    )
    recipe.meal_type = meal_type
    recipe.cuisine = cuisine
    db.session.commit()
    return jsonify(
        meal_type=meal_type, cuisine=cuisine,
        cuisine_allowed=bool(meal_type and meal_type_takes_cuisine(meal_type)),
    )


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


def _parse_ingredient_lines(imported=False):
    """Parse the picked ingredient rows. For a hand-made recipe each must link
    to an active catalogue ingredient (the form only lets you pick or
    add-and-pick) and raw_text is the *catalogue* name (server-trusted, not the
    client-sent label). An IMPORTED recipe (Phase 34) keeps the source's own
    wording as raw_text ("garlic cloves, crushed") and may save a line with no
    link yet — it shows "not linked" on the recipe page and can be linked
    there later. Returns (lines, error); fully-blank rows are skipped."""
    lines = []
    for i in _collect_indices("ing", "ingredient_id"):
        raw_id = (request.form.get(f"ing-{i}-ingredient_id") or "").strip()
        amount = (request.form.get(f"ing-{i}-amount") or "").strip()
        unit = (request.form.get(f"ing-{i}-unit") or "").strip()
        to_buy = request.form.get(f"ing-{i}-to_buy") == "on"
        name = (request.form.get(f"ing-{i}-name") or "").strip()
        raw = (request.form.get(f"ing-{i}-raw") or "").strip()[:200] if imported else ""
        if not raw_id and not amount and not unit and not name and not raw:
            continue  # blank row — ignore
        if not raw_id and raw:
            lines.append({"ingredient_id": None, "raw_text": raw, "amount": amount or None,
                          "unit": unit or None, "to_buy": to_buy})
            continue
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
            "raw_text": raw or ing.name,
            "amount": amount or None,
            "unit": unit or None,
            "to_buy": to_buy,
        })
    return lines, None


def _normalise_tags(meal_type_raw, cuisine_raw):
    """Validate + gate the two tags (shared by the create/edit form and the inline
    tag editor). Both optional. Cuisine is kept only when the meal type is set AND
    cuisine-bearing — mirrors the wizard hierarchy — else forced to None."""
    mt = (meal_type_raw or "").strip()
    meal_type = mt if mt in MEAL_TYPE_NAMES else None
    cu = (cuisine_raw or "").strip()
    cuisine = cu if cu in CUISINES else None
    if meal_type is None or not meal_type_takes_cuisine(meal_type):
        cuisine = None
    return meal_type, cuisine


def _save_recipe_from_form(recipe=None, source="user", source_url=None):
    """Create (recipe=None) or update a source='user' or 'imported' recipe in
    place. Writes the structured recipe_ingredients rows AND ingredients_json
    (display parity with AI recipes / keeps the 'still written' invariant).
    `source`/`source_url` apply when creating (Phase 34). Returns (recipe, error)."""
    if recipe is not None:
        source = recipe.source
    title = (request.form.get("title") or "").strip()
    blurb = (request.form.get("blurb") or "").strip()
    intro = (request.form.get("intro") or "").strip()
    meal_type, cuisine = _normalise_tags(
        request.form.get("meal_type"), request.form.get("cuisine")
    )
    # time_band is a free-standing display tag (Phase 18) — quick | relaxed | None.
    # Not gated by meal type (unlike cuisine); an unrecognised value -> None.
    time_band = (request.form.get("time_band") or "").strip()
    if time_band not in dict(TIME_BANDS):
        time_band = None
    try:
        servings = int(request.form.get("servings", ""))
    except (TypeError, ValueError):
        servings = 0

    prep = _parse_steps("prep", True)
    cook = _parse_steps("cook", True)
    tips = _parse_steps("tips", False)
    lines, line_err = _parse_ingredient_lines(imported=(source == "imported"))

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
        recipe = Recipe(source=source, generation_id=None,
                        created_by_user_id=current_user.id,
                        source_url=source_url if source == "imported" else None)
        db.session.add(recipe)

    recipe.title = title
    recipe.blurb = blurb or None
    recipe.intro = intro or None
    recipe.servings = servings
    recipe.meal_type = meal_type
    recipe.cuisine = cuisine
    recipe.time_band = time_band
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
            "raw": request.form.get(f"ing-{i}-raw") or "",
        })
    return {
        "title": request.form.get("title") or "",
        "blurb": request.form.get("blurb") or "",
        "intro": request.form.get("intro") or "",
        "servings": request.form.get("servings") or "",
        "meal_type": request.form.get("meal_type") or "",
        "cuisine": request.form.get("cuisine") or "",
        "time_band": request.form.get("time_band") or "",
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
            # The line's own wording, kept for imported recipes (Phase 34).
            "raw": ri.raw_text if recipe.source == "imported" else "",
        })
    return {
        "title": recipe.title or "",
        "blurb": recipe.blurb or "",
        "intro": recipe.intro or "",
        "servings": str(recipe.servings or ""),
        "meal_type": recipe.meal_type or "",
        "cuisine": recipe.cuisine or "",
        "time_band": recipe.time_band or "",
        "prep": steps(recipe.prep_steps_json, True),
        "cook": steps(recipe.cook_steps_json, True),
        "tips": steps(recipe.tips_json, False),
        "ingredients": ings,
    }


def _form_context(mode, recipe=None, from_form=False, prefill=None, source_url=None):
    """mode: "new" | "edit" | "import" (Phase 34: the create form, pre-filled
    from an import, as its review step)."""
    if prefill is not None:
        pass
    elif from_form:
        prefill = _collect_prefill_from_form()
    elif recipe is not None:
        prefill = _recipe_to_prefill(recipe)
    else:
        prefill = {"title": "", "blurb": "", "intro": "", "servings": "2",
                   "meal_type": "", "cuisine": "", "time_band": "",
                   "prep": [], "cook": [], "tips": [], "ingredients": []}
    link_catalogue = [
        {"id": i.id, "name": i.name}
        for i in Ingredient.query.filter_by(is_active=True)
                                 .order_by(db.func.lower(Ingredient.name)).all()
    ]
    categories = Category.query.order_by(*Category.ordering()).all()
    action = (url_for("wizard.recipe_edit", recipe_id=recipe.id)
              if (mode == "edit" and recipe is not None)
              else url_for("wizard.recipe_new"))
    return {
        "mode": mode, "recipe": recipe, "form_action": action,
        "prefill": prefill, "link_catalogue": link_catalogue,
        "categories": categories, "meal_types": MEAL_TYPE_NAMES,
        "cuisines": CUISINES, "cuisine_meal_types": CUISINE_MEAL_TYPES,
        "time_bands": TIME_BANDS,
        "source_url": source_url or (recipe.source_url if recipe is not None else None),
        "imported": mode == "import" or (recipe is not None and recipe.source == "imported"),
    }


def _clean_source_url(raw):
    raw = (raw or "").strip()[:500]
    return raw if urlparse(raw).scheme in ("http", "https") else None


@wizard_bp.route("/recipe/new", methods=["GET", "POST"])
def recipe_new():
    if request.method == "POST":
        imported = request.form.get("source") == "imported"
        source_url = _clean_source_url(request.form.get("source_url"))
        recipe, error = _save_recipe_from_form(
            None, source="imported" if imported else "user", source_url=source_url)
        if error:
            flash(error, "error")
            return render_template("wizard/recipe_form.html", **_form_context(
                "import" if imported else "new", from_form=True, source_url=source_url))
        flash("Recipe imported." if imported else "Recipe created.", "success")
        return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
    return render_template("wizard/recipe_form.html", **_form_context("new"))


@wizard_bp.route("/recipe/<int:recipe_id>/edit", methods=["GET", "POST"])
def recipe_edit(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    # Only hand-created and imported recipes are editable here. AI recipes'
    # links are edited inline on the recipe page (Phase 4a); their bodies
    # aren't hand-editable.
    if recipe.source not in ("user", "imported"):
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


@wizard_bp.route("/recipe/add")
def recipe_add():
    """The one way in to adding a recipe: a choice of how (0.34.1). By hand ->
    the create form; from the web -> the import page."""
    return render_template("wizard/recipe_add.html")


@wizard_bp.route("/recipe/import", methods=["GET", "POST"])
def recipe_import():
    """Import a recipe from a web page or pasted text (Phase 34). Success
    renders the create form, pre-filled, as the review step; nothing is saved
    until the cook presses Save there."""
    url = (request.form.get("url") or "").strip()
    text = request.form.get("text") or ""
    if request.method == "POST":
        blocked = import_blocked_reason(current_user.id)
        problem = blocked
        if not blocked:
            try:
                recipe, source_url = import_recipe(current_app.config, current_user.id,
                                                   url=url or None, text=text)
            except ImportProblem as e:
                problem = str(e)
            else:
                return render_template("wizard/recipe_form.html", **_form_context(
                    "import", prefill=_import_prefill(recipe), source_url=source_url))
        flash(problem, "error")
    return render_template("wizard/recipe_import.html", url=url, text=text)


def _import_prefill(r):
    """An importer recipe dict -> the create form's prefill shape."""
    meal_type, cuisine = _normalise_tags(r.get("meal_type"), r.get("cuisine"))

    def steps(items, with_timer):
        out = []
        for st in items:
            row = {"title": st["title"], "text": st["text"]}
            if with_timer:
                row["timer"] = str(st["timer_minutes"]) if st.get("timer_minutes") else ""
            out.append(row)
        return out
    return {
        "title": r["title"], "blurb": r["blurb"], "intro": r["intro"],
        "servings": str(r["servings"]), "meal_type": meal_type or "",
        "cuisine": cuisine or "", "time_band": r.get("time_band") or "",
        "prep": steps(r["prep"], True), "cook": steps(r["cook"], True),
        "tips": steps(r["tips"], False),
        "ingredients": [{
            "ingredient_id": str(i["ingredient_id"]) if i.get("ingredient_id") else "",
            "name": i.get("name") or "", "raw": i["item"],
            "amount": i["amount"], "unit": i["unit"], "to_buy": False,
        } for i in r["ingredients"]],
    }


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


@wizard_bp.route("/recipe/<int:recipe_id>/archive", methods=["POST"])
def recipe_archive(recipe_id):
    """Archive one recipe from its own page (Phase 24). Household-wide and
    reversible: the page stays put and shows a restore banner, which is the
    undo."""
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    if not recipe.is_archived:
        recipe.archived_at = utcnow()
        recipe.archived_by_user_id = current_user.id
        db.session.commit()
    flash("Archived — it's out of your lists. Restore it any time.", "success")
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id))


@wizard_bp.route("/recipe/<int:recipe_id>/restore", methods=["POST"])
def recipe_restore(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    recipe.archived_at = None
    recipe.archived_by_user_id = None
    db.session.commit()
    flash("Restored to your recipes.", "success")
    nxt = request.form.get("next")
    if nxt == "archive":
        return redirect(url_for("history.archived"))
    return redirect(url_for("wizard.recipe", recipe_id=recipe.id))
