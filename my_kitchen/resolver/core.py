"""Resolver pure core — DB-free, deterministic, no LLM call.

The cascade is layered and precision-over-recall. The guiding idea: the
*least-stripped* form of the query gets first crack at an exact/alias hit, and we
only remove "removable" words progressively after a miss. That ordering is what
makes every precision trap pass by construction — a multi-word canonical
(Sweet potato, Ground coriander, Fresh thyme, Red onion, Black pepper) exact-hits
before any qualifier could be dropped, so the trap can never collapse to the
wrong entry.

Two normalisation forms, both built with the SAME pipeline for queries, catalogue
names AND alias keys (or exact/alias matches silently miss):

  norm_min   lowercase -> de-accent -> drop digits + punctuation -> drop UNIT and
             CONNECTIVE tokens -> singularise. Keeps prep words, descriptors,
             colours, form/type words. This is the "specific" form.
  norm_core  norm_min with the STRIP set additionally removed (prep / state /
             size / adverbs / 'fresh' / 'sea' / 'extra virgin'). Colour / form /
             type words (sweet, red, ground, dried, smoked, new, spring, …) are
             NEVER in STRIP — they distinguish real catalogue entries.

Cascade for a query:
  1. norm_min in catalogue index            -> exact
  2. norm_min in alias index                -> alias
  3. norm_core in catalogue index           -> exact   (recovered after stripping)
  4. norm_core in alias index               -> alias
  5. token_set_ratio(norm_min, names) >= TH -> fuzzy
  6. otherwise                              -> unmatched

token_set_ratio is chosen over partial_ratio / WRatio: substring scorers would
false-link off-catalogue items (e.g. "lemongrass" -> "lemon"), which the golden
negatives must reject. Catalogue + aliases are INJECTED, so the core runs with no
app/DB context — exactly like the prompt eval.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from rapidfuzz import fuzz, process

# Injected-data type hints (kept DB-free — see module docstring).
Catalogue = Iterable[Tuple[Optional[int], str]]   # (ingredient_id, canonical_name)
Aliases = dict                                     # {alias_text: canonical_name}

METHODS = ("exact", "alias", "fuzzy", "unmatched")

# Fuzzy scorer + threshold (tuned in CP2 against the golden set: negatives set the
# ceiling, real-world misspellings the floor). token_set_ratio only.
FUZZY_SCORER = fuzz.token_set_ratio
FUZZY_THRESHOLD = 90.0

# --- token sets, all matched AFTER lowercase/de-accent/de-digit -------------

# Quantities are stripped as digits; these are the measure/packaging words.
# None is part of any canonical name (checked), so dropping them is safe.
UNITS = {
    "g", "kg", "mg", "gram", "grams", "gramme", "grammes", "kilo", "kilos",
    "kilogram", "kilograms", "ml", "l", "litre", "litres", "liter", "liters",
    "cl", "dl", "tsp", "tsps", "teaspoon", "teaspoons", "tbsp", "tbsps", "tbs",
    "tablespoon", "tablespoons", "dsp", "cup", "cups", "oz", "ounce", "ounces",
    "lb", "lbs", "pound", "pounds", "pint", "pints", "clove", "cloves", "tin",
    "tins", "can", "cans", "jar", "jars", "packet", "packets", "pack", "packs",
    "bag", "bags", "box", "boxes", "block", "blocks", "tub", "tubs", "bottle",
    "bottles", "carton", "cartons", "pinch", "pinches", "handful", "handfuls",
    "bunch", "bunches", "stalk", "stalks", "sprig", "sprigs", "knob", "knobs",
    "dash", "dashes", "splash", "splashes", "glug", "glugs", "drizzle", "squeeze",
    "slice", "slices", "piece", "pieces", "strip", "strips", "head", "heads",
    "stick", "sticks", "x", "cm", "mm", "inch", "inches",
}

# Pure structural glue. "of" appears in "Bicarbonate of soda" but dropping it
# symmetrically (both sides) keeps that entry unique, so this is safe.
CONNECTIVES = {"of", "a", "an", "the", "and", "with", "to", "plus", "or", "in", "into"}

# Removed only in norm_core (the second pass). DELIBERATELY excludes colour /
# form / type words (sweet, red, green, black, white, new, spring, ground, dried,
# smoked, double, single, sun) — those are load-bearing canonical-name parts and
# their precision traps must hold. 'fresh' is here but is safe: a "Fresh thyme" /
# "Fresh rosemary" query exact-hits at norm_min before norm_core ever strips it.
STRIP = {
    # prep verbs / participles
    "chopped", "sliced", "diced", "minced", "crushed", "grated", "peeled",
    "deseeded", "seeded", "trimmed", "halved", "quartered", "cubed", "shredded",
    "torn", "cut", "mashed", "cracked", "beaten", "softened", "melted", "toasted",
    "cooked", "boiled", "steamed", "roasted", "grilled", "rinsed", "drained",
    "washed", "frozen", "fresh", "ripe", "raw",
    # adverbs
    "finely", "roughly", "thinly", "thickly", "coarsely", "freshly", "lightly", "well",
    # size / generic qualifier (never part of a canonical name)
    "baby", "large", "small", "big", "medium", "extra", "virgin", "sea", "whole",
    "mini", "jumbo",
    # idiom tail ("to taste")
    "taste",
}

# Words that look plural but must not be de-pluralised. The endswith us/ss/is
# guard handles asparagus / couscous / hummus generically; this is a backstop.
NO_SINGULAR = {
    "asparagus", "couscous", "hummus", "molasses", "watercress", "swiss",
    "gnocchi", "biscotti", "focaccia",
}


def _deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _singular(w: str) -> str:
    if w in NO_SINGULAR or len(w) <= 3:
        return w
    if w.endswith("ss") or w.endswith("us") or w.endswith("is"):
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("oes"):
        return w[:-2]
    if w.endswith("ches") or w.endswith("shes") or w.endswith("xes") or w.endswith("zes"):
        return w[:-2]
    if w.endswith("s"):
        return w[:-1]
    return w


def base_tokens(text: str) -> List[str]:
    """norm_min token list: lowercase, de-accent, drop digits+punctuation, drop
    UNIT and CONNECTIVE tokens, singularise. Order preserved."""
    s = re.sub(r"[^a-z\s]", " ", _deaccent(text.lower()))
    out = []
    for tok in s.split():
        if tok in UNITS or tok in CONNECTIVES:
            continue
        out.append(_singular(tok))
    return out


def norm_min(text: str) -> str:
    return " ".join(base_tokens(text))


def norm_core(text: str) -> str:
    return " ".join(t for t in base_tokens(text) if t not in STRIP)


# --- index -----------------------------------------------------------------

@dataclass
class Index:
    """Pre-normalised catalogue + aliases, built once and reused across queries.
    3b can build this on the live catalogue and keep it; the eval builds it on an
    injected fixture."""
    cat: Dict[str, Tuple[Optional[int], str]]      # norm_min(name) -> (id, name)
    alias: Dict[str, Tuple[Optional[int], str]]    # norm_min(alias) -> (id, name)
    fuzzy_choices: List[str]                        # norm_min names, aligned to fuzzy_targets
    fuzzy_targets: List[Tuple[Optional[int], str]]


def build_index(catalogue: Catalogue, aliases: Aliases) -> Index:
    cat: Dict[str, Tuple[Optional[int], str]] = {}
    for ing_id, name in catalogue:
        key = norm_min(name)
        if key and key not in cat:
            cat[key] = (ing_id, name)
    alias: Dict[str, Tuple[Optional[int], str]] = {}
    for raw_alias, canonical in (aliases or {}).items():
        target = cat.get(norm_min(canonical))
        if target is None:
            continue  # alias points at a name not in this catalogue — skip
        key = norm_min(raw_alias)
        if key and key not in cat:        # never let an alias shadow a real name
            alias[key] = target
    choices = list(cat.keys())
    targets = [cat[k] for k in choices]
    return Index(cat=cat, alias=alias, fuzzy_choices=choices, fuzzy_targets=targets)


@dataclass(frozen=True)
class ResolveResult:
    """Outcome of resolving one free-text ingredient.

    ingredient_id : catalogue id, or None when unmatched / name-only fixture.
    matched_name  : canonical name matched, or None. The golden set asserts on
                    THIS (reseed-stable), never the id.
    score         : 0–100. 100 exact/alias; rapidfuzz score for fuzzy; 0 unmatched.
    method        : one of METHODS.
    """
    ingredient_id: Optional[int]
    matched_name: Optional[str]
    score: float
    method: str


UNMATCHED = ResolveResult(ingredient_id=None, matched_name=None, score=0.0, method="unmatched")


def resolve_with_index(free_text: str, index: Index,
                       threshold: float = FUZZY_THRESHOLD) -> ResolveResult:
    """Resolve against a pre-built Index (the efficient path)."""
    bt = base_tokens(free_text)
    q_min = " ".join(bt)
    if not q_min:
        return UNMATCHED

    hit = index.cat.get(q_min)
    if hit is not None:
        return ResolveResult(hit[0], hit[1], 100.0, "exact")
    hit = index.alias.get(q_min)
    if hit is not None:
        return ResolveResult(hit[0], hit[1], 100.0, "alias")

    q_core = " ".join(t for t in bt if t not in STRIP)
    if q_core and q_core != q_min:
        hit = index.cat.get(q_core)
        if hit is not None:
            return ResolveResult(hit[0], hit[1], 100.0, "exact")
        hit = index.alias.get(q_core)
        if hit is not None:
            return ResolveResult(hit[0], hit[1], 100.0, "alias")

    if index.fuzzy_choices:
        best = process.extractOne(q_min, index.fuzzy_choices, scorer=FUZZY_SCORER)
        if best is not None:
            choice, score, idx = best
            if score >= threshold:
                ing_id, name = index.fuzzy_targets[idx]
                return ResolveResult(ing_id, name, float(score), "fuzzy")
    return UNMATCHED


def resolve(free_text: str, catalogue: Catalogue, aliases: Aliases,
            threshold: float = FUZZY_THRESHOLD) -> ResolveResult:
    """Convenience entry point matching the brief's surface: build an index from
    the injected catalogue + aliases and resolve one string. 3b that resolves
    many strings should build_index() once and call resolve_with_index()."""
    return resolve_with_index(free_text, build_index(catalogue, aliases), threshold)


def best_fuzzy(free_text: str, index: Index):
    """(choice_name, score) for the top fuzzy candidate regardless of threshold —
    used by the eval to show why a negative/miss landed where it did."""
    q_min = norm_min(free_text)
    if not q_min or not index.fuzzy_choices:
        return (None, 0.0)
    best = process.extractOne(q_min, index.fuzzy_choices, scorer=FUZZY_SCORER)
    if best is None:
        return (None, 0.0)
    choice, score, idx = best
    return (index.fuzzy_targets[idx][1], float(score))
