"""Creative seeds — small curated lists of flavour angles, techniques and
regional sub-styles used purely to nudge variety across generations.

One seed is picked at random per generation and offered to the FIRST recipe
only, as an *optional bias*: the model is explicitly told it may ignore it, and
the user-chosen cuisine always takes priority. The seeds exist for randomness,
not to dictate the dish. The chosen seed is stored on Generation.creative_seed
for reproducibility/debugging.

Seeds are meal-type aware:
  * SAVOURY_SEEDS — the default pool, for the cuisine-bearing meal types
                    (Breakfast, Lunch, Dinner, Snack, Side dish).
  * SWEET_SEEDS   — for Dessert and Baking, where a savoury angle
                    ("go garlicky", "lean into umami") is actively wrong.
  * No seed       — for "Sauce or dressing": a sauce is small and focused, so a
                    random creative angle is noise rather than variety.

SAVOURY_SEEDS content is deliberately unchanged from the original single list,
so the tuned savoury/Dinner goldens render byte-identically.
"""
import random

SAVOURY_SEEDS = [
    # Techniques
    "lean on smoky char from a hot pan, grill or griddle",
    "build deep, well-browned caramelisation into the dish",
    "keep it to a single pan or one tray",
    "add a quick pickle or sharp pickled element for contrast",
    "finish with a crunchy topping or textural garnish",
    "bring it together with a silky emulsified or pan sauce",
    "use gentle braising for meltingly tender results",
    "pair something hot with a fresh, no-cook element alongside",
    # Flavour angles
    "lift everything with bright, fresh acidity",
    "lean into deep umami (miso, anchovy, mushroom, parmesan)",
    "let warming toasted spices lead",
    "use fresh herbs generously, added at the end",
    "play a sweet-and-sour balance",
    "balance chilli heat against something cooling",
    "work in nutty browned butter or toasted nuts",
    "go garlicky and aromatic",
    "build a smoky-sweet, gently spiced warmth",
    # Regional sub-styles (gentle leanings, never overrides)
    "take a Levantine / Eastern Mediterranean lean",
    "borrow a Japanese-inspired lightness",
    "keep it rustic and Italian-simple",
    "draw on North African warmth (ras el hanout, preserved lemon territory)",
    "use gentle South-East Asian aromatics (lemongrass, lime, ginger)",
]

SWEET_SEEDS = [
    # Texture & technique
    "play a crisp or crunchy element against something soft and creamy",
    "lean on browned butter for a nutty, toffee-ish depth",
    "work in a proper caramel note (caramelised sugar, dulce, burnt butter)",
    "add textural crunch: toasted nuts, praline, crumble or a biscuit layer",
    "contrast a warm component with a cool one (warm sponge, cold cream)",
    # Flavour angles
    "cut the sweetness with acidity from citrus or tart fruit",
    "let warming baking spices lead (cinnamon, cardamom, ginger, nutmeg)",
    "bring in a grown-up bitter note — dark chocolate, coffee or treacle",
    "make fresh, seasonal fruit the star",
    "add a fragrant note: vanilla, almond, rose or orange blossom",
    "pair chocolate with something that cuts it (sea salt, orange, berries)",
    "add a gentle boozy lift (rum, amaretto, whisky)",
]

# Meal types that draw from the sweet pool instead of the savoury default.
_SWEET_MEAL_TYPES = {"Dessert", "Baking"}
# Meal types that get NO creative seed at all.
_NO_SEED_MEAL_TYPES = {"Sauce or dressing"}


def pick_seed_for(meal_type, rng=None):
    """Return one randomly chosen creative seed appropriate to `meal_type`, or
    None when the meal type should get no seed. `rng` is injectable for tests."""
    if meal_type in _NO_SEED_MEAL_TYPES:
        return None
    pool = SWEET_SEEDS if meal_type in _SWEET_MEAL_TYPES else SAVOURY_SEEDS
    return (rng or random).choice(pool)


def pick_seed(rng=None):
    """Backwards-compatible savoury pick, kept so any existing caller (e.g. the
    eval tooling) importing `pick_seed` keeps working with unchanged behaviour."""
    return (rng or random).choice(SAVOURY_SEEDS)
