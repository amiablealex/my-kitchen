"""Golden briefs for the recipe eval harness (flask eval-recipes).

Each entry is a standalone brief fed straight into build_user_prompt -> provider,
bypassing the DB->brief assembly (4a tested that deterministically). 4b tests
whether a GOOD brief yields GOOD recipes.

Per entry:
  name   - short id; used in the report and as a section header.
  brief  - the CLEAN prompt-input dict (exactly what build_user_prompt expects).
           creative_seed pinned + recent_titles fixed empty, so the only moving
           variable between eval runs is the prompt itself.
  assert - eval-ONLY metadata, kept OUT of `brief` so it never leaks into the
           prompt. Crude substring keyword checks (a floor, not a grader):
             required  : must appear in BOTH recipes (surviving must-use items).
             forbidden : must NOT appear in EITHER recipe (allergens — incl. an
                         allergen that was ALSO must-use, where allergy wins).
             max_to_buy: ceiling on to_buy items per recipe (default 2).
  note   - one-line "what good looks like" cue (fuller version in examples.md).

NB a tag like "Peanut allergy" won't substring-match "peanuts", so allergen
checks carry their own explicit `forbidden` keyword. Distinctness beyond "titles
differ" stays a human call.
"""

# A generous, realistic "well-stocked kitchen" — shared by most briefs.
STAPLES = [
    "olive oil", "vegetable oil", "salt", "black pepper", "cumin", "coriander seeds",
    "paprika", "turmeric", "chilli flakes", "dried mixed herbs", "plain flour",
    "stock cubes", "soy sauce", "tomato puree", "garlic", "honey", "lemon",
]

QUICK = ("quick", "Quick (under 30 min)")
RELAXED = ("relaxed", "Relaxed (30–75 min)")


def _ing(name, note=None):
    return {"name": name, "note": note}


GOLDEN_BRIEFS = [
    {
        "name": "ratatouille_batch",
        "note": "Big batch; real depth (caramelised veg, not boiled). Intro frames "
                "the dish; two distinct ways to use the same veg.",
        "brief": {
            "must_use": [_ing("aubergine"), _ing("bell pepper"), _ing("chestnut mushrooms"),
                         _ing("brown onion"), _ing("baby spinach"), _ing("carrots", "4 small"),
                         _ing("garlic"), _ing("fresh ginger"), _ing("red onion", "2 small"),
                         _ing("sweet potato", "small")],
            "available": [_ing("dry red lentils"), _ing("chickpeas", "tinned"),
                          _ing("chopped tomatoes", "tinned")],
            "staples": STAPLES, "equipment": ["large baking dish", "blender"],
            "allergies": [], "preferences": [],
            "cuisine": "Mediterranean", "time_band": RELAXED[0], "time_label": RELAXED[1],
            "servings": 6, "recent_titles": [],
            "creative_seed": "build deep, well-browned caramelisation into the dish",
        },
        "assert": {"required": ["aubergine", "pepper"], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "salmon_med_traybake",
        "note": "Salmon hero, rounded out from the pantry. Want a staggered-timing "
                "game plan so the salmon stays juicy, a bright acid finish, and an "
                "intro on why oily Med veg suit salmon.",
        "brief": {
            "must_use": [_ing("salmon fillet", "2 fillets")],
            "available": [_ing("basmati rice"), _ing("carrot"), _ing("red onion"),
                          _ing("sweet potato"), _ing("baking potato"), _ing("brown onion"),
                          _ing("couscous"), _ing("chickpeas"), _ing("chopped tomatoes"),
                          _ing("black olives")],
            "staples": STAPLES, "equipment": ["large baking tray", "oven"],
            "allergies": [], "preferences": [],
            "cuisine": "Mediterranean", "time_band": RELAXED[0], "time_label": RELAXED[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "lift everything with bright, fresh acidity",
        },
        "assert": {"required": ["salmon"], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "seabass_quick",
        "note": "Quick (<30). All four must-use present in both. Depth despite "
                "speed; a real doneness cue for the fish (flakes, opaque).",
        "brief": {
            "must_use": [_ing("seabass fillet", "2 fillets"), _ing("tenderstem broccoli"),
                         _ing("spring onions"), _ing("fresh coriander")],
            "available": [_ing("garlic"), _ing("red onion"), _ing("red pepper"),
                          _ing("chestnut mushrooms"), _ing("rice"), _ing("baking potato"),
                          _ing("quinoa")],
            "staples": STAPLES, "equipment": ["wok", "frying pan"],
            "allergies": [], "preferences": [],
            "cuisine": "Asian", "time_band": QUICK[0], "time_label": QUICK[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "use gentle South-East Asian aromatics (lemongrass, lime, ginger)",
        },
        "assert": {"required": ["seabass", "broccoli", "spring onion", "coriander"],
                   "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "veg_curry_chickpea_tofu",
        "note": "Authentic-feeling curry with a spice blend from common cupboard "
                "spices (toasted/bloomed). Intro frames the blend; steps teach "
                "blooming spices and the doneness of the onion base.",
        "brief": {
            "must_use": [_ing("chopped tomatoes", "2 x 400g tins"),
                         _ing("coconut milk", "400ml tin"), _ing("tofu", "225g block"),
                         _ing("brown onion", "2 large"), _ing("chickpeas", "tinned")],
            "available": [_ing("baby spinach"), _ing("red pepper")],
            "staples": STAPLES, "equipment": ["large pan", "blender"],
            "allergies": [], "preferences": ["Vegetarian"],
            "cuisine": "Indian", "time_band": RELAXED[0], "time_label": RELAXED[1],
            "servings": 4, "recent_titles": [],
            "creative_seed": "let warming toasted spices lead",
        },
        "assert": {"required": ["tofu", "chickpea", "coconut"], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "empty_pantry_staples_only",
        "note": "Genuinely empty pantry -> cook from staples ALONE (e.g. a quick "
                "flatbread, a store-cupboard number). Must NOT invent fresh produce "
                "as available; extras only via <=2 to_buy. Two distinct ideas.",
        "brief": {
            "must_use": [], "available": [],
            "staples": STAPLES, "equipment": ["oven", "frying pan"],
            "allergies": [], "preferences": [],
            "cuisine": "Surprise me", "time_band": QUICK[0], "time_label": QUICK[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "keep it rustic and Italian-simple",
        },
        "assert": {"required": [], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "blank_must_use_whole_pantry",
        "note": "No must-use -> design freely from the WHOLE pantry (not staples-"
                "only). Should actually use several available items across two "
                "distinct dishes.",
        "brief": {
            "must_use": [],
            "available": [_ing("chicken breast"), _ing("eggs"), _ing("rice"),
                          _ing("potato"), _ing("onion"), _ing("carrot"),
                          _ing("broccoli"), _ing("tomato"), _ing("cheddar cheese"),
                          _ing("milk")],
            "staples": STAPLES, "equipment": ["oven", "frying pan", "saucepan"],
            "allergies": [], "preferences": [],
            "cuisine": "Surprise me", "time_band": RELAXED[0], "time_label": RELAXED[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "go garlicky and aromatic",
        },
        "assert": {"required": [], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "veg_chicken_override",
        "note": "Preference (vegetarian) vs must-use (chicken): chicken MUST be used "
                "(must-use beats a soft preference). Both recipes contain chicken; "
                "the preference only steers the available tier.",
        "brief": {
            "must_use": [_ing("chicken breast")],
            "available": [_ing("onion"), _ing("carrot"), _ing("potato"),
                          _ing("rice"), _ing("broccoli")],
            "staples": STAPLES, "equipment": ["oven", "frying pan"],
            "allergies": [], "preferences": ["Vegetarian"],
            "cuisine": "Surprise me", "time_band": QUICK[0], "time_label": QUICK[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "build a smoky-sweet, gently spiced warmth",
        },
        "assert": {"required": ["chicken"], "forbidden": [], "max_to_buy": 2},
    },
    {
        "name": "peanut_allergen_as_must_use",
        "note": "SAFETY: peanut is must-use AND an allergen for a diner. Allergy "
                "WINS — peanut is dropped, appearing in NEITHER recipe (and no "
                "peanut oil / satay sneaking in).",
        "brief": {
            "must_use": [_ing("peanuts", "want to use these up")],
            "available": [_ing("chicken breast"), _ing("rice"), _ing("broccoli"),
                          _ing("red pepper")],
            "staples": STAPLES, "equipment": ["wok"],
            "allergies": ["Peanut allergy"], "preferences": [],
            "cuisine": "Asian", "time_band": QUICK[0], "time_label": QUICK[1],
            "servings": 2, "recent_titles": [],
            "creative_seed": "balance chilli heat against something cooling",
        },
        "assert": {"required": [], "forbidden": ["peanut", "satay"], "max_to_buy": 2},
    },
    {
        "name": "dessert_no_cuisine",
        "note": "Meal type = Dessert with NO cuisine (cuisine omitted from the brief "
                "entirely). Chocolate + eggs must-use -> an indulgent dessert "
                "(mousse / fondant / brownie). Exercises the meal-type line AND the "
                "cuisine-omission path in one test; both recipes should read as "
                "desserts, never savoury.",
        "brief": {
            "must_use": [_ing("dark chocolate", "100g bar"), _ing("eggs", "3 large")],
            "available": [_ing("butter"), _ing("caster sugar"), _ing("double cream"),
                          _ing("vanilla extract"), _ing("milk"), _ing("strawberries")],
            "staples": STAPLES, "equipment": ["oven", "saucepan", "whisk"],
            "allergies": [], "preferences": [],
            "meal_type": "Dessert", "cuisine": None,
            "time_band": RELAXED[0], "time_label": RELAXED[1],
            "servings": 4, "recent_titles": [],
            "creative_seed": "play a warm element against a cool, creamy one",
        },
        "assert": {"required": ["chocolate", "egg"], "forbidden": [], "max_to_buy": 2},
    },
]
