"""Recipe version families (0.41.0).

A refine makes a new version of a recipe, and its Generation row records which
recipe it came from (``source_recipe_id``). Read the other way, those rows are a
tree: the original at the root, each version a child of the one it was made
from. Phase 26 kept that tree a straight line by only letting the newest
version be refined; from 0.41.0 any live version can be, so a family can branch.

Everything that needs to know about versions asks this module, so the trail,
History, the Archive page, suggestions and the home page's "you could make"
line can't disagree:

* **Numbers** are creation order within the family (v1 is the original) and
  never change. A removed version keeps its number, so v3 stays v3 after v2 is
  removed, and comes back as v2 if it's restored.
* **The main version** is the newest live one. It is the family's one row in
  History, and the version suggestions prefer. ``reseat_main`` keeps
  ``was_chosen`` in step with it, so the existing ``was_chosen`` filters keep
  working: in a family of more than one, exactly the main version is chosen.
  A family of one is left alone (the choice screen decides it, as before).
* **Removing** a version only works at the end of a branch (nothing live was
  made from it), and never on the original: that's archiving the recipe.

The tree is built from one small query over the refine generations. At
household scale that's cheaper and simpler than a stored family column, and it
needs no migration or backfill.
"""

import re

from .extensions import db
from .models import Generation, Recipe


def _edges():
    """{child recipe id: parent recipe id} for every finished refine."""
    rows = (db.session.query(Recipe.id, Generation.source_recipe_id)
            .join(Generation, Recipe.generation_id == Generation.id)
            .filter(Generation.kind == "refine", Generation.source_recipe_id.isnot(None))
            .all())
    return {child: parent for child, parent in rows}


def _root(rid, parent_of):
    seen = set()
    while rid in parent_of and rid not in seen:
        seen.add(rid)
        rid = parent_of[rid]
    return rid


def _order(recipe):
    # SQLite hands back naive datetimes; a row created in this session may
    # still hold the aware one it was given. Compare them as naive UTC.
    at = recipe.created_at
    if at is not None and at.tzinfo is not None:
        at = at.replace(tzinfo=None)
    return (at is None, at, recipe.id)


class Family:
    """One recipe's versions: the original and everything made from it."""

    def __init__(self, members, parent_of):
        self.members = sorted(members, key=_order)
        self.by_id = {r.id: r for r in self.members}
        self.parent_of = {r.id: parent_of[r.id] for r in self.members
                          if r.id in parent_of and parent_of[r.id] in self.by_id}
        self.children_of = {}
        for r in self.members:
            p = self.parent_of.get(r.id)
            if p is not None:
                self.children_of.setdefault(p, []).append(r)
        self.root = next((r for r in self.members if r.id not in self.parent_of), self.members[0])
        self.number = {r.id: i + 1 for i, r in enumerate(self.members)}

    @property
    def size(self):
        return len(self.members)

    @property
    def live(self):
        return [r for r in self.members if not r.is_archived]

    @property
    def main(self):
        """The newest live version, or None when the whole family is archived."""
        live = self.live
        return live[-1] if live else None

    @property
    def next_number(self):
        return self.size + 1

    def parent(self, recipe):
        pid = self.parent_of.get(recipe.id)
        return self.by_id.get(pid) if pid is not None else None

    def ancestors(self, recipe):
        """Root first, not including the recipe itself."""
        out, r = [], self.parent(recipe)
        while r is not None and r not in out:
            out.append(r)
            r = self.parent(r)
        return list(reversed(out))

    def live_children(self, recipe):
        return [c for c in self.children_of.get(recipe.id, []) if not c.is_archived]

    def label(self, recipe):
        if recipe.id == self.root.id:
            return "Original"
        g = recipe.generation
        return (g.instruction if g is not None and g.instruction else "Refined")

    def removable(self, recipe):
        """Only the end of a branch, never the original, and only while live."""
        return (self.size > 1 and recipe.id != self.root.id and not recipe.is_archived
                and not self.live_children(recipe))

    def trail(self, current):
        """The version trail as rows (0.41.0). The first row runs from the
        original along each version's first child; every other child starts a
        row of its own, marked with the version it came from. Shows the live
        versions, plus the one being viewed and what it was made from (so an
        archived version still shows where it sits).

        Returns (rows, new_slot): rows are {"from": n or None, "nodes": [...]},
        each node {"recipe", "n", "label", "current"}; new_slot is "end" when
        "+ New version" belongs at the end of the current version's row, or
        "branch" when the current version already has a version made from it,
        so a new one starts a branch."""
        visible = {r.id for r in self.live} | {current.id} | {a.id for a in self.ancestors(current)}
        # Keep the set closed under "made from", so no row starts mid-air.
        for rid in list(visible):
            visible.update(a.id for a in self.ancestors(self.by_id[rid]))

        def kids(r):
            return [c for c in self.children_of.get(r.id, []) if c.id in visible]

        rows = []

        def build(start, from_n):
            row = {"from": from_n, "nodes": []}
            rows.append(row)
            pending, r = [], start
            while r is not None:
                row["nodes"].append({"recipe": r, "n": self.number[r.id], "label": self.label(r),
                                     "current": r.id == current.id})
                ks = kids(r)
                pending.extend((k, self.number[r.id]) for k in ks[1:])
                r = ks[0] if ks else None
            for k, n in pending:
                build(k, n)

        build(self.root, None)
        new_slot = "branch" if self.live_children(current) else "end"
        return rows, new_slot


def _load(ids):
    return Recipe.query.filter(Recipe.id.in_(ids)).all() if ids else []


def family_of(recipe, edges=None):
    """The family a recipe belongs to (a family of one when it has no versions)."""
    parent_of = _edges() if edges is None else edges
    root = _root(recipe.id, parent_of)
    # Every recipe whose root is this one.
    ids = {root} | {c for c in parent_of if _root(c, parent_of) == root}
    members = _load(ids) if len(ids) > 1 else [recipe]
    return Family(members, parent_of)


def families():
    """{recipe id: Family} for every recipe in a family of more than one.
    Recipes with no versions aren't in the map."""
    parent_of = _edges()
    groups = {}
    for rid in set(parent_of) | set(parent_of.values()):
        groups.setdefault(_root(rid, parent_of), set()).add(rid)
    recipes = {r.id: r for r in _load(set().union(*groups.values()) if groups else set())}
    out = {}
    for ids in groups.values():
        fam = Family([recipes[i] for i in ids if i in recipes], parent_of)
        for i in ids:
            out[i] = fam
    return out


def reseat_main(family):
    """Point was_chosen at the family's main version (the newest live one).
    A family of one is left alone. Call after anything that adds, removes,
    archives or restores a version; the caller commits."""
    if family.size < 2:
        return
    main = family.main
    for r in family.members:
        r.was_chosen = main is not None and r.id == main.id


def version_badges(recipes, fams=None):
    """{recipe id: version number} for recipes that aren't their family's main
    version — what a suggestion card shows as "v2"."""
    fams = families() if fams is None else fams
    out = {}
    for r in recipes:
        fam = fams.get(r.id)
        if fam is not None and fam.main is not None and fam.main.id != r.id:
            out[r.id] = fam.number[r.id]
    return out


def one_per_family(recipes, fams=None):
    """Keep one recipe per family, in the order given. When several versions
    of a family are in the list, the main version wins if it's there,
    otherwise the newest one. Recipes with no versions pass straight through."""
    fams = families() if fams is None else fams
    best = {}
    for r in recipes:
        fam = fams.get(r.id)
        if fam is None:
            continue
        key = fam.root.id
        cur = best.get(key)
        if cur is None:
            best[key] = r
        elif fam.main is not None and r.id == fam.main.id:
            best[key] = r
        elif (fam.main is None or cur.id != fam.main.id) and _order(r) > _order(cur):
            best[key] = r
    out = []
    for r in recipes:
        fam = fams.get(r.id)
        if fam is None or best.get(fam.root.id) is r:
            out.append(r)
    return out


# --- What changed (0.41.0) ----------------------------------------------------
# Worked out from the ingredient lines, not written by the model: it's a check
# on what the new version actually did, so it has to come from the rows.

_COMMA = re.compile(r"\s*[,(].*$")
_SPACES = re.compile(r"\s+")


def _text_key(raw):
    return _SPACES.sub(" ", _COMMA.sub("", (raw or "").strip().lower())).strip()


def _line_key(line):
    if line.ingredient_id is not None:
        return ("i", line.ingredient_id)
    return ("t", _text_key(line.raw_text))


def _line_name(line):
    if line.ingredient is not None:
        return line.ingredient.name.lower()
    return _text_key(line.raw_text)


def _join(names, cap=4):
    if len(names) > cap:
        names = names[:cap - 1] + [f"{len(names) - (cap - 1)} more"]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def version_changes(parent, child):
    """Short sentences saying what the child changed from its parent's
    ingredients, e.g. ["Added courgette and banana (not in stock).",
    "Dropped potato.", "Now serves 4 (was 2)."], or ["Same ingredients."].
    Empty when either version has no structured lines (legacy rows)."""
    if parent is None or not parent.ingredients or not child.ingredients:
        return []
    before = {}
    for line in parent.ingredients:
        before.setdefault(_line_key(line), line)
    after = {}
    for line in child.ingredients:
        after.setdefault(_line_key(line), line)
    added = [line for k, line in after.items() if k not in before and k[1]]
    dropped = [line for k, line in before.items() if k not in after and k[1]]
    out = []
    if added:
        names = []
        for line in added:
            name = _line_name(line)
            if line.ingredient is not None and not line.satisfied:
                name += " (not in stock)"
            names.append(name)
        out.append(f"Added {_join(names)}.")
    if dropped:
        out.append(f"Dropped {_join([_line_name(l) for l in dropped])}.")
    if parent.servings and child.servings and parent.servings != child.servings:
        out.append(f"Now serves {child.servings} (was {parent.servings}).")
    return out or ["Same ingredients."]
