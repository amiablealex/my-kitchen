"""Importing a recipe from a web page or pasted text (Phase 34).

    URL  -> fetch -> schema.org Recipe JSON-LD (deterministic) -> one AI pass
    text -> ---------------------------------------------------> one AI pass

The AI pass restructures the source into the app's own contract (intro /
ingredients / prep / cook / tips) without rewriting it: the source's wording,
quantities and method are kept; US measures become metric. The result is
resolved against the catalogue and handed to the create form as a prefill,
so the cook reviews everything before it's saved.

Most recipe sites embed JSON-LD, so only that compact block is sent, not the
page. A page without it falls back to its visible text. Kept apart from
prompt.py: the sealed generation prompt is untouched. Each call is an AiCall
row (kind "import").
"""
import html as html_lib
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from ..extensions import db
from ..models import AiCall, CUISINES, MEAL_TYPE_NAMES
from ..resolver import build_index, resolve_with_index
from ..resolver.aliases import ALIASES
from ..resolver.db import load_catalogue
from .providers import ProviderError, get_provider
from .qa import qa_models
from .schema import extract_json, _normalize_step

FETCH_TIMEOUT = 15            # seconds
FETCH_MAX_BYTES = 3_000_000   # a recipe page with its ads is well under this
TEXT_MAX_CHARS = 12_000       # page text / pasted text sent at most
IMPORT_MAX_TOKENS = 8000
IMPORT_TEMPERATURE = 0.2
USER_AGENT = ("Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")


class ImportProblem(Exception):
    """A calm, user-facing reason the import couldn't go ahead."""


# ---- fetching ------------------------------------------------------------------
def fetch_page(url):
    """(html, final_url). Only http(s); size- and time-capped."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ImportProblem("That doesn't look like a web address. It should start with https://")
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(FETCH_MAX_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            final_url = resp.geturl()
    except urllib.error.HTTPError as e:
        raise ImportProblem(f"The site wouldn't share that page (error {e.code}). "
                            "Paste the recipe's text instead.") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise ImportProblem("Couldn't reach that page. Check the address, or paste the "
                            "recipe's text instead.") from e
    return raw.decode(charset, errors="replace"), final_url


# ---- JSON-LD -------------------------------------------------------------------
_LD_BLOCK = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                       re.I | re.S)


def _is_recipe(node):
    t = node.get("@type") if isinstance(node, dict) else None
    return t == "Recipe" or (isinstance(t, list) and "Recipe" in t)


def _find_recipe(node):
    if isinstance(node, list):
        for n in node:
            hit = _find_recipe(n)
            if hit:
                return hit
    elif isinstance(node, dict):
        if _is_recipe(node):
            return node
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in node:
                hit = _find_recipe(node[key])
                if hit:
                    return hit
    return None


def _text(v):
    if isinstance(v, list):
        return ", ".join(_text(x) for x in v if x)
    if isinstance(v, dict):
        return _text(v.get("name") or v.get("text") or "")
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", str(v or ""))).strip()


def _instructions(v):
    """recipeInstructions in any of its shapes -> a flat list of lines, with
    section names kept as their own lines."""
    out = []
    if isinstance(v, str):
        out += [ln.strip() for ln in re.split(r"\n+", _text(v)) if ln.strip()]
    elif isinstance(v, list):
        for item in v:
            out += _instructions(item)
    elif isinstance(v, dict):
        if v.get("@type") == "HowToSection" or "itemListElement" in v:
            if v.get("name"):
                out.append(f"[{_text(v['name'])}]")
            out += _instructions(v.get("itemListElement") or [])
        else:
            out += _instructions(v.get("text") or v.get("name") or "")
    return out


def extract_recipe_jsonld(page_html):
    """The page's schema.org Recipe, trimmed to what the import needs, or None."""
    for block in _LD_BLOCK.findall(page_html):
        try:
            data = json.loads(block.strip().removeprefix("<!--").removesuffix("-->"), strict=False)
        except ValueError:
            continue
        r = _find_recipe(data)
        if not r or not r.get("recipeIngredient"):
            continue
        slim = {
            "name": _text(r.get("name")),
            "description": _text(r.get("description")),
            "recipeYield": _text(r.get("recipeYield")),
            "prepTime": _text(r.get("prepTime")),
            "cookTime": _text(r.get("cookTime")),
            "totalTime": _text(r.get("totalTime")),
            "recipeCategory": _text(r.get("recipeCategory")),
            "recipeCuisine": _text(r.get("recipeCuisine")),
            "recipeIngredient": [_text(x) for x in r.get("recipeIngredient") or [] if _text(x)],
            "recipeInstructions": _instructions(r.get("recipeInstructions")),
        }
        return {k: v for k, v in slim.items() if v}
    return None


def page_text(page_html):
    """Visible-ish text of a page with no JSON-LD: scripts, styles and page
    furniture dropped, tags to line breaks, capped."""
    s = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|form|aside)\b.*?</\1>", " ", page_html)
    s = re.sub(r"(?i)<br\s*/?>|</(p|li|h[1-6]|div|tr)>", "\n", s)
    s = html_lib.unescape(re.sub(r"<[^>]+>", " ", s))
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)[:TEXT_MAX_CHARS]


# ---- the AI pass -----------------------------------------------------------------
SYSTEM_PROMPT = """You are the RECIPE IMPORTER in a household's recipe app. You are given \
a recipe from a web page (as schema.org data or page text) or pasted by the cook. Put it \
into the app's format WITHOUT rewriting it.

Rules:
- Keep the source's own wording for ingredients, steps and tips as closely as the format \
allows. Don't add steps, ingredients or tips that aren't in the source, and don't drop any.
- Quantities: keep them exactly. Only if the source uses US cups, sticks, ounces, pounds or \
Fahrenheit, convert to metric (g, ml) and Celsius with the fan temperature in brackets, \
rounding sensibly.
- Ingredients: one entry per line. "item" is the ingredient as written, without the amount \
and unit ("garlic cloves, crushed"); "amount" and "unit" as written ("2", "", or "200", "g"). \
Section headings in an ingredient list ("For the sauce") are not ingredients: skip them.
- Method lines in square brackets ("[For the sauce]") are section names, not steps: \
don't make them steps, but let them inform the titles of the steps that follow.
- Split the method into "prep" (getting ingredients ready before any cooking: chopping, \
marinating, preheating) and "cook" (everything from the first heat or mixing for real). If \
the split isn't clear, put everything in "cook". Each step gets a short "title" (two to four \
words) and "text"; "timer_minutes" only when the step states a time.
- "tips": only notes, variations, storage or serving advice that the source itself gives.
- "intro": the source's own description, lightly trimmed, or "" if it has none. "blurb": \
one short sentence saying what the dish is.
- "servings": a whole number from the source's yield (default 4 if it gives none).
- "meal_type" from: {meal_types}. "cuisine" from: {cuisines}, or null if none fits. \
"time_band": "quick" if the whole recipe takes 30 minutes or less, otherwise "relaxed".
- UK English for anything you write yourself.
- If the input isn't a recipe at all, return {{"error": "not_a_recipe"}}.

Return JSON only, in exactly this shape:
{{"title": "", "blurb": "", "intro": "", "servings": 4, "meal_type": "Dinner", \
"cuisine": null, "time_band": "relaxed", \
"ingredients": [{{"item": "", "amount": "", "unit": ""}}], \
"prep": [{{"title": "", "text": "", "timer_minutes": null}}], \
"cook": [{{"title": "", "text": "", "timer_minutes": null}}], \
"tips": [{{"title": "", "text": ""}}]}}"""


def _system_prompt():
    return SYSTEM_PROMPT.format(meal_types=", ".join(MEAL_TYPE_NAMES),
                                cuisines=", ".join(CUISINES))


def build_prompt(source):
    """source: a JSON-LD dict, or text."""
    if isinstance(source, dict):
        head, body = "RECIPE DATA from the web page (JSON):", json.dumps(source, ensure_ascii=False)
    else:
        head, body = "RECIPE TEXT, between the markers:", source[:TEXT_MAX_CHARS]
    body = body.replace("<<<", "").replace(">>>", "")
    return f"{head}\n<<<\n{body}\n>>>"


def _validate(data):
    """The model's JSON -> a clean recipe dict, or ImportProblem."""
    if not isinstance(data, dict) or data.get("error") == "not_a_recipe":
        raise ImportProblem("That doesn't seem to contain a recipe.")
    ings = []
    for e in data.get("ingredients") or []:
        if isinstance(e, dict) and str(e.get("item") or "").strip():
            ings.append({"item": str(e["item"]).strip()[:200],
                         "amount": str(e.get("amount") or "").strip()[:40],
                         "unit": str(e.get("unit") or "").strip()[:40]})

    def steps(key):
        out = []
        for s in data.get(key) or []:
            try:
                out.append(_normalize_step(s))
            except ValueError:
                continue
        return out
    cook = steps("cook")
    title = str(data.get("title") or "").strip()[:200]
    if not (title and ings and (cook or steps("prep"))):
        raise ImportProblem("Couldn't find a full recipe there (a title, ingredients and a method).")
    if not cook:   # all method landed in prep: it's all cooking really
        cook, prep = steps("prep"), []
    else:
        prep = steps("prep")
    try:
        servings = max(1, min(50, int(data.get("servings") or 4)))
    except (TypeError, ValueError):
        servings = 4
    tips = [{"title": str(t.get("title") or "").strip(), "text": str(t.get("text") or "").strip()}
            for t in data.get("tips") or [] if isinstance(t, dict) and str(t.get("text") or "").strip()]
    return {
        "title": title, "blurb": str(data.get("blurb") or "").strip()[:300],
        "intro": str(data.get("intro") or "").strip()[:2000], "servings": servings,
        "meal_type": data.get("meal_type"), "cuisine": data.get("cuisine"),
        "time_band": data.get("time_band") if data.get("time_band") in ("quick", "relaxed") else None,
        "ingredients": ings, "prep": prep, "cook": cook, "tips": tips,
    }


def restructure(cfg, user_id, source):
    """One AI pass (the @kitchen Lite model, falling back to the main model).
    Records an AiCall. Returns a validated recipe dict or raises ImportProblem."""
    prompt = build_prompt(source)
    last_error = None
    for model in qa_models(cfg):
        call = AiCall(user_id=user_id, kind="import", status="error")
        provider = None
        try:
            provider = get_provider(cfg, model=model, max_tokens=IMPORT_MAX_TOKENS,
                                    temperature=IMPORT_TEMPERATURE)
            call.model = f"{provider.name}:{provider.model}"
            text = provider.generate(_system_prompt(), prompt, json_mode=True, thinking="low")
            recipe = _validate(extract_json(text))
            call.status = "done"
            return recipe
        except ImportProblem:
            call.status = "done"     # the call worked; the page just wasn't a recipe
            raise
        except (ProviderError, ValueError) as e:
            last_error = e
        finally:
            usage = (getattr(provider, "last_usage", None) or {}) if provider else {}
            call.input_tokens, call.output_tokens = usage.get("input"), usage.get("output")
            db.session.add(call)
            db.session.commit()
    raise ImportProblem("The recipe couldn't be read just now. Try again in a moment.") from last_error


# ---- the whole import --------------------------------------------------------------
def import_recipe(cfg, user_id, url=None, text=None):
    """(recipe, source_url). recipe is validated and each ingredient carries
    the catalogue link the resolver found (or None). Raises ImportProblem."""
    source_url = None
    if url:
        page, source_url = fetch_page(url.strip())
        source = extract_recipe_jsonld(page) or page_text(page)
        if not source:
            raise ImportProblem("That page had nothing readable. Paste the recipe's text instead.")
    else:
        source = (text or "").strip()
        if len(source) < 40:
            raise ImportProblem("Paste the whole recipe: its ingredients and method.")
    recipe = restructure(cfg, user_id, source)
    index = build_index(load_catalogue(), ALIASES)
    for ing in recipe["ingredients"]:
        res = resolve_with_index(ing["item"], index)
        ing["ingredient_id"], ing["name"] = res.ingredient_id, res.matched_name
    return recipe, source_url
