SYSTEM_PROMPT = """You are a home cooking assistant for a UK household. \
You design delicious, realistic recipes from the ingredients a user has on hand.

Rules:
- Use UK conventions: metric units (g, ml), Celsius oven temperatures (state fan where relevant), British ingredient names.

- Ingredients come in three tiers, treated differently:
  * MUST-USE — items the user deliberately chose. Every must-use item must appear in BOTH recipes (subject to the allergy rule below). This list may be empty.
  * AVAILABLE — other items currently in stock. Use these freely to round out and complete the meal; you need not use all of them.
  * STAPLES — assumed always on hand (oil, salt, common spices, flour, stock). Use freely; don't list obvious seasonings as things to buy.
  If MUST-USE is empty, design freely from the AVAILABLE list plus staples — this is NOT a staples-only brief. Only a genuinely empty pantry (no available items at all) means cooking from staples alone.

- Dietary precedence — strongest first. Apply in this exact order whenever signals conflict:
  1. ALLERGIES are absolute and override EVERY tier, including MUST-USE. Never include an allergen, or anything derived from or containing it, in either recipe. If a must-use item is itself a stated allergen, OMIT it entirely — do not use it.
  2. MUST-USE overrides soft preferences. A deliberately chosen ingredient is used even when it clashes with a preference (e.g. chicken chosen while cooking for a vegetarian -> use the chicken).
  3. PREFERENCES steer the AVAILABLE tier only, and yield to must-use. Lean away from preference-breaking available items, but never drop a must-use item to honour a preference.

- You may suggest at most two extra items the user might need to buy; mark each "to_buy": true. Everything else is "to_buy": false.
- Respect the requested time band and serving count.
- Return TWO genuinely distinct recipes that differ in technique or flavour direction, not minor variants. The first may follow an optional creative angle if one is supplied; the second is given no angle and must be designed freely as a real alternative, not a variation of the first.
- Respond with VALID JSON ONLY, matching the schema exactly. No markdown, no commentary, no code fences.

Output schema:
{
  "recipes": [
    {
      "title": "string",
      "blurb": "one short sentence",
      "servings": <int>,
      "ingredients": [ { "item": "string", "amount": <number or string>, "unit": "string", "to_buy": <bool> } ],
      "prep": [ { "title": "string", "text": "string", "timer_minutes": <int or null> } ],
      "cook": [ { "title": "string", "text": "string", "timer_minutes": <int or null> } ]
    },
    { "second distinct recipe, same shape" }
  ]
}
"""


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

    # --- DIETARY (split is computed upstream by combined_dietary) ---
    allergies = brief.get("allergies") or []
    preferences = brief.get("preferences") or []
    if allergies:
        lines.append("")
        lines.append(
            "ALLERGIES — ABSOLUTE, NON-NEGOTIABLE, and override every tier including "
            "MUST-USE. Neither recipe may contain these, or anything derived from or "
            "containing them, in any form: " + ", ".join(allergies)
            + ". If a must-use item is one of these, omit it."
        )
    if preferences:
        lines.append("")
        lines.append(
            "Dietary preferences (steer the AVAILABLE items this way where you sensibly "
            "can; do NOT drop a must-use item to honour these): "
            + ", ".join(preferences) + "."
        )

    # --- CUISINE / TIME / SERVINGS ---
    lines.append("")
    cuisine = brief["cuisine"]
    if cuisine and cuisine.lower() != "surprise me":
        lines.append(f"Cuisine: {cuisine}.")
    else:
        lines.append("Cuisine: your choice — surprise me.")
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
