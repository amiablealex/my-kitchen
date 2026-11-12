"""Model-call accounting (Phase 25): daily limits and cost estimates.

Every model call is a DB row (a Generation; a question since Phase 27; an
AiCall for receipt reads and list matches since Phase 33), so a limit is just
a COUNT over rows. That's correct across both gunicorn
workers with no in-memory state, and needs no new table.

Cost is never stored. Tokens are, and they're priced here at render time from
MODEL_PRICES, so updating a price is a one-line edit. Figures are estimates in
US dollars (the currency Google and Anthropic price in): list prices, with no
caching or free-tier allowance applied.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app

from ..models import AiCall, Generation, RecipeComment

# USD per 1M tokens: (input, output). Keyed by model id without the provider
# prefix stored on generations.model ("gemini:gemini-3.5-flash"). A model not
# listed shows its tokens but no cost. Checked Nov 2026 — re-check against
# https://ai.google.dev/gemini-api/docs/pricing when changing model.
MODEL_PRICES = {
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "claude-sonnet-4-6": (3.00, 15.00),
    "mock-1": (0.0, 0.0),
}


KIND_LABELS = {None: "Generate", "generate": "Generate",
               "regenerate": "Try again", "refine": "Refine", "question": "Question",
               "receipt": "Receipt", "match": "List match", "import": "Import"}


def model_id(stored):
    """'gemini:gemini-3.5-flash' -> 'gemini-3.5-flash'."""
    return (stored or "").split(":", 1)[-1] or None


def cost_of(model, input_tokens, output_tokens):
    """Estimated USD for one call, or None when it can't be priced (tokens not
    tracked, or the model isn't in MODEL_PRICES)."""
    if input_tokens is None and output_tokens is None:
        return None
    price = MODEL_PRICES.get(model_id(model))
    if price is None:
        return None
    return ((input_tokens or 0) * price[0] + (output_tokens or 0) * price[1]) / 1_000_000


def day_start_utc():
    """Local midnight (APP_TIMEZONE) as a naive UTC datetime — the form SQLite
    hands created_at back in — so "today" matches the household's clock."""
    tz = ZoneInfo(current_app.config.get("APP_TIMEZONE", "Europe/London"))
    local_midnight = datetime.combine(datetime.now(tz).date(), time.min, tzinfo=tz)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def naive_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generations_since(since, user_id=None):
    q = Generation.query.filter(Generation.created_at >= since)
    if user_id is not None:
        q = q.filter(Generation.created_by_user_id == user_id)
    return q.count()


def _questions_since(since, user_id=None):
    q = RecipeComment.query.filter(RecipeComment.kind == "question",
                                   RecipeComment.created_at >= since)
    if user_id is not None:
        q = q.filter(RecipeComment.user_id == user_id)
    return q.count()


# The kinds that count towards the per-person receipt/list limit. Imports
# (Phase 34) are rarer and deliberate, so they only count for the household.
READ_KINDS = ("receipt", "match")


def _ai_calls_since(since, user_id=None, kinds=None):
    q = AiCall.query.filter(AiCall.created_at >= since)
    if user_id is not None:
        q = q.filter(AiCall.user_id == user_id)
    if kinds:
        q = q.filter(AiCall.kind.in_(kinds))
    return q.count()


def limits_today(user_id):
    """Today's counts against the configured limits, for the wizard and the
    usage page. Failed generations count: they can still have cost tokens."""
    cfg = current_app.config
    start = day_start_utc()
    mine = _generations_since(start, user_id)
    my_questions = _questions_since(start, user_id)
    my_reads = _ai_calls_since(start, user_id, kinds=READ_KINDS)
    household = _generations_since(start) + _questions_since(start) + _ai_calls_since(start)
    gen_limit = int(cfg.get("LIMIT_GENERATIONS_PER_USER_DAY", 10))
    q_limit = int(cfg.get("LIMIT_QUESTIONS_PER_USER_DAY", 20))
    house_limit = int(cfg.get("LIMIT_HOUSEHOLD_CALLS_DAY", 40))
    read_limit = int(cfg.get("LIMIT_RECEIPT_READS_PER_USER_DAY", 10))
    return {
        "generations": mine, "generations_limit": gen_limit,
        "questions": my_questions, "questions_limit": q_limit,
        "household": household, "household_limit": house_limit,
        "generations_left": max(0, min(gen_limit - mine, house_limit - household)),
        "questions_left": max(0, min(q_limit - my_questions, house_limit - household)),
        "reads": my_reads, "reads_limit": read_limit,
        "reads_left": max(0, min(read_limit - my_reads, house_limit - household)),
    }


def question_blocked_reason(user_id):
    """None if this user may ask @kitchen now, else a calm explanation."""
    lim = limits_today(user_id)
    if lim["questions"] >= lim["questions_limit"]:
        return (f"You've asked all {lim['questions_limit']} of today's @kitchen "
                "questions. It resets at midnight — your note wasn't posted.")
    if lim["household"] >= lim["household_limit"]:
        return (f"The household has reached today's limit of "
                f"{lim['household_limit']} AI calls, so @kitchen can't answer until "
                "midnight — your note wasn't posted.")
    return None


def generation_blocked_reason(user_id):
    """None if this user may start a generation now, else a calm explanation."""
    lim = limits_today(user_id)
    if lim["generations"] >= lim["generations_limit"]:
        return (f"You've used all {lim['generations_limit']} of today's recipe "
                "generations. Your saved recipes are still here, and the count "
                "resets at midnight.")
    if lim["household"] >= lim["household_limit"]:
        return (f"The household has reached today's limit of "
                f"{lim['household_limit']} AI calls. It resets at midnight.")
    return None


def read_blocked_reason(user_id):
    """None if this user may have a receipt or list read now, else a calm
    explanation (Phase 33)."""
    lim = limits_today(user_id)
    if lim["reads"] >= lim["reads_limit"]:
        return (f"You've used all {lim['reads_limit']} of today's receipt reads. "
                "You can still paste or type a list, and the count resets at midnight.")
    if lim["household"] >= lim["household_limit"]:
        return (f"The household has reached today's limit of {lim['household_limit']} "
                "AI calls. You can still paste or type a list; it resets at midnight.")
    return None


def import_blocked_reason(user_id):
    """None if a recipe import may run now (Phase 34): only the household
    cap applies."""
    lim = limits_today(user_id)
    if lim["household"] >= lim["household_limit"]:
        return (f"The household has reached today's limit of {lim['household_limit']} "
                "AI calls, so importing will have to wait until midnight.")
    return None


class _QuestionCall:
    """A question row seen through the attributes the summaries read off a
    Generation, so both kinds of call share one code path."""
    kind = "question"

    def __init__(self, c):
        self.c = c
        self.created_at = c.created_at
        self.created_by = c.author
        self.model = c.model
        self.input_tokens = c.input_tokens
        self.output_tokens = c.output_tokens
        self.status = {"pending": "running", "error": "error"}.get(c.answer_status, "done")


def _summarise(rows):
    out = {"calls": 0, "failed": 0, "input": 0, "output": 0, "cost": 0.0, "unpriced": 0}
    for g in rows:
        out["calls"] += 1
        if (g.status or "done") == "error":
            out["failed"] += 1
        out["input"] += g.input_tokens or 0
        out["output"] += g.output_tokens or 0
        c = cost_of(g.model, g.input_tokens, g.output_tokens)
        if c is None:
            out["unpriced"] += 1
        else:
            out["cost"] += c
    return out


def dashboard(user_id):
    """Everything the /usage page shows. Household scale: one pass in Python
    over all generations is cheaper to read than a pile of GROUP BYs."""
    rows = Generation.query.all() + [
        _QuestionCall(c) for c in RecipeComment.query.filter(RecipeComment.kind == "question")
    ] + AiCall.query.all()   # an AiCall already has the attributes the summaries read
    rows.sort(key=lambda g: g.created_at or datetime.min, reverse=True)
    now = naive_utc_now()
    today = day_start_utc()

    def since(t):
        return [g for g in rows if g.created_at and g.created_at >= t]

    periods = [
        ("Today", _summarise(since(today))),
        ("Last 7 days", _summarise(since(now - timedelta(days=7)))),
        ("Last 30 days", _summarise(since(now - timedelta(days=30)))),
        ("All time", _summarise(rows)),
    ]

    by_person = {}
    for g in since(now - timedelta(days=30)):
        name = g.created_by.name if g.created_by else "unknown"
        by_person.setdefault(name, []).append(g)
    people = sorted(((n, _summarise(gs)) for n, gs in by_person.items()),
                    key=lambda kv: -kv[1]["calls"])

    by_kind = {}
    for g in since(now - timedelta(days=30)):
        by_kind.setdefault(KIND_LABELS.get(g.kind, "Generate"), []).append(g)
    kinds = [(k, _summarise(gs)) for k, gs in sorted(by_kind.items(), key=lambda kv: -len(kv[1]))]

    recent = [{
        "gen": g,
        "kind": KIND_LABELS.get(g.kind, "Generate"),
        "cost": cost_of(g.model, g.input_tokens, g.output_tokens),
    } for g in rows[:20]]

    return {"periods": periods, "people": people, "kinds": kinds, "recent": recent,
            "limits": limits_today(user_id)}
