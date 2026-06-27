"""Golden set for the resolver eval (``flask resolve-eval``).

Mirrors ``golden_briefs.py``: a curated, DB-free fixture that grounds tuning in
evidence, not eyeballing. From ``3a-resolver-inputs.md`` §3. Every expectation is
keyed on the canonical NAME (reseed-stable), never the id.

  POSITIVES  free_text -> expected canonical name (should match)
  NEGATIVES  free_text -> None (deliberately off-catalogue; must stay unmatched)
  TRAPS      free_text -> (must_be, [must_not_be, …]) — the precision cases that
             make or break tuning; a wrong link here is a HARD fail.

The fixture catalogue is the production seed catalogue (``seed_catalogue.py``)
with synthetic sequential ids — single source of truth, no DB.
"""
from ..seed_catalogue import CATALOGUE_NAMES


def fixture_catalogue():
    """[(id, name), …] for the DB-free eval. Ids are synthetic; the eval asserts
    on names."""
    return [(i + 1, name) for i, name in enumerate(CATALOGUE_NAMES)]


# free_text -> expected canonical name
POSITIVES = [
    ("2 chicken breasts, diced", "Chicken breast"),
    ("tenderstem broccoli", "Broccoli"),
    ("fresh coriander, roughly chopped", "Coriander"),
    ("1 large aubergine", "Aubergine"),
    ("baby spinach", "Spinach"),
    ("chestnut mushrooms, sliced", "Mushrooms"),
    ("300g fusilli", "Pasta"),
    ("400g tin of chopped tomatoes", "Tinned tomatoes"),
    ("spring onions, finely sliced", "Spring onion"),
    ("2 cloves of garlic", "Garlic"),
    ("1 red bell pepper", "Bell pepper"),
    ("1 tin chickpeas, drained", "Chickpeas"),
    ("extra virgin olive oil", "Olive oil"),
    ("1 tsp ground cumin", "Ground cumin"),
    ("200ml coconut milk", "Coconut milk"),
    ("sea salt, to taste", "Salt"),
]

# free_text -> None (must return unmatched)
NEGATIVES = [
    ("pinch of saffron threads", None),
    ("1 tbsp pomegranate molasses", None),
    ("2 tbsp gochujang", None),
    ("1 stalk lemongrass, bruised", None),
    ("1 tbsp white miso paste", None),
    ("handful of curry leaves", None),
]

# free_text -> (must_be, [must_not_be, …])
TRAPS = [
    ("1 sweet potato, cubed", "Sweet potato", ["Potatoes"]),
    ("1 tsp black pepper", "Black pepper", ["Bell pepper"]),
    ("1 tsp ground coriander", "Ground coriander", ["Coriander"]),
    ("2 tsp fresh thyme", "Fresh thyme", ["Dried thyme"]),
    ("1 red onion, sliced", "Red onion", ["Onion"]),
    ("1 tin tuna", "Tuna (tinned)",
     ["Salmon fillet", "White fish fillet", "Seabass fillet", "Cod fillet"]),
]
