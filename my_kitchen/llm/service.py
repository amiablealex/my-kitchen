from ..extensions import db
from ..models import Ingredient, Generation, Recipe
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import extract_json, validate_and_normalize
from .providers import get_provider, ProviderError

MAX_ATTEMPTS = 2  # initial call + one retry on malformed output, per the spec

def default_user_id():
    u = User.query.first()
    return u.id if u else None


def build_brief(wizard_state, time_label):
    selected_ids = wizard_state.get("selected_ingredient_ids") or []
    selected = []
    if selected_ids:
        rows = Ingredient.query.filter(Ingredient.id.in_(selected_ids)).all()
        selected = [{"name": r.name, "note": r.note} for r in rows]
    staples = [r.name for r in Ingredient.query.filter_by(is_staple=True, in_stock=True, is_active=True).all()]
    return {
        "ingredients": selected,
        "staples": staples,
        "cuisine": wizard_state.get("cuisine", "Surprise me"),
        "time_band": wizard_state.get("time_band", "quick"),
        "time_label": time_label,
        "servings": wizard_state.get("servings", 2),
    }


def run_generation(app_config, wizard_state, time_label, user_id=None):
    """Returns (generation, error_msg). error_msg is None on success."""
    brief = build_brief(wizard_state, time_label)
    user_prompt = build_user_prompt(brief)

    gen = Generation(
        created_by_user_id=user_id,
        cuisine=brief["cuisine"],
        time_band=brief["time_band"],
        servings=brief["servings"],
        cooking_for_user_ids=[],
        guest_count=0,
        selected_ingredient_ids=wizard_state.get("selected_ingredient_ids") or [],
        creative_seed="",  # MVP: no creative seed yet
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
