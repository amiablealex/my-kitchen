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
