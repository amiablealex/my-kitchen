SYSTEM_PROMPT = """You are a home cooking assistant for a UK household. \
You design delicious, realistic recipes from the ingredients a user has on hand.

Rules:
- Use UK conventions: metric units (g, ml), Celsius oven temperatures (state fan where relevant), British ingredient names.
- Build the recipes around the user's chosen ingredients. You may freely assume the listed staples are available.
- You may suggest at most two extra items the user might need to buy; mark each "to_buy": true. Everything else is "to_buy": false.
- If the brief lists allergies, they are absolute: never include those ingredients, or anything derived from or containing them, in either recipe. Dietary preferences are softer steers to honour where reasonable.
- Respect the requested time band and serving count.
- Return TWO genuinely distinct recipes that differ in technique or flavour direction, not minor variants.
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
    if brief["ingredients"]:
        lines.append("Core ingredients to use up:")
        for ing in brief["ingredients"]:
            note = f" ({ing['note']})" if ing.get("note") else ""
            lines.append(f"- {ing['name']}{note}")
    else:
        lines.append("No specific core ingredients chosen — design around staples and at most two suggested extras.")

    if brief["staples"]:
        lines.append("")
        lines.append("Staples assumed available: " + ", ".join(brief["staples"]) + ".")

    allergies = brief.get("allergies") or []
    preferences = brief.get("preferences") or []
    if allergies:
        lines.append("")
        lines.append(
            "ALLERGIES — ABSOLUTE, NON-NEGOTIABLE. Neither recipe may contain these, "
            "or anything derived from or containing them, in any form: "
            + ", ".join(allergies) + "."
        )
    if preferences:
        lines.append("")
        lines.append(
            "Dietary preferences (lean this way where you sensibly can): "
            + ", ".join(preferences) + "."
        )

    lines.append("")
    cuisine = brief["cuisine"]
    if cuisine and cuisine.lower() != "surprise me":
        lines.append(f"Cuisine: {cuisine}.")
    else:
        lines.append("Cuisine: your choice — surprise me.")
    lines.append(f"Time available: {brief['time_label']}.")
    lines.append(f"Servings: {brief['servings']}.")
    lines.append("")
    lines.append("Return two distinct recipes as valid JSON per the schema.")
    return "\n".join(lines)
