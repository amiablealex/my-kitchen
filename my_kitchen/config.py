import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # --- Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # CSRF tokens are session-scoped with no separate time expiry, so a stock
    # page left open on the kitchen tablet doesn't start rejecting toggles after
    # an hour. Token is still bound to the session (cleared on logout/restart).
    WTF_CSRF_TIME_LIMIT = None
    # Flask-WTF enforces a strict Referer-vs-Host check on HTTPS POSTs
    # (WTF_CSRF_SSL_STRICT, default True). Behind HA ingress via the Nabu Casa
    # cloud relay the app doesn't see the public host as its own, so that check
    # rejects logins ("form expired") even though the CSRF token is valid. The
    # token-based protection (session token vs form token) is unaffected and
    # stays active, so this only drops a redundant layer — fine for an app that
    # already sits behind HA's auth + ingress.
    WTF_CSRF_SSL_STRICT = False

    # --- Database (path configurable for the Pi / HA add-on later) ---
    _db_path = os.environ.get("MY_KITCHEN_DB_PATH", str(BASE_DIR / "my_kitchen.db"))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{_db_path}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Network ---
    HOST = os.environ.get("MY_KITCHEN_HOST", "0.0.0.0")
    PORT = int(os.environ.get("MY_KITCHEN_PORT", "8000"))

    # IANA timezone for displaying stored UTC timestamps locally (zoneinfo handles BST).
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Europe/London")

    # --- LLM provider adapter (built out in Checkpoint 5) ---
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")  # mock | anthropic | gemini
    LLM_MODEL = os.environ.get("LLM_MODEL", "")            # blank -> provider default
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # Anti-repetition (wired in a later phase)
    LLM_RECENT_TITLES_N = int(os.environ.get("LLM_RECENT_TITLES_N", "10"))

    # Generation tuning (Phase 4b). Temperature kept moderate on purpose: variety
    # comes from the creative seed + anti-repetition (§5.3), not from cranking heat.
    LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.8"))
    # The richer intro/steps/tips output is longer — give it headroom so a good
    # response isn't truncated mid-recipe.
    LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4000"))

    # Model-call limits (Phase 25), counted per local calendar day. Generous
    # enough never to bite on a normal evening; there to stop a runaway (a bug,
    # or repeated taps) at a known ceiling. See usage/service.py.
    LIMIT_GENERATIONS_PER_USER_DAY = int(os.environ.get("LIMIT_GENERATIONS_PER_USER_DAY", "10"))
    LIMIT_HOUSEHOLD_CALLS_DAY = int(os.environ.get("LIMIT_HOUSEHOLD_CALLS_DAY", "40"))
    # "Neither — try again" rounds allowed from one brief (Phase 26).
    LIMIT_REGENERATES_PER_BRIEF = int(os.environ.get("LIMIT_REGENERATES_PER_BRIEF", "3"))
    # @kitchen questions per person per day (Phase 27); they also count
    # towards LIMIT_HOUSEHOLD_CALLS_DAY.
    LIMIT_QUESTIONS_PER_USER_DAY = int(os.environ.get("LIMIT_QUESTIONS_PER_USER_DAY", "20"))
    # Model for @kitchen answers. Blank -> the provider's Lite default
    # (gemini-3.5-flash-lite), falling back to LLM_MODEL if that's refused.
    LLM_QA_MODEL = os.environ.get("LLM_QA_MODEL", "")
    # Receipt scanning (Phase 33). Off -> the receipt button never renders and
    # the route 404s. The household-wide switch for anyone who'd rather not
    # send receipt photos to an AI provider.
    RECEIPT_SCANNING = os.environ.get("RECEIPT_SCANNING", "true").lower() in ("1", "true", "yes", "on")
    # Receipt reads + AI matching of pasted list lines, per person per day.
    # Both also count towards LIMIT_HOUSEHOLD_CALLS_DAY.
    LIMIT_RECEIPT_READS_PER_USER_DAY = int(os.environ.get("LIMIT_RECEIPT_READS_PER_USER_DAY", "10"))
    # A receipt photo is cropped and shrunk in the browser first; this is only
    # a backstop against something odd arriving.
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
