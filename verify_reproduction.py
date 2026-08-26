#!/usr/bin/env python3
"""
Verified reproduction harness for TINKER TAILOR.

Runs every *deterministic, synthetic* experiment (no real browser data, no
wall-clock timings), collects their numeric outputs into a canonical
metrics object, and checks that object against a committed, checksummed
manifest (``results/expected_manifest.json``). This lets a reviewer
confirm, with a single command, that the released pipeline reproduces the
paper's synthetic tables bit-for-bit:

    python verify_reproduction.py            # run + verify against manifest
    python verify_reproduction.py --update   # (re)generate the manifest
    python verify_reproduction.py --figures  # also regenerate paper figures

Exit code is 0 iff every metric matches the manifest (SHA-256 identical).

Covered experiments (all synthetic, deterministic):
  * recovery        (Table: synthetic P/R/F1)
  * ablation        (component ablation P/R/F1)
  * unicode         (per-script recovery)
  * corruption      (seeded truncation / byte-flip / zero-fill)
  * schema_drift    (schema-mutation robustness)
  * role_assignment (role-parity robustness)

Non-deterministic experiments (speed) and those requiring real browser
data (tool comparison, persistence) are intentionally excluded from the
checksum; they cannot be reproduced from the public artifact.
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
MANIFEST_PATH = os.path.join(RESULTS_DIR, "expected_manifest.json")
HR = "=" * 72


def _quiet(fn, *args, **kwargs):
    """Run a noisy experiment function, swallowing its stdout."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Canonical metric collectors — each returns a JSON-serializable object whose
# values are stable across runs and machines.
# ---------------------------------------------------------------------------

def collect_recovery():
    from evaluation.experiment_recovery import run_experiment
    rows = _quiet(run_experiment)
    # case_id contains a random UUID for ChatGPT cases; key by stable
    # ordinal+platform (dataset order is deterministic) instead.
    return {
        f"{i:02d}:{r['platform']}": {"P": r["precision"], "R": r["recall"], "F1": r["f1"]}
        for i, r in enumerate(rows)
    }


def collect_ablation():
    from collections import defaultdict
    from evaluation.experiment_ablation import run_experiment
    rows = _quiet(run_experiment)
    by_cfg = defaultdict(list)
    for r in rows:
        by_cfg[r["config_name"]].append(r)
    out = {}
    for cfg, rs in by_cfg.items():
        n = len(rs)
        out[cfg] = {
            "P": round(sum(r["precision"] for r in rs) / n, 4),
            "R": round(sum(r["recall"] for r in rs) / n, 4),
            "F1": round(sum(r["f1"] for r in rs) / n, 4),
            "cases": n,
        }
    return out


def collect_unicode():
    from evaluation.experiment_unicode import run_experiment
    rows = _quiet(run_experiment)
    return {
        f"{r['language']}|{r['platform']}|{r['encoding_type']}": bool(r["match"])
        for r in rows
    }


def collect_corruption():
    from evaluation.experiment_corruption import run_experiment
    rows = _quiet(run_experiment)
    # deterministic (seeded); key by type+level+trial -> recovered count
    return {
        f"{r['corruption_type']}|{r['corruption_level']}|t{r['trial']}": r["messages_recovered"]
        for r in rows
    }


def collect_schema_drift():
    from evaluation.experiment_schema_drift import run_experiment
    rows = _quiet(run_experiment)
    return {
        r["mutation"]: {
            "struct": r["structured_recall"],
            "full": r["full_recall"],
            "path": r["recovering_path"],
        }
        for r in rows
    }


def collect_role_assignment():
    from evaluation.experiment_role_assignment import run_experiment
    rows = _quiet(run_experiment)
    return {r["scenario"]: r["role_accuracy"] for r in rows}


COLLECTORS = [
    ("recovery", collect_recovery),
    ("ablation", collect_ablation),
    ("unicode", collect_unicode),
    ("corruption", collect_corruption),
    ("schema_drift", collect_schema_drift),
    ("role_assignment", collect_role_assignment),
]


def build_metrics():
    metrics = {}
    for name, fn in COLLECTORS:
        print(f"  running {name} ...", flush=True)
        metrics[name] = fn()
    return metrics


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_of(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Diff helper (per-experiment mismatch reporting)
# ---------------------------------------------------------------------------

def diff_section(name, expected, actual):
    diffs = []
    keys = sorted(set(expected) | set(actual))
    for k in keys:
        e = expected.get(k, "<missing>")
        a = actual.get(k, "<missing>")
        if e != a:
            diffs.append(f"      {k}: expected {e} != got {a}")
    return diffs


def main():
    ap = argparse.ArgumentParser(description="Verified reproduction harness")
    ap.add_argument("--update", action="store_true",
                    help="(re)generate results/expected_manifest.json from this run")
    ap.add_argument("--figures", action="store_true",
                    help="also regenerate paper figures (requires matplotlib)")
    args = ap.parse_args()

    print(HR)
    print("  TINKER TAILOR — Verified Reproduction")
    print(HR)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    metrics = build_metrics()
    digest = sha256_of(metrics)
    print(f"\n  computed SHA-256: {digest}")

    if args.update:
        manifest = {"sha256": digest, "metrics": metrics}
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        print(f"  [WROTE] manifest -> {MANIFEST_PATH}")
        _maybe_figures(args)
        return 0

    if not os.path.exists(MANIFEST_PATH):
        print(f"\n  [ERROR] no manifest at {MANIFEST_PATH}")
        print("          generate it with: python verify_reproduction.py --update")
        return 2

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    expected = manifest.get("metrics", {})
    ok = True
    print(f"\n  {'experiment':<18} {'status':<8} detail")
    print("  " + "-" * 60)
    for name, _ in COLLECTORS:
        exp = expected.get(name, {})
        act = metrics.get(name, {})
        if exp == act:
            print(f"  {name:<18} {'PASS':<8} {len(act)} metrics match")
        else:
            ok = False
            print(f"  {name:<18} {'FAIL':<8} mismatch:")
            for line in diff_section(name, exp, act)[:12]:
                print(line)

    hash_ok = (digest == manifest.get("sha256"))
    print("  " + "-" * 60)
    print(f"  manifest SHA-256 match: {'YES' if hash_ok else 'NO'}")

    _maybe_figures(args)

    print(f"\n{HR}")
    if ok and hash_ok:
        print("  RESULT: PASS — all synthetic metrics reproduce exactly.")
        print(HR)
        return 0
    print("  RESULT: FAIL — see mismatches above.")
    print(HR)
    return 1


def _maybe_figures(args):
    if not args.figures:
        return
    print(f"\n--- regenerating figures ---")
    try:
        import reproduce_figures
        _quiet(reproduce_figures.main)
        print("  figures regenerated into paper/figures/")
    except Exception as exc:
        print(f"  [WARN] figure regeneration skipped: {exc}")


if __name__ == "__main__":
    sys.exit(main())
