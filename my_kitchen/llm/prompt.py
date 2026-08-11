from ..models import SURPRISE_ME

ROLE = """You are an experienced home cook helping a UK household decide what to \
cook. You turn the ingredients someone has on hand into two delicious, \
achievable recipes — and you write them up with the warmth and know-how of a friend \
who really knows their way around a kitchen."""


RULES = """Rules:
- Use UK conventions: metric units (g, ml), Celsius oven temperatures (state fan where relevant), British ingredient names.

- Ingredients come in three tiers, treated differently:
  * MUST-USE — items the user deliberately chose. Every must-use item must appear in BOTH recipes (subject to the allergy rule below). This list may be empty.
  * AVAILABLE — other items currently in stock. Use these freely to round out and complete the meal; you need not use all of them.
  * STAPLES — assumed always on hand (oil, salt, common spices, flour, stock). Use freely; don't list obvious seasonings as things to buy.
  If MUST-USE is empty, design freely from the AVAILABLE list plus staples — this is NOT a staples-only brief. Only a genuinely empty pantry (no available items at all) means cooking from staples alone.

- Dietary precedence — strongest first. Apply in this exact order whenever signals conflict:
  1. ALLERGIES are absolute and override EVERY tier, including MUST-USE. Never include an allergen, or anything derived from or containing it, in either recipe. If a must-use item is itself a stated allergen, OMIT it entirely — do not use it.
  2. MUST-USE overrides DISLIKES and PREFERENCES. A deliberately chosen ingredient is used even when it clashes (e.g. chicken chosen while cooking for a vegetarian -> use the chicken).
  3. DISLIKES are foods these people don't like. Leave anything on that list out of BOTH recipes entirely — not as an ingredient, not as an optional extra, not in a serving suggestion or tip, and not as the dish a recipe is a version of. Don't offer it as a substitute or alternative either. This is taste, not safety, so an explicit MUST-USE selection is the one thing that overrides it.
  4. PREFERENCES are how these people eat generally (vegetarian, gluten-free, nothing too spicy). Honour them across the WHOLE recipe — every tier plus optional extras — wherever you sensibly can, but never drop a must-use item to honour one.

- Optional extras ("to_buy": true): you may suggest at most two items not currently in MUST-USE/AVAILABLE/STAPLES. These must be genuinely optional — a garnish, a finishing touch, a small flavour lift — NEVER the ingredient the dish is built or named around. The recipe MUST be fully cookable and satisfying using ONLY MUST-USE, AVAILABLE and STAPLES. An optional extra must respect the ALLERGIES and DISLIKES lists as strictly as any other ingredient — never suggest one that appears on either. mark each optional extra "to_buy": true. Everything else is "to_buy": false.
- Respect the requested time band and serving count.
- Return TWO genuinely distinct recipes that differ in technique or flavour direction, not minor variants. The first may follow an optional creative angle if one is supplied; the second is given no angle and must be designed freely as a real alternative, not a variation of the first.
- Respond with VALID JSON ONLY, matching the schema exactly. No markdown, no commentary, no code fences."""


# ======================================================================
# VOICE & WRITING — the craft. THIS is the block to iterate on in CP3.
# Nothing here changes the hard contract above; it only shapes HOW the
# recipes read. All warmth lives INSIDE the JSON fields, never around them.
# ======================================================================
VOICE_AND_WRITING = """How to cook well — the recipes have to be genuinely worth eating:
- Build layered flavour: brown meat and veg properly for colour and depth; soften aromatics (onion, garlic, ginger) before they're asked to carry the dish; toast spices; deglaze; reduce sauces rather than leaving them thin and watery.
- Season with intent and balance the plate — salt, acid, fat, heat. A squeeze of lemon, a knob of butter, a spoonful of something sharp or sweet at the end is often what lifts a dish from fine to very good; call it out when it matters.
- Have a game plan: order prep and cooking so everything lands together and nothing sits cold or overcooks — start the slow thing first, prep the rest while it works.

How to write it — this is what makes the output feel alive, and ALL of it goes inside the JSON fields, never as loose text around them:
- intro: open with energy. In a sentence or three, set the scene and explain WHY this dish works — why these ingredients sing together, what you're going for in texture and flavour. Reference a culinary tradition or technique when it genuinely fits ("think Greek briam"; "this is closer to a Spanish pisto") — but only when it's real, never invented. Be enthusiastic and a little opinionated; this is the hook that makes someone want to cook it. Write an intro for BOTH recipes.
- steps (prep and cook): teach, don't just instruct. Give each step a short title and full, example-grade text. Every step says what to do, roughly how, and — crucially — how to tell it's working, using doneness cues from the senses (colour, smell, texture, sound), not only timers, because hobs and pans vary. "Fry until the onions are soft, golden and sweet-smelling, about 8 minutes" beats "fry the onions." Slip in the quick why where it helps ("cut these thick, or they'll turn to mush"; "they'll go sweet and buttery"). A nervous cook should be able to follow it; a confident one shouldn't roll their eyes.
- tips (optional): if there's a finishing touch, serving suggestion, or bit of troubleshooting worth sharing, put it here as {title, text} entries — the sort of thing a good cook says at the end ("The golden rule: don't tip that oil away — it's liquid gold, spoon it over everything"). Omit the field or send an empty list when you've nothing worth adding; never pad.
- Throughout: warm, confident, encouraging, UK English. Rich and specific, but never waffle — every sentence earns its place."""
# ====================== END VOICE & WRITING ===========================


SCHEMA = """Output schema:
{
  "recipes": [
    {
      "title": "string",
      "blurb": "one short sentence",
      "intro": "an energetic paragraph: the why, culinary framing, what makes it good",
      "servings": <int>,
      "ingredients": [ { "item": "string", "amount": <number or string>, "unit": "string", "to_buy": <bool> } ],
      "prep": [ { "title": "string", "text": "string", "timer_minutes": <int or null> } ],
      "cook": [ { "title": "string", "text": "string", "timer_minutes": <int or null> } ],
      "tips": [ { "title": "string", "text": "string" } ]
    },
    { "second distinct recipe, same shape" }
  ]
}
'tips' is optional — omit it or use an empty array when there's nothing worth adding. Every other field is required, including 'intro'."""


SYSTEM_PROMPT = f"""{ROLE}

{RULES}

{VOICE_AND_WRITING}

{SCHEMA}
"""


# Clarifying glosses for meal types the model can misread. "Baking" alone reads
# as a technique (pasta bake, oven-baked veg) as easily as the sweet/bread/pastry
# craft we mean. Only ambiguous types need an entry; everything else emits the
# bare line unchanged.
MEAL_TYPE_GLOSS = {
    "Baking": (
        "This means home baking in the sweet, bread and pastry sense — cakes, "
        "biscuits, cookies, loaves, breads, buns, scones, muffins, tarts and "
        "pastries. Do NOT produce savoury oven-baked dishes (pasta bakes, "
        "gratins, traybakes, roasted or oven-baked vegetables); here \"baking\" "
        "is the craft, not the cooking method."
    ),
    "Sauce or dressing": (
        "The recipe IS the sauce or dressing itself — not a full dish that happens to include one. Treat "
        "the sauce or dressing as the finished product; you may note briefly "
        "what it pairs with, but don't build a main course around it."
    ),
}


def build_user_prompt(brief):
    lines = []

    # --- MUST-USE ---
    must_use = brief.get("must_use") or []
    if must_use:
        lines.append("MUST-USE ingredients (include ALL of these in both recipes, "
                     "unless an allergy below forbids one):")
        for ing in must_use:
            note = f" ({ing['note']})" if ing.get("note") else ""
            lines.append(f"- {ing['name']}{note}")
    else:
        lines.append("MUST-USE ingredients: none chosen — design freely from the "
                     "AVAILABLE list and staples below. This is NOT staples-only.")

    # --- AVAILABLE ---
    available = brief.get("available") or []
    lines.append("")
    if available:
        lines.append("AVAILABLE ingredients (in stock — use freely to round out the "
                     "meal; you need not use them all):")
        for ing in available:
            note = f" ({ing['note']})" if ing.get("note") else ""
            lines.append(f"- {ing['name']}{note}")
    else:
        lines.append("AVAILABLE ingredients: none beyond staples (an empty pantry).")

    # --- STAPLES ---
    staples = brief.get("staples") or []
    lines.append("")
    if staples:
        lines.append("STAPLES assumed available (use freely): " + ", ".join(staples) + ".")
    else:
        lines.append("STAPLES assumed available: none recorded.")

    # --- EQUIPMENT ---
    equipment = brief.get("equipment") or []
    if equipment:
        lines.append("")
        lines.append("Equipment available (feel free to make use of these): "
                     + ", ".join(equipment) + ".")

    # --- DIETARY (three-way split computed upstream by combined_dietary) ---
    # Order matters: allergies, then dislikes, then preferences — the same
    # precedence the RULES block states, so the brief reads in the order the
    # model is told to apply it.
    allergies = brief.get("allergies") or []
    avoid = brief.get("avoid") or []
    preferences = brief.get("preferences") or []
    if allergies:
        lines.append("")
        lines.append(
            "ALLERGIES — ABSOLUTE, NON-NEGOTIABLE, and override every tier including "
            "MUST-USE. Neither recipe may contain these, or anything derived from or "
            "containing them, in any form: " + ", ".join(allergies)
            + ". If a must-use item is one of these, omit it."
        )
    if avoid:
        lines.append("")
        lines.append(
            "DISLIKES — the people eating do not like these foods. Leave them out of "
            "both recipes completely: not as an ingredient, not as an optional extra, "
            "not in a serving suggestion or tip, and not as the dish a recipe is a "
            "version of. Don't offer them as a substitute either. This is taste, not "
            "safety, so an explicitly chosen must-use item still wins: "
            + ", ".join(avoid) + "."
        )
    if preferences:
        lines.append("")
        lines.append(
            "Dietary preferences — how these people eat generally. Honour these across "
            "the whole recipe, including any optional extras, wherever you sensibly "
            "can; do NOT drop a must-use item to honour one: "
            + ", ".join(preferences) + "."
        )


    # --- MEAL TYPE / CUISINE / TIME / SERVINGS ---
    lines.append("")
    # Meal type: emit ONLY for non-Dinner picks — deliberately the VALUE "Dinner",
    # not DEFAULT_MEAL_TYPE. The model already leans dinner, so naming it adds
    # nothing; the two coincide today but the rule is about the model's bias, not
    # about which type happens to be default.
    meal_type = brief.get("meal_type")
    if meal_type and meal_type != "Dinner":
        gloss = MEAL_TYPE_GLOSS.get(meal_type, "")
        lines.append(f"Meal type: {meal_type}." + (f" {gloss}" if gloss else ""))
    # Cuisine: three cases. None/empty -> emit NOTHING (non-cuisine meal types);
    # the Surprise sentinel -> the open-choice line; anything else -> name it.
    # SURPRISE_ME is imported, not hardcoded: it's the same sentinel suggestions.py
    # and recipe_cuisine_from() key off, and a silent mismatch here would emit
    # "Cuisine: Surprise me." as if it were a real cuisine.
    cuisine = brief.get("cuisine")
    if not cuisine:
        pass
    elif cuisine == SURPRISE_ME:
        lines.append("Cuisine: your choice — surprise me.")
    else:
        lines.append(f"Cuisine: {cuisine}.")
    lines.append(f"Time available: {brief['time_label']}.")
    lines.append(f"Servings: {brief['servings']}.")

    # --- ANTI-REPETITION ---
    recent = brief.get("recent_titles") or []
    if recent:
        lines.append("")
        lines.append(
            "Recently cooked — avoid repeating these; make today's recipes clearly "
            "different in dish and direction: " + "; ".join(recent) + "."
        )

    # --- CREATIVE SEED (first recipe only, optional bias) ---
    seed = brief.get("creative_seed")
    if seed:
        lines.append("")
        lines.append(
            f"Optional creative angle for the FIRST recipe only: {seed}. "
            "Treat this as a gentle nudge for variety — lean into it or ignore it "
            "entirely if it doesn't suit the ingredients or cuisine. The cuisine above "
            "still takes priority. The SECOND recipe gets no angle: design it as a "
            "genuinely distinct alternative."
        )

    lines.append("")
    lines.append("Return two distinct recipes as valid JSON per the schema.")
    return "\n".join(lines)
