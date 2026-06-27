"""Deterministic free-text -> catalogue ingredient resolver (Phase 3a).

No LLM call. The pure core (``core.py``) is DB-free: catalogue + aliases are
INJECTED, so it runs without an app/DB context — exactly like the prompt eval.
``db.py`` is a thin, DORMANT wrapper that loads the live catalogue for 3b; it is
not called anywhere in 3a. The resolver's only consumer this phase is the eval
harness (``flask resolve-eval``).
"""
from .core import (
    ResolveResult,
    UNMATCHED,
    Index,
    resolve,
    resolve_with_index,
    build_index,
    norm_min,
    norm_core,
)

__all__ = [
    "ResolveResult", "UNMATCHED", "Index",
    "resolve", "resolve_with_index", "build_index",
    "norm_min", "norm_core",
]
