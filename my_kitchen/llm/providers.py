import json


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-flash",  # override via LLM_MODEL, e.g. gemini-3.5-flash
}


class ProviderError(RuntimeError):
    """Raised when a provider can't be used (missing key, missing SDK, API error)."""


class MockProvider:
    """Returns canned-but-brief-aware recipe JSON. No key or SDK required."""
    name = "mock"

    def __init__(self, model=None, **kwargs):
        self.model = model or "mock-1"

    def generate(self, system_prompt, user_prompt, brief=None):
        return json.dumps(_mock_payload(brief or {}))


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key, model=None, **kwargs):
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set.")
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS["anthropic"]

    def generate(self, system_prompt, user_prompt, brief=None):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ProviderError("The 'anthropic' package isn't installed. Run: pip install anthropic") from e
        client = Anthropic(api_key=self.api_key)
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            raise ProviderError(f"Anthropic API call failed: {e}") from e
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model=None, **kwargs):
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set.")
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS["gemini"]

    def generate(self, system_prompt, user_prompt, brief=None):
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ProviderError("The 'google-genai' package isn't installed. Run: pip install google-genai") from e
        client = genai.Client(api_key=self.api_key)
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",  # ask Gemini for clean JSON
                ),
            )
        except Exception as e:
            raise ProviderError(f"Gemini API call failed: {e}") from e
        return resp.text


def get_provider(config):
    provider = (config.get("LLM_PROVIDER") or "mock").lower()
    model = config.get("LLM_MODEL") or None
    if provider == "mock":
        return MockProvider(model=model)
    if provider == "anthropic":
        return AnthropicProvider(api_key=config.get("ANTHROPIC_API_KEY"), model=model)
    if provider == "gemini":
        return GeminiProvider(api_key=config.get("GEMINI_API_KEY"), model=model)
    raise ProviderError(f"Unknown LLM_PROVIDER '{provider}'. Use mock, anthropic, or gemini.")


def _mock_payload(brief):
    """Two distinct recipes that reference the actual brief, so the mock
    exercises the display realistically."""
    selected = [i["name"] for i in brief.get("ingredients", [])]
    servings = brief.get("servings", 2)
    cuisine = brief.get("cuisine", "Surprise me")
    hero = selected[0] if selected else "seasonal veg"
    second = selected[1] if len(selected) > 1 else "onion"
    prefix = "" if cuisine.lower() == "surprise me" else f"{cuisine} "

    traybake = {
        "title": f"{prefix}{hero} traybake",
        "blurb": f"A simple one-tray dinner built around {hero}.",
        "servings": servings,
        "ingredients": [
            {"item": hero, "amount": servings, "unit": "portions", "to_buy": False},
            {"item": second, "amount": 1, "unit": "", "to_buy": False},
            {"item": "olive oil", "amount": 2, "unit": "tbsp", "to_buy": False},
            {"item": "lemon", "amount": 1, "unit": "", "to_buy": True},
        ],
        "prep": [
            {"title": "Heat oven", "text": "Preheat the oven to 200C (180C fan).", "timer_minutes": None},
            {"title": "Chop", "text": f"Roughly chop the {second} and any veg into even pieces.", "timer_minutes": None},
        ],
        "cook": [
            {"title": "Roast", "text": f"Toss {hero} and {second} with the oil, season, and roast until golden.", "timer_minutes": 30},
            {"title": "Finish", "text": "Squeeze over the lemon and serve.", "timer_minutes": None},
        ],
    }
    stirfry = {
        "title": f"Quick {hero} stir-fry",
        "blurb": f"A fast, savoury stir-fry showcasing {hero}.",
        "servings": servings,
        "ingredients": [
            {"item": hero, "amount": servings, "unit": "portions", "to_buy": False},
            {"item": "soy sauce", "amount": 2, "unit": "tbsp", "to_buy": False},
            {"item": "garlic", "amount": 2, "unit": "cloves", "to_buy": False},
            {"item": "spring onions", "amount": 1, "unit": "bunch", "to_buy": True},
        ],
        "prep": [
            {"title": "Prep", "text": f"Slice the {hero} thinly and mince the garlic.", "timer_minutes": None},
        ],
        "cook": [
            {"title": "Fry", "text": "Get a wok very hot, add a little oil, then fry the garlic briefly.", "timer_minutes": None},
            {"title": "Combine", "text": f"Add the {hero}, splash in the soy, and toss for a few minutes.", "timer_minutes": 6},
            {"title": "Serve", "text": "Scatter over the spring onions and serve.", "timer_minutes": None},
        ],
    }
    return {"recipes": [traybake, stirfry]}
