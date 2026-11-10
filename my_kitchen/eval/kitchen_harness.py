"""`flask eval-kitchen` (Phase 29): does @kitchen flag the right answers?

"Make this version N" appears under a reply only when the model ends it with a
CHANGE line, and it should do that only for MAJOR changes (ones that need the
recipe rewriting), never for like-for-like swaps or questions about storage,
timing and technique. That's a judgement call by the model, so this runs a
fixed set of questions against one in-memory recipe and checks the flag.

Uses the real QA prompt, model choice and parser (llm/qa.py), and the live
DB's stock, staples and household dietary tags, like a real question. Nothing
is written. Each case is one QA-model call (about ten per run). The mock
provider only checks the plumbing (it flags by keyword), not the judgement.
"""
from ..models import Recipe
from ..llm.providers import ProviderError, get_provider
from ..llm.qa import (QA_MAX_TOKENS, QA_SYSTEM_PROMPT, QA_TEMPERATURE,
                      _clean_answer, build_qa_prompt, qa_models, split_change)

# (question, should_flag). Major = would need a rewritten recipe.
CASES = [
    ("Could I make this vegetarian?", True),
    ("Can I do this in the slow cooker instead?", True),
    ("Could I turn this into a traybake so it all cooks in one tin?", True),
    ("I'd like to make it into a pasta dish. How would that work?", True),
    ("Can I use lemon instead of lime?", False),
    ("Could I use chicken thighs instead of breasts?", False),
    ("I've only got dried thyme. Is that OK?", False),
    ("How long will the leftovers keep in the fridge?", False),
    ("How do I know when the chicken is cooked through?", False),
    ("Can I freeze this?", False),
]


def _recipe():
    """A transient recipe (never added to the session) in the shape the
    prompt reads: the contract JSON comes from ingredients_json and the steps."""
    return Recipe(
        title="Jamaican-Spiced Chicken with Sticky Caramelised Tomatoes",
        blurb="Warm-spiced chicken with jammy cherry tomatoes and crisp green beans.",
        servings=2, source="ai",
        ingredients_json=[
            {"item": "chicken breasts", "amount": "2", "unit": ""},
            {"item": "cherry tomatoes", "amount": "300", "unit": "g"},
            {"item": "green beans", "amount": "150", "unit": "g"},
            {"item": "honey", "amount": "1", "unit": "tbsp"},
            {"item": "soy sauce", "amount": "1", "unit": "tbsp"},
            {"item": "lime, juiced", "amount": "1", "unit": ""},
            {"item": "fresh thyme", "amount": "4", "unit": "sprigs"},
            {"item": "ground allspice", "amount": "1", "unit": "tsp"},
            {"item": "red chilli, sliced", "amount": "1", "unit": ""},
            {"item": "garlic cloves, crushed", "amount": "2", "unit": ""},
        ],
        prep_steps_json=[{"title": "Spice", "text": "Rub the chicken with allspice, thyme leaves, garlic and a pinch of salt."}],
        cook_steps_json=[
            {"title": "Sear", "text": "Fry the chicken in a hot pan for 6-7 minutes a side until golden and cooked through.", "timer_minutes": 14},
            {"title": "Tomatoes", "text": "Add the tomatoes, chilli, honey and soy to the same pan and cook until they blister and turn sticky.", "timer_minutes": 6},
            {"title": "Beans", "text": "Steam the green beans for 4 minutes and finish everything with lime juice.", "timer_minutes": 4},
        ],
        tips_json=[],
    )


def run_kitchen_eval(cfg, provider_name=None, only=None, echo=print):
    cfg = dict(cfg)
    if provider_name:
        cfg["LLM_PROVIDER"] = provider_name
    recipe = _recipe()
    cases = [c for c in CASES if not only or only.lower() in c[0].lower()]
    models = qa_models(cfg)
    echo(f"eval-kitchen: {len(cases)} case(s), provider={cfg.get('LLM_PROVIDER') or 'mock'}, model={models[0]}")
    echo("")
    passed = 0
    for question, want in cases:
        prompt = build_qa_prompt(recipe, question)
        text, err = None, None
        for model in models:
            try:
                p = get_provider(cfg, model=model, max_tokens=QA_MAX_TOKENS, temperature=QA_TEMPERATURE)
                text = p.generate(QA_SYSTEM_PROMPT, prompt, json_mode=False, thinking="low")
                break
            except ProviderError as e:
                err = e
        if text is None:
            echo(f"ERROR  {question}\n       {err}")
            continue
        body, change = split_change(text)
        got = change is not None
        ok = got == want
        passed += ok
        mark = "PASS" if ok else "FAIL"
        want_s = "flag" if want else "no flag"
        echo(f"{mark}   [{want_s:>7}]  {question}")
        if change:
            echo(f"         CHANGE: {change}")
        if not ok:
            echo("         answer: " + _clean_answer(body).replace("\n", " ")[:220])
    echo("")
    echo(f"{passed}/{len(cases)} passed")
    return passed == len(cases)
