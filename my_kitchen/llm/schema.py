import json
import re


def extract_json(raw_text):
    """Pull a JSON object out of model text that may be wrapped in prose or
```json fences. Returns the parsed object or raises ValueError."""
    if not raw_text:
        raise ValueError("empty response")
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in response")
    return json.loads(text[start:end + 1])  # JSONDecodeError is a ValueError


def _coerce_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_step(step):
    if not isinstance(step, dict):
        raise ValueError("step is not an object")
    text = str(step.get("text", "")).strip()
    if not text:
        raise ValueError("step missing text")
    timer = step.get("timer_minutes", None)
    if timer is not None:
        timer = _coerce_int(timer, None)
    return {"title": str(step.get("title", "")).strip(), "text": text, "timer_minutes": timer}


def _normalize_tip(tip):
    """Tips are optional and non-essential: a malformed entry is skipped, never
    fatal. Returns {title, text}, or None to drop the entry."""
    if not isinstance(tip, dict):
        return None
    text = str(tip.get("text", "")).strip()
    if not text:
        return None
    return {"title": str(tip.get("title", "")).strip(), "text": text}


def _normalize_ingredient(ing):
    if not isinstance(ing, dict):
        raise ValueError("ingredient is not an object")
    item = str(ing.get("item", "")).strip()
    if not item:
        raise ValueError("ingredient missing item")
    return {
        "item": item,
        "amount": ing.get("amount", ""),
        "unit": str(ing.get("unit", "")).strip(),
        "to_buy": bool(ing.get("to_buy", False)),
    }


def _normalize_recipe(recipe):
    if not isinstance(recipe, dict):
        raise ValueError("recipe is not an object")
    title = str(recipe.get("title", "")).strip()
    if not title:
        raise ValueError("recipe missing title")
    for key in ("ingredients", "prep", "cook"):
        if not isinstance(recipe.get(key), list):
            raise ValueError(f"recipe '{key}' is not a list")
    ingredients = [_normalize_ingredient(i) for i in recipe["ingredients"]]
    if not ingredients:
        raise ValueError("recipe has no ingredients")
    cook = [_normalize_step(s) for s in recipe["cook"]]
    if not cook:
        raise ValueError("recipe has no cook steps")

    # intro: contract asks for it, but treated LENIENTLY — a missing/blank intro
    # is stored empty rather than failing an otherwise-good two-recipe response.
    intro = str(recipe.get("intro", "")).strip()

    # tips: optional. A list; malformed entries dropped; absent/empty -> [].
    tips_raw = recipe.get("tips")
    tips = []
    if isinstance(tips_raw, list):
        tips = [t for t in (_normalize_tip(x) for x in tips_raw) if t]

    return {
        "title": title,
        "blurb": str(recipe.get("blurb", "")).strip(),
        "intro": intro,
        "servings": _coerce_int(recipe.get("servings", 0), 0),
        "ingredients": ingredients,
        "prep": [_normalize_step(s) for s in recipe["prep"]],
        "cook": cook,
        "tips": tips,
    }


def validate_and_normalize(data, count=2):
    """Validate the §5.2 contract. Returns a normalised list of exactly `count`
    recipe dicts (2 for generation, 1 for a refine — Phase 26), or raises
    ValueError describing the first problem found."""
    if not isinstance(data, dict):
        raise ValueError("top-level response is not an object")
    recipes = data.get("recipes")
    if not isinstance(recipes, list):
        raise ValueError("'recipes' is missing or not a list")
    if len(recipes) < count:
        raise ValueError(f"expected {count} recipe(s), got {len(recipes)}")
    return [_normalize_recipe(r) for r in recipes[:count]]
