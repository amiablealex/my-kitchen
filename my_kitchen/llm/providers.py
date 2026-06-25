import json


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-3.5-flash",  # 3.5 reasons + writes noticeably better than 2.5-flash for this task
}

DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 8000


class ProviderError(RuntimeError):
    """Raised when a provider can't be used (missing key, missing SDK, API error)."""


class MockProvider:
    """Returns canned-but-brief-aware recipe JSON. No key or SDK required.
    Ignores temperature/max_tokens; never truncates."""
    name = "mock"

    def __init__(self, model=None, temperature=None, max_tokens=None, **kwargs):
        self.model = model or "mock-1"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.last_finish_reason = None  # set per generate() call

    def generate(self, system_prompt, user_prompt, brief=None):
        self.last_finish_reason = "stop"
        return json.dumps(_mock_payload(brief or {}))


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key, model=None, temperature=None, max_tokens=None, **kwargs):
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set.")
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS["anthropic"]
        self.temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.last_finish_reason = None

    def generate(self, system_prompt, user_prompt, brief=None):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ProviderError("The 'anthropic' package isn't installed. Run: pip install anthropic") from e
        client = Anthropic(api_key=self.api_key)
        self.last_finish_reason = None
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            raise ProviderError(f"Anthropic API call failed: {e}") from e
        # "max_tokens" here means the response was cut off — the harness reads this.
        self.last_finish_reason = getattr(resp, "stop_reason", None)
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model=None, temperature=None, max_tokens=None, **kwargs):
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set.")
        self.api_key = api_key
        self.model = model or DEFAULT_MODELS["gemini"]
        self.temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.last_finish_reason = None

    def generate(self, system_prompt, user_prompt, brief=None):
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ProviderError("The 'google-genai' package isn't installed. Run: pip install google-genai") from e
        client = genai.Client(api_key=self.api_key)
        self.last_finish_reason = None
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",  # ask Gemini for clean JSON
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            )
        except Exception as e:
            raise ProviderError(f"Gemini API call failed: {e}") from e
        # finish_reason lives on the candidate; defensive in case the shape varies.
        try:
            self.last_finish_reason = resp.candidates[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            self.last_finish_reason = None
        return resp.text


def get_provider(config):
    provider = (config.get("LLM_PROVIDER") or "mock").lower()
    common = {
        "model": config.get("LLM_MODEL") or None,
        "temperature": config.get("LLM_TEMPERATURE", DEFAULT_TEMPERATURE),
        "max_tokens": config.get("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
    }
    if provider == "mock":
        return MockProvider(**common)
    if provider == "anthropic":
        return AnthropicProvider(api_key=config.get("ANTHROPIC_API_KEY"), **common)
    if provider == "gemini":
        return GeminiProvider(api_key=config.get("GEMINI_API_KEY"), **common)
    raise ProviderError(f"Unknown LLM_PROVIDER '{provider}'. Use mock, anthropic, or gemini.")


def _mock_payload(brief):
    """Two distinct recipes referencing the actual brief — now also carrying the
    Phase 4b intro + optional tips so the mock exercises the full contract and
    display offline. Not constraint-aware (it'll happily echo an allergen): the
    mock proves PLUMBING; the real providers prove the RULES."""
    must_use = [i["name"] for i in brief.get("must_use", [])]
    available = [i["name"] for i in brief.get("available", [])]
    pool = must_use + available
    servings = brief.get("servings", 2)
    # `or` (not a .get default) because the key can now be present-but-None for
    # non-cuisine meal types (Phase 11); .get's default only fires on a MISSING key.
    cuisine = brief.get("cuisine") or "Surprise me"
    seed = brief.get("creative_seed")
    hero = pool[0] if pool else "seasonal veg"
    second = pool[1] if len(pool) > 1 else "onion"
    prefix = "" if cuisine.lower() == "surprise me" else f"{cuisine} "

    traybake = {
        "title": f"{prefix}{hero} traybake",
        "blurb": (f"A simple one-tray dinner built around {hero}"
                  + (f"; angle: {seed}." if seed else ".")),
        "intro": (f"This is the kind of fuss-free tray dinner that lets {hero} do the "
                  f"talking — everything roasts together so the flavours mingle, and "
                  f"you're left with one tray to wash."
                  + (f" Today's angle: {seed}." if seed else "")),
        "servings": servings,
        "ingredients": [
            {"item": hero, "amount": servings, "unit": "portions", "to_buy": False},
            {"item": second, "amount": 1, "unit": "", "to_buy": False},
            {"item": "olive oil", "amount": 2, "unit": "tbsp", "to_buy": False},
            {"item": "lemon", "amount": 1, "unit": "", "to_buy": True},
        ],
        "prep": [
            {"title": "Heat oven", "text": "Preheat the oven to 200C (180C fan).", "timer_minutes": None},
            {"title": "Chop", "text": f"Roughly chop the {second} and any veg into even pieces so they cook at the same rate.", "timer_minutes": None},
        ],
        "cook": [
            {"title": "Roast", "text": f"Toss {hero} and {second} with the oil, season well, and roast until golden and tender at the edges.", "timer_minutes": 30},
            {"title": "Finish", "text": "Squeeze over the lemon and serve straight from the tray.", "timer_minutes": None},
        ],
        "tips": [
            {"title": "Don't waste the pan juices", "text": "Spoon the oily, savoury juices from the tray back over everything before serving."},
        ],
    }
    stirfry = {
        "title": f"Quick {hero} stir-fry",
        "blurb": f"A fast, savoury stir-fry showcasing {hero}.",
        "intro": (f"When you want dinner in minutes, a hot pan and {hero} is all you "
                  f"need. The trick is high heat and keeping everything moving so it "
                  f"sears rather than steams."),
        "servings": servings,
        "ingredients": [
            {"item": hero, "amount": servings, "unit": "portions", "to_buy": False},
            {"item": "soy sauce", "amount": 2, "unit": "tbsp", "to_buy": False},
            {"item": "garlic", "amount": 2, "unit": "cloves", "to_buy": False},
            {"item": "spring onions", "amount": 1, "unit": "bunch", "to_buy": True},
        ],
        "prep": [
            {"title": "Prep", "text": f"Slice the {hero} thinly and mince the garlic — have everything ready by the hob, as stir-frying moves fast.", "timer_minutes": None},
        ],
        "cook": [
            {"title": "Fry", "text": "Get a wok very hot, add a little oil, then fry the garlic for a few seconds until fragrant but not browned.", "timer_minutes": None},
            {"title": "Combine", "text": f"Add the {hero}, splash in the soy, and toss over high heat until just cooked and glossy.", "timer_minutes": 6},
            {"title": "Serve", "text": "Scatter over the spring onions and serve at once.", "timer_minutes": None},
        ],
        "tips": [],  # exercises the "no tips" display path
    }
    return {"recipes": [traybake, stirfry]}
