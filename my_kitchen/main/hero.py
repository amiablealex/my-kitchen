"""The home page's rotating hero line (Phase 31).

A constant bank of short lines, one picked at random per visit. Some lines
take light real data: {name} (the logged-in cook), {a}/{b} (two in-stock,
non-staple ingredients; {A}/{B} capitalised for the start of a sentence) and
{n} (how many such items are in stock). A line is only eligible when the data
it needs exists, so the bank never renders a gap. Plain text — the template
autoescapes. Edit freely; no other code depends on the wording.
"""
import random
import string

# (line, minimum in-stock items it needs). {n} lines want a decent pantry.
HERO_LINES = [
    ("What are we cooking?", 0),
    ("Hungry? Let's sort that out.", 0),
    ("The kitchen's open.", 0),
    ("Let's make something worth sitting down for.", 0),
    ("Pans at the ready.", 0),
    ("Dinner won't decide itself.", 0),
    ("Fancy something new?", 0),
    ("Good food, no fuss.", 0),
    ("Let's see what we can rustle up.", 0),
    ("Apron on?", 0),
    ("Something good is about to happen.", 0),
    ("A little cooking, a lot of eating.", 0),
    ("Hello, {name}. What are we making?", 0),
    ("{name}, the kitchen's yours.", 0),
    ("Over to you, {name}.", 0),
    ("What does {name} fancy?", 0),
    ("{A} and {b} in. Something good will come of that.", 2),
    ("{A}, {b}, and an idea waiting to happen.", 2),
    ("Got {a}? Let's use it well.", 1),
    ("What shall we do with the {a}?", 1),
    ("There's {a} in. That's a start.", 1),
    ("{A} would like a word.", 1),
    ("{n} things in stock. Plenty to work with.", 6),
    ("{n} ingredients and one good idea away.", 6),
]

_FIELDS = string.Formatter()


def _fields(line):
    return {f for _, f, _, _ in _FIELDS.parse(line) if f}


def _lower_first(name):
    """'Chicken thigh' -> 'chicken thigh', but leave 'BBQ sauce' alone."""
    return name[0].lower() + name[1:] if name[1:2].islower() else name


def pick_line(name=None, items=(), avoid=None):
    """(index, text) of a random eligible line. `items` are in-stock
    ingredient names; `avoid` is the previous index so a reload doesn't
    repeat the same line twice running."""
    items = list(items)
    picked = random.sample(items, min(2, len(items)))
    data = {"name": name or "", "n": len(items)}
    if picked:
        data["a"] = _lower_first(picked[0])
        data["A"] = picked[0][:1].upper() + picked[0][1:]
    if len(picked) > 1:
        data["b"] = _lower_first(picked[1])
        data["B"] = picked[1][:1].upper() + picked[1][1:]

    def eligible(i):
        line, min_items = HERO_LINES[i]
        if len(items) < min_items:
            return False
        if "name" in _fields(line) and not name:
            return False
        return i != avoid

    choices = [i for i in range(len(HERO_LINES)) if eligible(i)] or [0]
    i = random.choice(choices)
    return i, HERO_LINES[i][0].format(**data)
