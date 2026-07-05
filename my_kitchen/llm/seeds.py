"""Creative seeds — small curated lists of flavour angles, techniques and
regional sub-styles used purely to nudge variety across generations.

One seed is (sometimes) picked per generation and offered to the FIRST recipe
only, as an *optional bias*: the model is told it may ignore it, and the chosen
cuisine always takes priority. Seeds exist for randomness, not to dictate the
dish. The chosen seed (or None) is stored on Generation.creative_seed.

Meal-type + cuisine aware:
  * SAVOURY_SEEDS          — cuisine-neutral technique/flavour angles. Safe on
                             ANY savoury brief, including a specific cuisine.
  * SAVOURY_REGIONAL_SEEDS — mini-cuisine leanings (Levantine, Japanese…). Only
                             eligible when NO specific cuisine is chosen, or
                             they'd pull against the user's pick.
  * SWEET_SEEDS            — for Dessert and Baking, where a savoury angle is
                             actively wrong.
  * No seed                — for "Sauce or dressing" (a random angle is noise on
                             something small and focused), AND ~half the time on
                             an open-cuisine savoury brief, to leave the model a
                             free hand.

SAVOURY_SEEDS + SAVOURY_REGIONAL_SEEDS is the original single list, in the
original order, so the legacy pick_seed() below stays byte-identical.
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
]

SAVOURY_REGIONAL_SEEDS = [
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

# Meal types that draw from the sweet pool instead of a savoury one.
_SWEET_MEAL_TYPES = {"Dessert", "Baking"}
# Meal types that get NO creative seed at all.
_NO_SEED_MEAL_TYPES = {"Sauce or dressing"}
# On an open-cuisine savoury brief, probability we pass a seed at all; the rest
# of the time we pass None and let the model design with a free hand.
OPEN_CUISINE_SEED_PROB = 0.5


def pick_seed_for(meal_type, cuisine, rng=None):
    """Return one creative seed appropriate to (meal_type, cuisine), or None when
    the brief should get none. `rng` is injectable for tests/eval determinism.

    - Sauce or dressing            -> None.
    - Dessert / Baking             -> a sweet seed.
    - Savoury, specific cuisine    -> a cuisine-neutral savoury seed (never a
                                      regional one — it'd fight the chosen cuisine).
    - Savoury, open cuisine        -> ~half the time a seed (regional included),
      (Any / Surprise me / None)      otherwise None (free hand).
    """
    rng = rng or random
    if meal_type in _NO_SEED_MEAL_TYPES:
        return None
    if meal_type in _SWEET_MEAL_TYPES:
        return rng.choice(SWEET_SEEDS)

    open_cuisine = cuisine is None or cuisine.strip().lower() == "surprise me"
    if open_cuisine:
        if rng.random() < OPEN_CUISINE_SEED_PROB:
            return rng.choice(SAVOURY_SEEDS + SAVOURY_REGIONAL_SEEDS)
        return None
    return rng.choice(SAVOURY_SEEDS)


def pick_seed(rng=None):
    """Legacy savoury pick — the full original pool (core + regional) in the
    original order, kept byte-identical for any caller (e.g. eval tooling) that
    imports it. Drop it if a grep shows nothing uses it."""
    return (rng or random).choice(SAVOURY_SEEDS + SAVOURY_REGIONAL_SEEDS)
