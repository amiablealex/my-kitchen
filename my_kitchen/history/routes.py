from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user
from datetime import datetime

from ..extensions import db
from ..models import Generation, Recipe, RecipeComment, User, utcnow

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


def _lineage_context(generations):
    """What hides a generation row because something newer stands in for it
    (Phase 26), plus each recipe's version number for the "v3" badge.

    - A regenerate round replaces its parent while the parent has no chosen
      recipe: a chain of "Neither — try again" shows as ONE row, the latest.
    - A finished refine replaces the generation its source recipe came from;
      the lineage is represented by its newest version's row.
    Error rounds and refines replace nothing."""
    done = [g for g in generations if (g.status or "done") == "done"]
    regen_parents = {g.parent_generation_id for g in generations
                     if g.kind == "regenerate" and g.status != "error"}
    refined_sources = {g.source_recipe_id for g in done if g.kind == "refine"}
    by_recipe_gen = {g.id: g for g in generations}

    versions = {}

    def version(recipe, depth=0):
        if recipe.id in versions:
            return versions[recipe.id]
        gen = by_recipe_gen.get(recipe.generation_id)
        n = 1
        if gen is not None and gen.kind == "refine" and gen.source_recipe is not None and depth < 50:
            n = version(gen.source_recipe, depth + 1) + 1
        versions[recipe.id] = n
        return n

    for g in done:
        for r in g.recipes:
            version(r)
    return {"regen_parents": regen_parents, "refined_sources": refined_sources,
            "versions": versions}


def _generation_row(gen, ctx=None):
    """The History row for one generation, or None when archived away.

    Archive (Phase 24) is recipe-level, so a row's visibility follows the
    recipes it shows: a chosen row disappears with its chosen recipe (the
    unchosen sibling never resurfaces as an "unchosen" row); an unchosen row
    shows whichever of its two recipes are still live and disappears when
    neither is. A failed generation has no recipes, so it carries its own
    archived_at."""
    if ctx is not None:
        if any(r.id in ctx["refined_sources"] for r in gen.recipes):
            return None
        if gen.id in ctx["regen_parents"] and not any(r.was_chosen for r in gen.recipes):
            return None
    if not gen.recipes:
        # A job still in flight isn't a row yet; it isn't a failure either.
        if gen.archived_at is not None or gen.status == "running":
            return None
        return {"kind": "generation", "sort_at": gen.created_at, "gen": gen,
                "status": "error", "chosen": None, "recipes": []}
    chosen = next((r for r in gen.recipes if r.was_chosen), None)
    if chosen is not None:
        if chosen.is_archived:
            return None
        return {"kind": "generation", "sort_at": gen.created_at, "gen": gen,
                "status": "chosen", "chosen": chosen, "recipes": gen.recipes}
    live = [r for r in gen.recipes if not r.is_archived]
    if not live:
        return None
    return {"kind": "generation", "sort_at": gen.created_at, "gen": gen,
            "status": "unchosen", "chosen": None, "recipes": live}


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
    user_recipes = Recipe.query.filter(Recipe.source == "user", Recipe.live()).all()
    ctx = _lineage_context(generations)

    rows = []
    for gen in generations:
        row = _generation_row(gen, ctx)
        if row is not None:
            rows.append(row)
    for r in user_recipes:
        rows.append({"kind": "user", "sort_at": r.created_at, "recipe": r})

    rows.sort(key=lambda row: row["sort_at"] or datetime.min, reverse=True)

    facet_options = _attach_facets(rows)
    fav_ids = {r.id for r in current_user.favourite_recipes}
    noted_ids = {rid for (rid,) in db.session.query(RecipeComment.recipe_id).distinct()}
    return render_template("history/index.html", rows=rows,
                           versions=ctx["versions"],
                           facet_options=facet_options,
                           fav_ids=fav_ids, noted_ids=noted_ids)


@history_bp.route("/favourites")
def favourites():
    """The logged-in user's favourites, newest-first (spec section 6, corrected
    to be per-user)."""
    recipes = (Recipe.query
               .filter(Recipe.favourited_by.any(id=current_user.id), Recipe.live())
               .order_by(Recipe.created_at.desc()).all())
    noted_ids = {rid for (rid,) in db.session.query(RecipeComment.recipe_id).distinct()}
    facets, facet_options = _recipe_facets(recipes)
    return render_template("history/favourites.html", recipes=recipes,
                           noted_ids=noted_ids, facets=facets,
                           facet_options=facet_options)


# --- Archive (Phase 24) -----------------------------------------------------
# Household-wide soft delete. A History row archives the recipes it shows (or,
# for a failed generation, the generation itself); undo restores exactly that
# set, so the JSON handshake returns what was touched. JSON rather than an HTML
# fragment: the client re-inserts the row element it already holds, so no
# url_for-built markup has to travel back.


def _archive(recipes, gen=None):
    now = utcnow()
    for r in recipes:
        r.archived_at = now
        r.archived_by_user_id = current_user.id
    if gen is not None:
        gen.archived_at = now


def _archive_one(item, ctx):
    """Archive what one History row shows. item is {"generation_id": n} or
    {"recipe_id": n}. Returns (recipe_ids, generation_id_or_None) touched."""
    if item.get("generation_id") is not None:
        gen = db.session.get(Generation, int(item["generation_id"]))
        if gen is None:
            return [], None
        row = _generation_row(gen, ctx())
        if row is None:
            return [], None  # already archived — nothing to do
        if row["status"] == "error":
            _archive([], gen)
            return [], gen.id
        # A picked pair archives the pick; an unpicked pair archives both.
        recs = [row["chosen"]] if row["status"] == "chosen" else row["recipes"]
        _archive(recs)
        return [r.id for r in recs], None
    if item.get("recipe_id") is not None:
        recipe = db.session.get(Recipe, int(item["recipe_id"]))
        if recipe is None or recipe.is_archived:
            return [], None
        _archive([recipe])
        return [recipe.id], None
    return [], None


@history_bp.route("/row/archive", methods=["POST"])
def row_archive():
    """Archive one row ({"generation_id"} or {"recipe_id"}) or several
    ({"rows": [...]}, from swipe-to-archive's select mode, 0.30.1). Returns
    exactly what was touched, which /row/restore takes back as Undo."""
    data = request.get_json(silent=True) or {}
    items = data.get("rows") if isinstance(data.get("rows"), list) else [data]
    if not items or not all(isinstance(i, dict) and (i.get("generation_id") is not None
                                                     or i.get("recipe_id") is not None)
                            for i in items):
        abort(400)
    cache = {}
    def ctx():
        if "ctx" not in cache:
            cache["ctx"] = _lineage_context(Generation.query.all())
        return cache["ctx"]
    touched = {"recipe_ids": [], "generation_ids": []}
    for item in items:
        rids, gid = _archive_one(item, ctx)
        touched["recipe_ids"] += rids
        if gid is not None:
            touched["generation_ids"].append(gid)
    db.session.commit()
    return jsonify(touched)


@history_bp.route("/row/restore", methods=["POST"])
def row_restore():
    """Undo for row_archive: restores exactly the set it reported."""
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in (data.get("recipe_ids") or [])]
    for r in Recipe.query.filter(Recipe.id.in_(ids)).all() if ids else []:
        r.archived_at = None
        r.archived_by_user_id = None
    gids = [int(g) for g in (data.get("generation_ids") or [])]
    if data.get("generation_id") is not None:          # pre-0.30.1 shape
        gids.append(int(data["generation_id"]))
    for gen in Generation.query.filter(Generation.id.in_(gids)).all() if gids else []:
        gen.archived_at = None
    db.session.commit()
    return jsonify(ok=True)


@history_bp.route("/archived")
def archived():
    """The archive: every archived recipe, most recently archived first, each
    with a restore button. Failed generations aren't listed — there's nothing
    in one to restore."""
    recipes = (Recipe.query.filter(Recipe.archived_at.isnot(None))
               .order_by(Recipe.archived_at.desc(), Recipe.id.desc()).all())
    return render_template("history/archived.html", recipes=recipes)
