"""Resolver pure core — DB-free.

The cascade (implemented in CP2) is layered, precision-over-recall:

  1. normalise the query (lowercase, strip punctuation/quantities/units, strip a
     CONSERVATIVE prep/state qualifier list, singularise) and exact-match against
     normalised catalogue names AND aliases;
  2. if that misses, progressively drop leading *descriptor* words
     (fresh/baby/large/small/…) and retry exact/alias — so a multi-word canonical
     (Fresh thyme, Sweet potato, Ground coriander, Red onion) always wins an exact
     hit BEFORE any descriptor is removed (the precision traps pass by construction);
  3. else ``rapidfuzz.token_set_ratio`` above a tuned threshold (NOT partial_ratio
     / WRatio — substring scorers would false-link e.g. "lemongrass" -> "lemon");
  4. else UNMATCHED (null id) — fine for to_buy / off-catalogue / staple items.

Catalogue + aliases are INJECTED. The catalogue is an iterable of
``(ingredient_id, canonical_name)``; ``ingredient_id`` may be ``None`` (the eval
fixture is name-only). Aliases is a ``{alias_text: canonical_name}`` dict. Both
are normalised with the SAME pipeline as the query, or exact/alias matches miss.

CP1 status: ResolveResult + UNMATCHED are final; ``resolve`` is a stub returning
UNMATCHED so the package imports and the harness can be wired. The matching logic
is CP2.
"""
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

# Injected-data type hints (kept DB-free — see module docstring).
Catalogue = Iterable[Tuple[Optional[int], str]]   # (ingredient_id, canonical_name)
Aliases = dict                                     # {alias_text: canonical_name}

# The four resolution methods, in cascade order. 'unmatched' is the safe default.
METHODS = ("exact", "alias", "fuzzy", "unmatched")


@dataclass(frozen=True)
class ResolveResult:
    """The outcome of resolving one free-text ingredient.

    ingredient_id : catalogue id, or None when unmatched / when the injected
                    catalogue is name-only (the eval fixture).
    matched_name  : the canonical catalogue name matched, or None when unmatched.
                    The golden set asserts on THIS (reseed-stable), never the id.
    score         : 0–100. 100 for exact/alias; the rapidfuzz score for fuzzy; 0
                    for unmatched.
    method        : one of METHODS.
    """
    ingredient_id: Optional[int]
    matched_name: Optional[str]
    score: float
    method: str


UNMATCHED = ResolveResult(ingredient_id=None, matched_name=None, score=0.0, method="unmatched")


def resolve(free_text: str, catalogue: Catalogue, aliases: Aliases) -> ResolveResult:
    """Resolve a raw free-text ingredient string to a catalogue entry.

    CP1 skeleton — always returns UNMATCHED. CP2 implements the layered cascade
    described in the module docstring.
    """
    # CP2: normalise -> exact/alias -> descriptor-drop fallback -> fuzzy -> unmatched.
    return UNMATCHED
