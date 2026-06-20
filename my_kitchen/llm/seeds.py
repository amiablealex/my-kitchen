"""Creative seeds — a small curated list of flavour angles, techniques and
regional sub-styles used purely to nudge variety across generations.

One seed is picked at random per generation and offered to the FIRST recipe
only, as an *optional bias*: the model is explicitly told it may ignore it, and
the user-chosen cuisine always takes priority. The seeds exist for randomness,
not to dictate the dish. The chosen seed is stored on Generation.creative_seed
for reproducibility/debugging.

Hardcoded-but-easily-edited for now; the list gets expanded in Pass 4b.
"""
import random

CREATIVE_SEEDS = [
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


def pick_seed(rng=None):
    """Return one randomly chosen creative seed. `rng` is injectable for tests."""
    return (rng or random).choice(CREATIVE_SEEDS)
