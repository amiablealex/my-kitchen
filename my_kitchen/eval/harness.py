"""Re-runnable eval harness for the recipe generator (Phase 4b, CP3).

Loops the golden briefs through the configured provider and reports, per brief,
a hard-constraint PASS/FAIL checklist plus the full recipes for eyeballing voice
quality. Saves a timestamped report so prompt iterations can be diffed.

DB-free: briefs are standalone dicts fed to build_user_prompt, so no seeding is
needed. The mock proves the plumbing for free (it's not constraint-aware, so it
WILL fail the allergen/preference asserts — that's expected); the real provider
proves the rules and the voice.
"""
import json
from datetime import datetime
from pathlib import Path

from ..llm.prompt import SYSTEM_PROMPT, build_user_prompt
from ..llm.providers import get_provider, ProviderError
from ..llm.schema import extract_json, validate_and_normalize
from .golden_briefs import GOLDEN_BRIEFS

DEFAULT_EVAL_TEMPERATURE = 0.2  # low on purpose: tight, comparable diffs
OUTPUT_DIR = "eval_runs"


def _is_truncated(finish_reason):
    """True only when the model stopped because it hit the token ceiling.
    Handles Anthropic 'max_tokens', Gemini 'FinishReason.MAX_TOKENS', etc."""
    if finish_reason is None:
        return False
    s = str(finish_reason).lower()
    return "max_token" in s or "length" in s


def _recipe_text_blob(recipe):
    """All human-readable text of a normalised recipe, lowercased, for keyword checks."""
    parts = [recipe.get("title", ""), recipe.get("blurb", ""), recipe.get("intro", "")]
    for ing in recipe.get("ingredients", []):
        parts.append(str(ing.get("item", "")))
        parts.append(str(ing.get("unit", "")))
    for key in ("prep", "cook"):
        for step in recipe.get(key, []):
            parts.append(str(step.get("title", "")))
            parts.append(str(step.get("text", "")))
    for tip in recipe.get("tips", []):
        parts.append(str(tip.get("title", "")))
        parts.append(str(tip.get("text", "")))
    return " ".join(parts).lower()


def _count_to_buy(recipe):
    return sum(1 for ing in recipe.get("ingredients", []) if ing.get("to_buy"))


def _run_checks(parsed, normalized, finish_reason, assertions):
    """Return [(label, passed, detail), ...]. Labels ending '(info)' don't count
    toward the brief's overall pass."""
    checks = []
    max_to_buy = assertions.get("max_to_buy", 2)
    required = [k.lower() for k in assertions.get("required", [])]
    forbidden = [k.lower() for k in assertions.get("forbidden", [])]

    raw_count = len(parsed.get("recipes", [])) if isinstance(parsed, dict) else 0
    checks.append(("exactly two recipes", raw_count == 2, f"got {raw_count}"))

    checks.append(("not truncated", not _is_truncated(finish_reason),
                   f"finish_reason={finish_reason}"))

    blobs = [_recipe_text_blob(r) for r in normalized]

    if required:
        missing = [f"'{kw}' missing from recipe {i + 1}"
                   for kw in required for i, blob in enumerate(blobs) if kw not in blob]
        checks.append(("must-use present in both", not missing, "; ".join(missing) or "ok"))

    if forbidden:
        hits = [f"'{kw}' found in recipe {i + 1}"
                for kw in forbidden for i, blob in enumerate(blobs) if kw in blob]
        checks.append(("no allergen present", not hits, "; ".join(hits) or "ok"))

    over = [f"recipe {i + 1} has {_count_to_buy(r)}"
            for i, r in enumerate(normalized) if _count_to_buy(r) > max_to_buy]
    checks.append((f"<= {max_to_buy} to_buy per recipe", not over, "; ".join(over) or "ok"))

    titles = [r.get("title", "").strip().lower() for r in normalized]
    distinct = len(titles) == 2 and titles[0] != titles[1] and all(titles)
    checks.append(("two distinct titles", distinct,
                   " vs ".join(t or "(blank)" for t in titles)))

    intros_ok = all(r.get("intro", "").strip() for r in normalized)
    checks.append(("intro present (info)", intros_ok,
                   "both" if intros_ok else "one or both blank"))

    return checks


def run_eval(config, provider_name=None, temperature=None, only=None, echo=print):
    """Run the golden briefs. `echo` is the output sink (click.echo from the CLI)."""
    cfg = dict(config)
    if provider_name:
        cfg["LLM_PROVIDER"] = provider_name
    cfg["LLM_TEMPERATURE"] = DEFAULT_EVAL_TEMPERATURE if temperature is None else temperature

    try:
        provider = get_provider(cfg)
    except ProviderError as e:
        echo(f"Could not build provider: {e}")
        return None

    briefs = GOLDEN_BRIEFS
    if only:
        briefs = [b for b in GOLDEN_BRIEFS if b["name"] == only]
        if not briefs:
            echo(f"No golden brief named '{only}'. "
                 f"Known: {', '.join(b['name'] for b in GOLDEN_BRIEFS)}")
            return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = []

    def emit(text=""):
        echo(text)
        lines.append(text)

    emit(f"Recipe eval — provider={provider.name}:{provider.model} "
         f"temp={cfg['LLM_TEMPERATURE']}  {stamp}")
    emit("=" * 72)

    total_pass = 0
    for b in briefs:
        emit("")
        emit(f"### {b['name']}")
        if b.get("note"):
            emit(f"# what good looks like: {b['note']}")

        user_prompt = build_user_prompt(b["brief"])
        try:
            raw = provider.generate(SYSTEM_PROMPT, user_prompt, brief=b["brief"])
        except ProviderError as e:
            emit(f"PROVIDER ERROR: {e}")
            continue
        finish_reason = getattr(provider, "last_finish_reason", None)

        try:
            parsed = extract_json(raw)
            normalized = validate_and_normalize(parsed)
        except ValueError as e:
            emit(f"[FAIL] valid JSON to schema: {e}")
            emit("--- raw response ---")
            emit(raw or "(empty)")
            continue

        emit("[PASS] valid JSON to schema")
        brief_pass = True
        for label, passed, detail in _run_checks(parsed, normalized, finish_reason, b.get("assert", {})):
            if label.endswith("(info)"):
                emit(f"[info] {label}: {detail}")
                continue
            if not passed:
                brief_pass = False
            emit(f"[{'PASS' if passed else 'FAIL'}] {label} — {detail}")

        if brief_pass:
            total_pass += 1

        emit("")
        emit("--- recipes ---")
        for i, r in enumerate(normalized, 1):
            emit(f"-- recipe {i} --")
            emit(json.dumps(r, indent=2, ensure_ascii=False))

    emit("")
    emit("=" * 72)
    emit(f"Hard-constraint pass: {total_pass}/{len(briefs)} briefs")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(OUTPUT_DIR) / f"recipes_eval_{provider.name}_{stamp}.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    echo(f"\nSaved report to {out_path}")
    return out_path
