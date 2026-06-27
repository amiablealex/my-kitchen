"""Re-runnable resolver eval (``flask resolve-eval``), the permanent
resolver-regression tool. Mirrors ``harness.py`` but is a PURE-FUNCTION eval —
no provider, no network, no DB. Runs every golden free-text through the resolver
against an INJECTED fixture catalogue and reports:

  * match rate (correct / total)
  * FALSE-LINK count — the metric that matters: a wrong, non-null link. MUST be 0
    on traps and negatives.
  * MISS count — unmatched where a match was expected (degrades gracefully).
  * per-method breakdown (exact / alias / fuzzy / unmatched)
  * a line for every disagreement (expected vs got, with method + score)
  * a dedicated TRAPS block (the hard gate) and a negatives best-fuzzy view to
    aid threshold tuning.

A run is a PASS only when every trap holds, every negative is unmatched, and
there are zero false links anywhere.
"""
from datetime import datetime
from pathlib import Path

from ..resolver.core import build_index, resolve_with_index, best_fuzzy, FUZZY_THRESHOLD
from .golden_ingredients import fixture_catalogue, POSITIVES, NEGATIVES, TRAPS

OUTPUT_DIR = "eval_runs"


def run_resolver_eval(threshold=None, echo=print):
    th = FUZZY_THRESHOLD if threshold is None else float(threshold)
    index = build_index(fixture_catalogue(), _aliases())

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = []

    def emit(text=""):
        echo(text)
        lines.append(text)

    emit(f"Resolver eval — token_set_ratio  threshold={th}  {stamp}")
    emit("=" * 72)

    method_counts = {"exact": 0, "alias": 0, "fuzzy": 0, "unmatched": 0}
    correct = false_links = misses = 0
    disagreements = []
    trap_rows = []

    def record_method(r):
        method_counts[r.method] = method_counts.get(r.method, 0) + 1

    # --- positives ---
    emit("\n--- POSITIVES (expect a match) ---")
    for text, expected in POSITIVES:
        r = resolve_with_index(text, index, th)
        record_method(r)
        got = r.matched_name
        if got == expected:
            correct += 1
        elif got is None:
            misses += 1
            disagreements.append(("POS-MISS", text, expected, got, r))
        else:
            false_links += 1
            disagreements.append(("POS-FALSELINK", text, expected, got, r))
        flag = "ok " if got == expected else ("MISS" if got is None else "FALSE-LINK")
        emit(f"  [{flag:10s}] {text!r:42s} -> {got!r}  ({r.method}, {r.score:.0f})")

    # --- negatives ---
    emit("\n--- NEGATIVES (expect unmatched) ---")
    for text, _ in NEGATIVES:
        r = resolve_with_index(text, index, th)
        record_method(r)
        got = r.matched_name
        if got is None:
            correct += 1
        else:
            false_links += 1
            disagreements.append(("NEG-FALSELINK", text, None, got, r))
        cand, cscore = best_fuzzy(text, index)
        flag = "ok " if got is None else "FALSE-LINK"
        emit(f"  [{flag:10s}] {text!r:42s} -> {got!r}  "
             f"(best fuzzy: {cand!r} {cscore:.0f}, cut {th:.0f})")

    # --- traps ---
    emit("\n--- PRECISION TRAPS (hard gate — every one must hold) ---")
    for text, must_be, must_not in TRAPS:
        r = resolve_with_index(text, index, th)
        record_method(r)
        got = r.matched_name
        if got == must_be:
            correct += 1
            ok = True
        else:
            ok = False
            if got in must_not:
                false_links += 1
                disagreements.append(("TRAP-FALSELINK", text, must_be, got, r))
            elif got is None:
                misses += 1
                disagreements.append(("TRAP-MISS", text, must_be, got, r))
            else:
                false_links += 1
                disagreements.append(("TRAP-WRONG", text, must_be, got, r))
        trap_rows.append((ok, text, must_be, got))
        flag = "ok " if ok else ("WRONG-LINK!" if got in must_not else
                                 ("miss" if got is None else "wrong"))
        emit(f"  [{flag:11s}] {text!r:30s} -> {got!r}   "
             f"(want {must_be!r}, never {must_not}) [{r.method} {r.score:.0f}]")

    total = len(POSITIVES) + len(NEGATIVES) + len(TRAPS)

    emit("\n" + "=" * 72)
    emit(f"match rate     : {correct}/{total} = {100.0 * correct / total:.1f}%")
    emit(f"FALSE LINKS    : {false_links}   <-- must be 0")
    emit(f"misses         : {misses}")
    emit(f"per-method     : " + "  ".join(f"{k}={v}" for k, v in method_counts.items()))
    traps_ok = all(ok for ok, *_ in trap_rows)
    negs_ok = all(d[0] != "NEG-FALSELINK" for d in disagreements)
    overall = (false_links == 0) and traps_ok and negs_ok
    emit(f"traps          : {sum(1 for ok, *_ in trap_rows if ok)}/{len(TRAPS)} hold")
    emit(f"OVERALL        : {'PASS' if overall else 'FAIL'}")

    if disagreements:
        emit("\n--- disagreements (expected vs got) ---")
        for kind, text, expected, got, r in disagreements:
            emit(f"  [{kind}] {text!r}: expected {expected!r}, got {got!r} "
                 f"({r.method}, {r.score:.0f})")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(OUTPUT_DIR) / f"resolver_eval_{stamp}.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    echo(f"\nSaved report to {out_path}")
    return overall


def _aliases():
    """Import the curated alias constant. Kept in a helper so the harness module
    imports cleanly even if someone runs it before the resolver package is on the
    path."""
    from ..resolver.aliases import ALIASES
    return ALIASES


if __name__ == "__main__":
    # DB-free entry point (mirrors render_prompts.py): runs with no Flask app, no
    # app context, no DB, no network —
    #     python -m my_kitchen.eval.resolver_harness
    import sys
    ok = run_resolver_eval(echo=print)
    sys.exit(0 if ok else 1)
