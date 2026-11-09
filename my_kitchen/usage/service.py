"""Model-call accounting (Phase 25): daily limits and cost estimates.

Every model call is a DB row (a Generation today; questions join in Phase 27),
so a limit is just a COUNT over rows. That's correct across both gunicorn
workers with no in-memory state, and needs no new table.

Cost is never stored. Tokens are, and they're priced here at render time from
MODEL_PRICES, so updating a price is a one-line edit. Figures are estimates in
US dollars (the currency Google and Anthropic price in): list prices, with no
caching or free-tier allowance applied.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app

from ..models import Generation

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


def limits_today(user_id):
    """Today's counts against the configured limits, for the wizard and the
    usage page. Failed generations count: they can still have cost tokens."""
    cfg = current_app.config
    start = day_start_utc()
    mine = _generations_since(start, user_id)
    household = _generations_since(start)  # + questions, Phase 27
    gen_limit = int(cfg.get("LIMIT_GENERATIONS_PER_USER_DAY", 10))
    house_limit = int(cfg.get("LIMIT_HOUSEHOLD_CALLS_DAY", 40))
    return {
        "generations": mine, "generations_limit": gen_limit,
        "household": household, "household_limit": house_limit,
        "generations_left": max(0, min(gen_limit - mine, house_limit - household)),
    }


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
    rows = Generation.query.order_by(Generation.created_at.desc()).all()
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

    recent = [{
        "gen": g,
        "kind": "Generate",
        "cost": cost_of(g.model, g.input_tokens, g.output_tokens),
    } for g in rows[:20]]

    return {"periods": periods, "people": people, "recent": recent,
            "limits": limits_today(user_id)}
