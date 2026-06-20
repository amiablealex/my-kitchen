from ..extensions import db
from ..models import Ingredient, Equipment, Generation, Recipe, User
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import extract_json, validate_and_normalize
from .providers import get_provider, ProviderError
from .seeds import pick_seed

MAX_ATTEMPTS = 2  # initial call + one retry on malformed output, per the spec

def default_user_id():
    u = User.query.first()
    return u.id if u else None


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

    return {
        "must_use": must_use,
        "available": available,
        "staples": staples,
        "equipment": equipment,
        "cuisine": wizard_state.get("cuisine", "Surprise me"),
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


def run_generation(app_config, wizard_state, time_label, user_id=None):
    """Returns (generation, error_msg). error_msg is None on success."""
    brief = build_brief(wizard_state, time_label, app_config)
    user_prompt = build_user_prompt(brief)

    gen = Generation(
        created_by_user_id=user_id,
        cuisine=brief["cuisine"],
        time_band=brief["time_band"],
        servings=brief["servings"],
        cooking_for_user_ids=brief["cooking_for_user_ids"],
        guest_count=brief["guest_count"],
        selected_ingredient_ids=wizard_state.get("selected_ingredient_ids") or [],
        creative_seed=brief["creative_seed"],
        raw_prompt=user_prompt,
    )

    try:
        provider = get_provider(app_config)
    except ProviderError as e:
        gen.model = app_config.get("LLM_PROVIDER", "")
        gen.error = str(e)
        db.session.add(gen)
        db.session.commit()
        return gen, str(e)

    gen.model = f"{provider.name}:{provider.model}"

    last_error, last_raw, normalized = None, None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            last_raw = provider.generate(SYSTEM_PROMPT, user_prompt, brief=brief)
            normalized = validate_and_normalize(extract_json(last_raw))
            break
        except ProviderError as e:
            last_error = f"Provider error: {e}"
            break  # don't retry a hard API/key error
        except ValueError as e:
            last_error = f"Malformed output (attempt {attempt}): {e}"
            continue  # retry on bad JSON / schema

    if normalized is None:
        gen.error = last_error or "Generation failed."
        db.session.add(gen)
        db.session.commit()
        return gen, gen.error

    db.session.add(gen)
    db.session.flush()  # assign gen.id before adding recipes
    for r in normalized:
        db.session.add(Recipe(
            generation_id=gen.id,
            title=r["title"],
            blurb=r["blurb"],
            servings=r["servings"] or brief["servings"],
            ingredients_json=r["ingredients"],
            prep_steps_json=r["prep"],
            cook_steps_json=r["cook"],
            raw_response=last_raw,
        ))
    db.session.commit()
    return gen, None
