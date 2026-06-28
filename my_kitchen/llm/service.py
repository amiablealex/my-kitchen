import threading

from ..extensions import db
from ..models import (
    Ingredient, Equipment, Generation, Recipe, RecipeIngredient, User,
    DEFAULT_MEAL_TYPE, meal_type_takes_cuisine, recipe_cuisine_from,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import extract_json, validate_and_normalize
from .providers import get_provider, ProviderError
from .seeds import pick_seed
# Deterministic free-text -> catalogue resolver (Phase 3a), wired into the write
# path here in 3b. build_index is built ONCE per generation and reused; the index
# is plain data (no ORM objects), so it's safe to use across both recipes.
from ..resolver import build_index, resolve_with_index
from ..resolver.db import load_catalogue
from ..resolver.aliases import ALIASES

MAX_ATTEMPTS = 2  # initial call + one retry on malformed output, per the spec

def default_user_id():
    u = User.query.first()
    return u.id if u else None


def _text_or_none(value):
    """Store an AI ingredient amount/unit verbatim as text. The model emits
    `amount` untouched — it may be a number (2), a string ("a splash", "½"), or
    empty — so we stringify and treat empty/whitespace as NULL. `unit` is already
    a (possibly empty) string. raw_text carries the full display string anyway;
    this just keeps the structured columns faithful without a numeric type that
    would reject non-numeric amounts."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _is_truncated(finish_reason):
    """True when the model stopped because it hit the token ceiling. Handles
    Anthropic 'max_tokens' and Gemini 'FinishReason.MAX_TOKENS' shapes."""
    s = str(finish_reason).lower()
    return "max_token" in s or "length" in s


def combined_dietary(user_ids):
    """Union of the selected users' dietary tags, de-duplicated, split into
    (allergies, preferences) name lists. The single source of truth for the
    dietary split — used both by the review screen and the brief."""
    allergies, preferences = [], []
    if not user_ids:
        return allergies, preferences
    users = User.query.filter(User.id.in_(user_ids)).all()
    seen = set()
    for u in users:
        for tag in u.dietary_tags:
            key = (tag.type, tag.name.lower())
            if key in seen:
                continue
            seen.add(key)
            (allergies if tag.type == "allergy" else preferences).append(tag.name)
    return sorted(allergies), sorted(preferences)


def recent_recipe_titles(limit):
    """The most recent recipe titles across the whole household, de-duplicated
    case-insensitively, newest first. Feeds the anti-repetition steer. Both
    recipes of each generation count (either could be cooked again)."""
    if not limit or limit <= 0:
        return []
    rows = (
        Recipe.query
        .order_by(Recipe.created_at.desc(), Recipe.id.desc())
        .limit(limit * 4)  # over-fetch so de-dup still yields up to `limit`
        .all()
    )
    seen, titles = set(), []
    for r in rows:
        key = (r.title or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        titles.append(r.title)
        if len(titles) >= limit:
            break
    return titles


def build_brief(wizard_state, time_label, app_config):
    # MUST-USE: the wizard-selected ingredients, with notes. Retired items are
    # dropped (a retired ingredient shouldn't appear anywhere); an out-of-stock
    # selection is KEPT — an explicit choice wins over its stock state.
    selected_ids = wizard_state.get("selected_ingredient_ids") or []
    must_use, must_use_ids = [], set()
    if selected_ids:
        rows = (
            Ingredient.query
            .filter(Ingredient.id.in_(selected_ids), Ingredient.is_active.is_(True))
            .all()
        )
        must_use = [{"name": r.name, "note": r.note} for r in rows]
        must_use_ids = {r.id for r in rows}

    # AVAILABLE: everything else in stock (active, non-staple) that ISN'T already
    # must-use — passed every time so the model can round out the meal. This is
    # the key change: previously only the selected items were fed.
    available_rows = Ingredient.query.filter_by(
        in_stock=True, is_staple=False, is_active=True
    ).all()
    available = [
        {"name": r.name, "note": r.note}
        for r in available_rows if r.id not in must_use_ids
    ]

    # STAPLES: active, in-stock staples, assumed available and used freely.
    staples = [
        r.name for r in Ingredient.query.filter_by(
            is_staple=True, in_stock=True, is_active=True
        ).all()
    ]

    # EQUIPMENT: only what's currently available (is_available = true).
    equipment = [
        e.name for e in Equipment.query.filter_by(is_available=True)
        .order_by(db.func.lower(Equipment.name)).all()
    ]

    cooking_for_ids = wizard_state.get("cooking_for_user_ids") or []
    guest_count = int(wizard_state.get("guest_count") or 0)
    allergies, preferences = combined_dietary(cooking_for_ids)

    # Meal type (Phase 11) + defensive cuisine suppression. The wizard's step-2
    # POST already nulls cuisine for non-cuisine meal types; we re-assert it here
    # so the brief is correct even if the session value is stale. The server is
    # authoritative — the wizard's JS show/hide is cosmetic only.
    meal_type = wizard_state.get("meal_type", DEFAULT_MEAL_TYPE)
    cuisine = wizard_state.get("cuisine", "Surprise me")
    if not meal_type_takes_cuisine(meal_type):
        cuisine = None

    return {
        "must_use": must_use,
        "available": available,
        "staples": staples,
        "equipment": equipment,
        "meal_type": meal_type,
        "cuisine": cuisine,
        "time_band": wizard_state.get("time_band", "quick"),
        "time_label": time_label,
        "servings": len(cooking_for_ids) + guest_count,
        "cooking_for_user_ids": cooking_for_ids,
        "guest_count": guest_count,
        "allergies": allergies,
        "preferences": preferences,
        "recent_titles": recent_recipe_titles(
            int(app_config.get("LLM_RECENT_TITLES_N", 10))
        ),
        "creative_seed": pick_seed(),
    }


def start_generation(app, wizard_state, time_label, user_id=None):
    """Synchronous starter — runs INSIDE the request. Does only fast, reliable
    work: build the brief (DB reads) + user_prompt (string assembly), create the
    Generation row as status="running", commit, then hand the slow/fallible part
    (the LLM call) to a background daemon thread. Returns the new generation_id.

    The brief is built ONCE here and passed to the thread, so the stored
    creative_seed matches what's actually used and stock is read at click time
    (rebuilding it in the thread would re-roll the seed and re-read stock).

    `app` is the real application object (current_app._get_current_object() from
    the caller), passed so the thread can push its own app context — never rely
    on current_app / the request session across the thread boundary.
    """
    brief = build_brief(wizard_state, time_label, app.config)
    user_prompt = build_user_prompt(brief)

    gen = Generation(
        created_by_user_id=user_id,
        cuisine=brief["cuisine"],
        meal_type=brief["meal_type"],
        time_band=brief["time_band"],
        servings=brief["servings"],
        cooking_for_user_ids=brief["cooking_for_user_ids"],
        guest_count=brief["guest_count"],
        selected_ingredient_ids=wizard_state.get("selected_ingredient_ids") or [],
        creative_seed=brief["creative_seed"],
        raw_prompt=user_prompt,
        status="running",
    )
    db.session.add(gen)
    db.session.commit()  # assigns gen.id and makes the running row visible to polls
    generation_id = gen.id

    # Pass only primitives across the boundary: the app object, the row id, the
    # prompt string, and the plain-data brief dict. NO ORM objects, NO request
    # session. The thread re-queries the row by id inside its own context.
    thread = threading.Thread(
        target=_run_generation_job,
        args=(app, generation_id, user_prompt, brief),
        daemon=True,
    )
    thread.start()
    return generation_id


def _run_generation_job(app, generation_id, user_prompt, brief):
    """Background thread body — runs OUTSIDE any request. Pushes its own app
    context, uses a FRESH db session, re-queries the Generation by id, and runs
    only the genuinely slow/fallible part: provider call -> retry-once loop ->
    validate/normalize -> write the two Recipe rows -> set status. Recipes and
    status="done" are written in ONE commit, so a poll on the *other* gunicorn
    worker never sees "done" before the recipes exist. Session is cleaned up in
    a finally so the thread leaves no connection behind.
    """
    with app.app_context():
        try:
            gen = db.session.get(Generation, generation_id)
            if gen is None:
                return  # row vanished (deleted mid-flight) — nothing to do

            try:
                provider = get_provider(app.config)
            except ProviderError as e:
                gen.model = app.config.get("LLM_PROVIDER", "")
                gen.error = str(e)
                gen.status = "error"
                db.session.commit()
                return

            gen.model = f"{provider.name}:{provider.model}"

            last_error, last_raw, normalized = None, None, None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    last_raw = provider.generate(SYSTEM_PROMPT, user_prompt, brief=brief)
                    finish = getattr(provider, "last_finish_reason", None)
                    if finish is not None and _is_truncated(finish):
                        # Output hit the token ceiling — retrying won't help; the
                        # recipe is just longer than max_tokens allows. Fail
                        # honestly instead of letting the half-finished JSON
                        # surface as a parser error.
                        last_error = (
                            "The recipes came back longer than the current limit "
                            "and got cut off. Try again, or raise LLM_MAX_TOKENS."
                        )
                        break
                    normalized = validate_and_normalize(extract_json(last_raw))
                    break
                except ProviderError as e:
                    last_error = f"Provider error: {e}"
                    break  # don't retry a hard API/key error
                except ValueError as e:
                    last_error = f"Malformed output (attempt {attempt}): {e}"
                    continue  # retry on bad JSON / schema
                except Exception as e:  # last-resort safety net
                    last_error = f"Unexpected generation error (attempt {attempt}): {e}"
                    break

            if normalized is None:
                gen.error = last_error or "Generation failed."
                gen.status = "error"
                db.session.commit()
                return

            # Build the resolver index ONCE for this generation, before the recipe
            # loop. load_catalogue() hits the DB (active ingredients incl. staples,
            # excl. retired); building the index per-ingredient would be needlessly
            # slow. It's plain data, reused for both recipes. Runs inside this
            # thread's app context + session (Phase 12), which load_catalogue()
            # needs — already established here. Generation stays SEALED: this is a
            # strictly post-hoc pass over the model's free-text output.
            index = build_index(load_catalogue(), ALIASES)

            for r in normalized:
                recipe = Recipe(
                    generation_id=gen.id,
                    title=r["title"],
                    blurb=r["blurb"],
                    intro=r["intro"],
                    servings=r["servings"] or brief["servings"],
                    ingredients_json=r["ingredients"],  # unchanged — still the display source this phase
                    prep_steps_json=r["prep"],
                    cook_steps_json=r["cook"],
                    tips_json=r["tips"],
                    raw_response=last_raw,
                    # Keystone meta (Phase 3b): provenance + forward-copied fields so
                    # post-3b recipes are suggestion-ready.
                    source="ai",
                    meal_type=gen.meal_type,
                    cuisine=recipe_cuisine_from(gen.cuisine),
                    created_by_user_id=gen.created_by_user_id,
                )
                # Resolve each free-text ingredient to a catalogue id and write a
                # structured recipe_ingredients row. Resolve the `item` STRING only;
                # amount/unit/to_buy/position are preserved verbatim. to_buy items
                # are resolved too — to_buy means not-in-stock, not off-catalogue, so
                # many still link. Unmatched -> ingredient_id None (degrades
                # gracefully). Appended via the relationship so the rows land in the
                # SAME atomic commit as the recipe + status="done" below — a poll on
                # the other gunicorn worker never sees a half-linked recipe.
                for position, ing in enumerate(r["ingredients"]):
                    item = ing.get("item", "")
                    result = resolve_with_index(item, index)
                    recipe.ingredients.append(RecipeIngredient(
                        raw_text=item,
                        amount=_text_or_none(ing.get("amount")),
                        unit=_text_or_none(ing.get("unit")),
                        to_buy=bool(ing.get("to_buy", False)),
                        position=position,
                        ingredient_id=result.ingredient_id,
                    ))
                db.session.add(recipe)
            gen.status = "done"
            db.session.commit()  # recipes + recipe_ingredients + status="done" land together, atomically
        except Exception as e:
            # Truly unexpected (e.g. a DB error mid-write). Roll back the broken
            # transaction, then record the failure on a freshly-fetched row.
            db.session.rollback()
            try:
                gen = db.session.get(Generation, generation_id)
                if gen is not None:
                    gen.error = f"Unexpected generation error: {e}"
                    gen.status = "error"
                    db.session.commit()
            except Exception:
                db.session.rollback()
        finally:
            db.session.remove()
