import json


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-3.5-flash",  # 3.5 reasons + writes noticeably better than 2.5-flash for this task
}

# Answering @kitchen questions (Phase 27): a short plain-text reply, so a Lite
# model. Falls back to the main model if this one is refused (see qa.py).
DEFAULT_QA_MODELS = {
    "gemini": "gemini-3.5-flash-lite",
}

DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 8000


class ProviderError(RuntimeError):
    """Raised when a provider can't be used (missing key, missing SDK, API error)."""


def _int(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


# Every provider sets `last_usage` per generate() call, the same way it sets
# last_finish_reason: {"input": int, "output": int}, where output includes any
# thinking tokens (they're billed as output). None when the API reported nothing.


class MockProvider:
    """Returns canned-but-brief-aware recipe JSON. No key or SDK required.
    Ignores temperature/max_tokens; never truncates."""
    name = "mock"

    def __init__(self, model=None, temperature=None, max_tokens=None, **kwargs):
        self.model = model or "mock-1"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.last_finish_reason = None  # set per generate() call
        self.last_usage = None

    def generate(self, system_prompt, user_prompt, brief=None, json_mode=True, thinking=None,
                 images=None):
        self.last_finish_reason = "stop"
        if "RECIPE IMPORTER" in system_prompt:  # Phase 34/35: a canned import for dev
            out = json.dumps(_mock_import(user_prompt, len(images or [])))
            self.last_usage = {"input": len(user_prompt) // 4, "output": len(out) // 4}
            return out
        if "RECEIPT READER" in system_prompt:  # Phase 33: a canned read for dev
            out = json.dumps(_mock_receipt(user_prompt, bool(images)))
            self.last_usage = {"input": 1500 if images else len(user_prompt) // 4,
                               "output": len(out) // 4}
            return out
        if not json_mode:  # Phase 27: a plain-text @kitchen answer
            out = ("Good question! (This is the mock provider.) Keep the heat at a "
                   "steady medium and trust your eyes and nose over the timer.")
            # Phase 29: a major-change question gets a CHANGE line, so the
            # "Make this version N" button can be tried in dev.
            q = user_prompt.rsplit("<<<", 1)[-1].lower()
            if any(k in q for k in ("vegetarian", "vegan", "slow cooker", "air fryer", "turn this into", "pasta")):
                out += "\nCHANGE: " + q.split(">>>")[0].strip().rstrip("?").capitalize()
            self.last_usage = {"input": (len(system_prompt) + len(user_prompt)) // 4,
                               "output": len(out) // 4}
            return out
        payload = _mock_payload(brief or {})
        if "REFINEMENT MODE" in system_prompt:  # Phase 26: make refines visible in dev
            payload["recipes"] = payload["recipes"][:1]
            payload["recipes"][0]["title"] = "Refined " + payload["recipes"][0]["title"]
        out = json.dumps(payload)
        # Rough chars/4 estimate so the usage page has numbers to show in dev.
        self.last_usage = {"input": (len(system_prompt) + len(user_prompt)) // 4,
                           "output": len(out) // 4}
        return out


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
        self.last_usage = None

    def generate(self, system_prompt, user_prompt, brief=None, json_mode=True, thinking=None,
                 images=None):
        # json_mode / thinking are Gemini knobs; Anthropic is steered by the prompt.
        # images: [(bytes, mime)] sent ahead of the text (Phase 33).
        self.last_usage = None
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
                messages=[{"role": "user", "content": _anthropic_content(user_prompt, images)}],
            )
        except Exception as e:
            raise ProviderError(f"Anthropic API call failed: {e}") from e
        # "max_tokens" here means the response was cut off — the harness reads this.
        self.last_finish_reason = getattr(resp, "stop_reason", None)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.last_usage = {"input": _int(getattr(usage, "input_tokens", 0)),
                               "output": _int(getattr(usage, "output_tokens", 0))}
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
        self.last_usage = None

    def generate(self, system_prompt, user_prompt, brief=None, json_mode=True, thinking=None,
                 images=None):
        """json_mode=False for plain text (Phase 27). thinking: an optional
        thinking level ("low") to keep short answers fast and cheap; skipped if
        this SDK can't express it, and dropped on retry if the API refuses it.
        images: [(bytes, mime)] sent ahead of the text (Phase 33)."""
        self.last_usage = None
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ProviderError("The 'google-genai' package isn't installed. Run: pip install google-genai") from e
        client = genai.Client(api_key=self.api_key)
        self.last_finish_reason = None
        contents = user_prompt
        if images:
            contents = [types.Part.from_bytes(data=b, mime_type=m) for b, m in images] + [user_prompt]
        cfg = {
            "system_instruction": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        if json_mode:
            cfg["response_mime_type"] = "application/json"  # ask Gemini for clean JSON
        thinking_cfg = None
        if thinking:
            try:
                thinking_cfg = types.ThinkingConfig(thinking_level=thinking)
            except Exception:
                thinking_cfg = None  # older SDK: no thinking levels — just skip it
        try:
            try:
                resp = client.models.generate_content(
                    model=self.model, contents=contents,
                    config=types.GenerateContentConfig(
                        **cfg, **({"thinking_config": thinking_cfg} if thinking_cfg else {})),
                )
            except Exception:
                if thinking_cfg is None:
                    raise
                # The model may not take that thinking level; one plain retry.
                resp = client.models.generate_content(
                    model=self.model, contents=contents,
                    config=types.GenerateContentConfig(**cfg),
                )
        except Exception as e:
            raise ProviderError(f"Gemini API call failed: {e}") from e
        # finish_reason lives on the candidate; defensive in case the shape varies.
        try:
            self.last_finish_reason = resp.candidates[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            self.last_finish_reason = None
        meta = getattr(resp, "usage_metadata", None)
        if meta is not None:
            self.last_usage = {
                "input": _int(getattr(meta, "prompt_token_count", 0)),
                # Thinking tokens are billed at the output rate.
                "output": _int(getattr(meta, "candidates_token_count", 0))
                          + _int(getattr(meta, "thoughts_token_count", 0)),
            }
        return resp.text


def _anthropic_content(text, images):
    if not images:
        return text
    import base64
    blocks = [{"type": "image", "source": {"type": "base64", "media_type": m,
                                           "data": base64.b64encode(b).decode("ascii")}}
              for b, m in images]
    return blocks + [{"type": "text", "text": text}]


# Providers whose models read images (Phase 33). The receipt button is only
# rendered for these; a future text-only provider simply isn't listed (or
# reads an option), so the feature never appears rather than failing.
IMAGE_PROVIDERS = {"mock", "gemini", "anthropic"}


def provider_reads_images(config):
    return (config.get("LLM_PROVIDER") or "mock").lower() in IMAGE_PROVIDERS


def get_provider(config, model=None, max_tokens=None, temperature=None):
    """The configured provider. `model` / `max_tokens` / `temperature` override
    the config per call (Phase 25/27), so a cheaper task can use a smaller
    model, a tighter cap and a calmer temperature."""
    provider = (config.get("LLM_PROVIDER") or "mock").lower()
    common = {
        "model": model or config.get("LLM_MODEL") or None,
        "temperature": (temperature if temperature is not None
                        else config.get("LLM_TEMPERATURE", DEFAULT_TEMPERATURE)),
        "max_tokens": max_tokens or config.get("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
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


def _mock_receipt(user_prompt, from_image):
    """A canned read for dev. A photo: the first three catalogue entries the
    prompt lists (so they match), one food item that isn't in the catalogue
    and one line it can't make out. Pasted lines: each line back as an
    unmatched guess. Proves the plumbing, not the reading."""
    import re
    if not from_image:
        pasted = user_prompt.rsplit("<<<", 1)[-1].split(">>>")[0].strip().splitlines()
        return {"lines": [{"text": ln, "id": None, "guess": ln.lower(), "category": None}
                          for ln in pasted if ln.strip()]}
    ids = re.findall(r"^(\d+): (.+)$", user_prompt, flags=re.M)[:3]
    lines = [{"text": name.upper(), "id": int(i), "guess": name.lower(), "category": None}
             for i, name in ids]
    lines.append({"text": "TSCO DRGN FRT", "id": None, "guess": "dragon fruit", "category": "Fruit"})
    lines.append({"text": "WR SPCL 2PK", "id": None, "guess": None, "category": None})
    return {"lines": lines}


def _mock_import(user_prompt, pages=0):
    """A canned import for dev: with JSON-LD in the prompt, its own name,
    ingredients and steps come back (amounts not split out); photos give a
    fixed recipe titled with the page count (and the "which recipe" hint if
    given); otherwise a fixed recipe. Proves the plumbing, not the reading."""
    if pages:
        hint = user_prompt.split("<<<", 1)[-1].rsplit(">>>", 1)[0].strip() if "<<<" in user_prompt else ""
        return {**_mock_import(""), "title": hint or f"Mock recipe from {pages} photo(s)", "cuisine": None}
    body = user_prompt.split("<<<", 1)[-1].rsplit(">>>", 1)[0]
    try:
        src = json.loads(body)
    except ValueError:
        src = {}
    ings = src.get("recipeIngredient") or ["2 leeks, sliced", "400g chicken thighs", "1 tbsp olive oil"]
    steps = src.get("recipeInstructions") or ["Soften the leeks in the oil.", "Add the chicken and cook through."]
    return {
        "title": src.get("name") or "Mock imported pie",
        "blurb": "An imported recipe (mock provider).",
        "intro": src.get("description") or "",
        "servings": 4, "meal_type": "Dinner", "cuisine": "British", "time_band": "relaxed",
        "ingredients": [{"item": i, "amount": "", "unit": ""} for i in ings],
        "prep": [],
        "cook": [{"title": f"Step {n + 1}", "text": t, "timer_minutes": None} for n, t in enumerate(steps)],
        "tips": [],
    }
