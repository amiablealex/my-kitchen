"""Phase 11 CP1 — render golden + spot-check prompts for an API-free,
deterministic regression diff. No DB or app context needed (build_user_prompt
is pure). Run on the unchanged code FIRST to capture a baseline, then again
after the prompt change, and diff the two.

    python -m my_kitchen.eval.render_prompts > /tmp/prompts_before.txt   # before edits
    # ...apply the prompt.py change...
    python -m my_kitchen.eval.render_prompts > /tmp/prompts_after.txt
    diff /tmp/prompts_before.txt /tmp/prompts_after.txt

Expected: the GOLDEN BRIEFS sections show NO diff (byte-identical regression
pass); the only differences fall inside SPOT CHECKS, where Dessert gains a
"Meal type:" line and loses its cuisine line.
"""
from ..llm.prompt import build_user_prompt
from .golden_briefs import GOLDEN_BRIEFS

# Minimal well-formed briefs exercising the Phase 11 paths. Kept here (not in
# golden_briefs.py) until CP3 adds the real Dessert golden.
_SPOT_CHECKS = [
    ("spot__dessert_no_cuisine", {
        "must_use": [],
        "available": [{"name": "eggs", "note": None},
                      {"name": "dark chocolate", "note": None},
                      {"name": "butter", "note": None}],
        "staples": ["plain flour", "caster sugar", "salt", "vanilla"],
        "equipment": ["oven"], "allergies": [], "preferences": [],
        "meal_type": "Dessert", "cuisine": None,
        "time_band": "relaxed", "time_label": "Relaxed (30–75 min)",
        "servings": 4, "recent_titles": [], "creative_seed": None,
    }),
    ("spot__breakfast_with_cuisine", {
        "must_use": [], "available": [{"name": "eggs", "note": None}],
        "staples": ["salt"], "equipment": ["frying pan"],
        "allergies": [], "preferences": [],
        "meal_type": "Breakfast", "cuisine": "British",
        "time_band": "quick", "time_label": "Quick (under 30 min)",
        "servings": 2, "recent_titles": [], "creative_seed": None,
    }),
]


def main():
    print("===== GOLDEN BRIEFS (must be byte-identical across the change) =====")
    for b in GOLDEN_BRIEFS:
        print(f"\n### {b['name']}")
        print(build_user_prompt(b["brief"]))
    print("\n\n===== SPOT CHECKS (Phase 11 — expected to change) =====")
    for name, brief in _SPOT_CHECKS:
        print(f"\n### {name}")
        print(build_user_prompt(brief))


if __name__ == "__main__":
    main()
