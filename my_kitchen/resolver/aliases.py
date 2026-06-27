"""Curated alias map — ``alias text -> canonical catalogue name``.

A plain Python constant (NOT a DB table — promotion to DB-backed is deferred
past 3a). Built from ``3a-resolver-inputs.md`` §2. Keys and values are RAW /
human-readable here; the resolver normalises both on load (CP2) with the same
pipeline as the query, or alias/exact matches silently miss.

Three deliberate corrections to the inputs package (logged for the summary):
  1. The package line ``aubergine eggplant, capsicum -> Bell pepper`` is a doc
     slip — "aubergine"/"eggplant" already map to Aubergine above. Only
     ``capsicum -> Bell pepper`` is kept.
  2. ``cod`` is dropped from the white-fish collapse: the catalogue has its own
     ``Cod fillet`` entry, so aliasing cod -> White fish fillet would be a wrong
     link (the danger-zone the package warns about). haddock / pollock / white
     fish have no own entry and stay collapsed to White fish fillet.
  3. ``tuna`` aliases added (the package omitted them) so the golden trap
     "1 tin tuna" -> Tuna (tinned) resolves; the bare canonical carries a
     parenthetical the free-text never includes.
"""

ALIASES = {
    # --- synonyms / regional ---
    "tenderstem broccoli": "Broccoli",
    "sprouting broccoli": "Broccoli",
    "broccolini": "Broccoli",
    "scallion": "Spring onion",
    "green onion": "Spring onion",
    "eggplant": "Aubergine",
    "zucchini": "Courgette",
    "cilantro": "Coriander",
    "arugula": "Rocket",
    "garbanzo": "Chickpeas",
    "garbanzo beans": "Chickpeas",
    "shrimp": "Prawns",
    "baking soda": "Bicarbonate of soda",
    "capsicum": "Bell pepper",

    # --- specific -> generic (collapse to the catalogue's granularity) ---
    "fusilli": "Pasta",
    "penne": "Pasta",
    "spaghetti": "Pasta",
    "macaroni": "Pasta",
    "rigatoni": "Pasta",
    "tagliatelle": "Pasta",
    "linguine": "Pasta",
    "farfalle": "Pasta",
    "chestnut mushrooms": "Mushrooms",
    "button mushrooms": "Mushrooms",
    "white mushrooms": "Mushrooms",
    "portobello": "Mushrooms",
    "red pepper": "Bell pepper",
    "green pepper": "Bell pepper",
    "yellow pepper": "Bell pepper",
    "red bell pepper": "Bell pepper",
    "chopped tomatoes": "Tinned tomatoes",
    "plum tomatoes": "Tinned tomatoes",
    "tinned chopped tomatoes": "Tinned tomatoes",
    "basmati": "Rice",
    "basmati rice": "Rice",
    "jasmine rice": "Rice",
    "long-grain rice": "Rice",
    "haddock": "White fish fillet",
    "pollock": "White fish fillet",
    "white fish": "White fish fillet",

    # --- added in 3a (golden-set gap, see module docstring) ---
    "tuna": "Tuna (tinned)",
    "tinned tuna": "Tuna (tinned)",
    "tin of tuna": "Tuna (tinned)",

    # --- added in 3a CP3 (frequent household terms, from examples.md) ---
    # "brown onion" / "white onion" are just the standard onion; make them a
    # deterministic alias rather than leaning on a fuzzy match.
    "brown onion": "Onion",
    "white onion": "Onion",
}
