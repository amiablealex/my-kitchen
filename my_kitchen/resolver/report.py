"""Match-rate report over REAL recipe_ingredients rows (Phase 3b).

3b's validation in place of UI: extends the thin golden-set evidence (28 cases)
to real Gemini output. Reads the structured rows the generation path wrote and
reports:

- the overall catalogue match rate, broken out into two populations —
  REQUIRED (``to_buy=False``, the headline metric) and EXTRAS (``to_buy=True``,
  not-in-stock suggestions, informational). ``to_buy`` means not-in-stock, not
  off-catalogue, so extras are resolved exactly like required items and many
  still link; they're reported separately so they don't skew the headline.
- the per-method breakdown (exact / alias / fuzzy / unmatched), recovered by
  re-resolving each ``raw_text`` against the LIVE catalogue, since the method is
  not stored on the row. A drift counter flags any row whose re-resolution
  disagrees with its stored link (i.e. the catalogue changed since generation) —
  expected to be 0 in 3b.
- the DISTINCT unmatched ``raw_text`` values, split: the ``to_buy=False`` list is
  the PRIMARY signal (these block future suggestability — candidates for new
  catalogue entries / aliases); the ``to_buy=True`` list is SECONDARY.

Match rate uses the STORED ``ingredient_id`` (what's actually linked in the DB,
which is what the suggestions query will see); method is recovered separately.
"""
from collections import Counter

from .core import build_index, resolve_with_index
from .db import load_catalogue
from .aliases import ALIASES


def _distinct_unmatched(rows):
    """Distinct unmatched raw_text (stored link is null), case-insensitive,
    preserving the original casing of the first occurrence, sorted for stable
    reading."""
    seen, out = set(), []
    for r in rows:
        if r.ingredient_id is None:
            text = (r.raw_text or "").strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                out.append(text)
    return sorted(out, key=str.lower)


def run_resolve_report(echo=print):
    """Print the report. `echo` is click.echo under the CLI, print() in tests."""
    from ..models import RecipeIngredient

    rows = RecipeIngredient.query.all()
    if not rows:
        echo("No recipe_ingredients rows yet — run a generation first, then "
             "re-run this report.")
        return

    # Index built ONCE (load_catalogue() hits the DB) and reused for every row.
    index = build_index(load_catalogue(), ALIASES)

    required = [r for r in rows if not r.to_buy]
    extras = [r for r in rows if r.to_buy]

    def rate(subset):
        total = len(subset)
        matched = sum(1 for r in subset if r.ingredient_id is not None)
        pct = (matched / total * 100) if total else 0.0
        return matched, total, pct

    # Per-method breakdown + drift check, via re-resolution against the live
    # catalogue (method isn't stored on the row). Also capture the FUZZY links so
    # they can be eyeballed — fuzzy is the only soft path, so a false link can only
    # hide here. token_set_ratio scores a superset ("chicken breast fillets" ->
    # "Chicken breast") at 100, which is benign; sub-100 fuzzy is where to look.
    method_counts = Counter()
    drift = 0
    fuzzy_links = {}  # raw_text.lower() -> (raw_text, matched_name, score)
    for r in rows:
        res = resolve_with_index(r.raw_text or "", index)
        method_counts[res.method] += 1
        if (res.ingredient_id is not None) != (r.ingredient_id is not None):
            drift += 1
        if res.method == "fuzzy":
            key = (r.raw_text or "").strip().lower()
            fuzzy_links.setdefault(key, (r.raw_text.strip(), res.matched_name, res.score))

    n_recipes = len({r.recipe_id for r in rows})
    line = "=" * 72

    echo(line)
    echo("Resolver match-rate report — real recipe_ingredients")
    echo(f"{len(rows)} ingredient rows across {n_recipes} recipes")
    echo(line)

    m, t, p = rate(required)
    echo("")
    echo("REQUIRED (to_buy=False) — headline metric")
    echo(f"  match rate : {m}/{t} = {p:.1f}%" if t else "  (none yet)")

    m, t, p = rate(extras)
    echo("")
    echo("EXTRAS (to_buy=True, not-in-stock suggestions) — informational")
    echo(f"  match rate : {m}/{t} = {p:.1f}%" if t else "  (none yet)")

    m, t, p = rate(rows)
    echo("")
    echo(f"OVERALL    : {m}/{t} = {p:.1f}%")

    echo("")
    echo("per-method (re-resolved against the live catalogue):")
    for method in ("exact", "alias", "fuzzy", "unmatched"):
        echo(f"  {method:<10}: {method_counts.get(method, 0)}")
    if drift:
        echo(f"  NOTE: {drift} row(s) re-resolve differently from their stored "
             "link (catalogue changed since generation).")

    # FUZZY links, lowest score first (the riskiest to review). Sub-100 scores are
    # the ones worth a human glance; 100 = a benign descriptor superset.
    if fuzzy_links:
        echo("")
        echo(f"FUZZY links (review — soft matches): {len(fuzzy_links)} distinct")
        for text, name, score in sorted(fuzzy_links.values(), key=lambda x: x[2]):
            echo(f"    {score:5.1f}  {text}  ->  {name}")

    primary = _distinct_unmatched(required)
    echo("")
    echo(f"UNMATCHED — required (to_buy=False): {len(primary)} distinct "
         "<-- catalogue-gap / alias candidates")
    for text in primary:
        echo(f"    {text}")

    secondary = _distinct_unmatched(extras)
    echo("")
    echo(f"UNMATCHED — extras (to_buy=True): {len(secondary)} distinct (secondary)")
    for text in secondary:
        echo(f"    {text}")

    echo(line)
