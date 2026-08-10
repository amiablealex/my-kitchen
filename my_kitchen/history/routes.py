from flask import Blueprint, render_template, request
from flask_login import current_user
from datetime import datetime

from ..extensions import db
from ..models import Generation, Recipe, RecipeComment, User

history_bp = Blueprint("history", __name__, url_prefix="/history")

# The Recipes list filters client-side across four facets plus free text. Each
# row carries its facet values as pipe-delimited, pipe-bounded, lowercased
# strings, so a substring test for "|italian|" is an exact whole-value match and
# can't half-match ("indian" never matches "|west indian|"). Multi-valued by
# design: an unchosen AI row links to two recipes whose tags may differ, so the
# row matches if EITHER does.

SOURCE_LABELS = {"ai": "AI generated", "user": "Created by hand", "imported": "Imported"}


def _row_recipes(row):
    """The recipes a row actually links to — its filterable surface. A chosen
    generation shows only the chosen recipe; an unchosen one shows both; a
    failed generation shows none."""
    if row["kind"] == "user":
        return [row["recipe"]]
    if row["status"] == "chosen":
        return [row["chosen"]]
    if row["status"] == "unchosen":
        return list(row["recipes"])
    return []


def _row_cooks(row):
    """Cook names for a row. Recipes carry created_by_user_id (copied forward
    from the generation for AI), but pre-keystone AI recipes have it NULL — so
    fall back to the generation's cook, which the old server-side filter used."""
    names = {r.author.name for r in _row_recipes(row) if r.author}
    if row["kind"] == "generation" and row["gen"].created_by:
        names.add(row["gen"].created_by.name)
    return names


def _facet_field(values):
    """Pipe-bounded lowercased field, or "" when there's nothing to match on."""
    vals = sorted({(v or "").strip().lower() for v in values if v and str(v).strip()})
    return "|" + "|".join(vals) + "|" if vals else ""


def _recipe_cook(recipe):
    """The one cook name for a recipe: its author, falling back to the
    generation's cook (pre-keystone AI recipes have created_by_user_id NULL)."""
    if recipe.author:
        return recipe.author.name
    if recipe.generation and recipe.generation.created_by:
        return recipe.generation.created_by.name
    return None


class _FacetOptions:
    """Collects the facet values that actually occur, so the filter never offers
    a value matching nothing. Shared by both list pages so their suggestion
    lists can't drift apart."""

    FACETS = ("cuisine", "meal", "cook", "source")

    def __init__(self):
        self._seen = {f: {} for f in self.FACETS}

    def note(self, facet, value, label=None):
        if value and str(value).strip():
            self._seen[facet].setdefault(str(value).strip().lower(), label or value)

    def as_list(self):
        out = []
        for facet in self.FACETS:
            for value, label in sorted(self._seen[facet].items(),
                                       key=lambda kv: kv[1].lower()):
                out.append({"facet": facet, "value": value, "label": label})
        return out


def _note_recipe(opts, recipe, cooks):
    """Record one recipe's facet values against the collector."""
    opts.note("cuisine", recipe.cuisine)
    opts.note("meal", recipe.meal_type)
    opts.note("source", recipe.source, SOURCE_LABELS.get(recipe.source, recipe.source))
    for name in cooks:
        opts.note("cook", name)


def _attach_facets(rows):
    """Decorate each History row with its facet fields and return the options.
    Walks the rows already in memory — no extra queries."""
    opts = _FacetOptions()
    for row in rows:
        recs = _row_recipes(row)
        cooks = _row_cooks(row)
        row["f_cuisine"] = _facet_field(r.cuisine for r in recs)
        row["f_meal"] = _facet_field(r.meal_type for r in recs)
        row["f_cook"] = _facet_field(cooks)
        row["f_source"] = _facet_field(r.source for r in recs)
        row["f_title"] = " ".join((r.title or "").lower() for r in recs)
        for r in recs:
            _note_recipe(opts, r, cooks)
    return opts.as_list()


def _recipe_facets(recipes):
    """Facet fields for a flat list of recipes (Favourites, where each row is
    one recipe). Returns (fields_by_recipe_id, options)."""
    opts = _FacetOptions()
    fields = {}
    for r in recipes:
        cook = _recipe_cook(r)
        cooks = [cook] if cook else []
        fields[r.id] = {
            "title": (r.title or "").lower(),
            "cuisine": _facet_field([r.cuisine]),
            "meal": _facet_field([r.meal_type]),
            "cook": _facet_field(cooks),
            "source": _facet_field([r.source]),
        }
        _note_recipe(opts, r, cooks)
    return fields, opts.as_list()


@history_bp.route("/")
def index():
    """A merged, newest-first list of the recipe bank: AI generations (chosen /
    unchosen / error, as before) plus hand-created (source='user') recipes, which
    have no generation."""

    # Filtering moved fully client-side in Phase 21 (see recipe_facets.js): the
    # whole bank is in the DOM anyway, and instant filtering beats a reload at
    # the hob. The old ?user= / ?source= params are gone — source had already
    # been superseded by the AI/hand grouping below.

    generations = Generation.query.all()
    user_recipes = Recipe.query.filter(Recipe.source == "user").all()

    rows = []
    for gen in generations:
        if gen.recipes:
            chosen = next((r for r in gen.recipes if r.was_chosen), None)
            status = "chosen" if chosen else "unchosen"
        else:
            chosen = None
            status = "error"
        rows.append({"kind": "generation", "sort_at": gen.created_at,
                     "gen": gen, "status": status, "chosen": chosen,
                     "recipes": gen.recipes})
    for r in user_recipes:
        rows.append({"kind": "user", "sort_at": r.created_at, "recipe": r})

    rows.sort(key=lambda row: row["sort_at"] or datetime.min, reverse=True)

    facet_options = _attach_facets(rows)
    fav_ids = {r.id for r in current_user.favourite_recipes}
    noted_ids = {rid for (rid,) in db.session.query(RecipeComment.recipe_id).distinct()}
    return render_template("history/index.html", rows=rows,
                           facet_options=facet_options,
                           fav_ids=fav_ids, noted_ids=noted_ids)


@history_bp.route("/favourites")
def favourites():
    """The logged-in user's favourites, newest-first (spec section 6, corrected
    to be per-user)."""
    recipes = (Recipe.query
               .filter(Recipe.favourited_by.any(id=current_user.id))
               .order_by(Recipe.created_at.desc()).all())
    noted_ids = {rid for (rid,) in db.session.query(RecipeComment.recipe_id).distinct()}
    facets, facet_options = _recipe_facets(recipes)
    return render_template("history/favourites.html", recipes=recipes,
                           noted_ids=noted_ids, facets=facets,
                           facet_options=facet_options)
