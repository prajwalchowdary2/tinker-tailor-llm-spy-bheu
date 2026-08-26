#!/usr/bin/env python3
"""
Reproduce Tables 4-9 (plus the schema-drift and role-assignment
robustness experiments) from the USENIX Security paper.

Runs all evaluation experiments and prints formatted results matching
the paper's table structure.  Each experiment is wrapped in try/except
so partial runs still produce output.

Usage:
    python reproduce_tables.py
"""

import os
import sys
import time

# Ensure imports resolve from the project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HR = "=" * 72


# ---------------------------------------------------------------------------
# Table 4 — Recovery Rates (experiment_recovery)
# ---------------------------------------------------------------------------
def table4_recovery():
    print(f"\n{HR}")
    print("  TABLE 4: Recovery Rates (Precision / Recall / F1)")
    print(HR)

    from evaluation.experiment_recovery import run_experiment
    results = run_experiment()

    print(f"\n{'Platform':<14} {'P':>8} {'R':>8} {'F1':>8} {'Recovered':>10} {'Expected':>10}")
    print("-" * 62)
    for r in results:
        print(f"{r['platform']:<14} {r['precision']:>8.2f} {r['recall']:>8.2f} "
              f"{r['f1']:>8.2f} {r['recovered_count']:>10} {r['expected_count']:>10}")

    avg_p = sum(r["precision"] for r in results) / len(results)
    avg_r = sum(r["recall"] for r in results) / len(results)
    avg_f = sum(r["f1"] for r in results) / len(results)
    print("-" * 62)
    print(f"{'Average':<14} {avg_p:>8.2f} {avg_r:>8.2f} {avg_f:>8.2f}")
    return results


# ---------------------------------------------------------------------------
# Table 5 — Speed Benchmark (experiment_speed)
# ---------------------------------------------------------------------------
def table5_speed():
    print(f"\n{HR}")
    print("  TABLE 5: Infostealer Speed Benchmark (100 trials)")
    print(HR)

    from evaluation.experiment_speed import run_experiment
    results = run_experiment(trials=100)

    print(f"\n{'Platform':<14} {'Mean ms':>9} {'Median':>9} {'p95':>9} "
          f"{'p99':>9} {'EDRs Beaten':>12}")
    print("-" * 66)
    for r in results:
        print(f"{r['platform']:<14} {r['mean_ms']:>9.3f} {r['median_ms']:>9.3f} "
              f"{r['p95_ms']:>9.3f} {r['p99_ms']:>9.3f} "
              f"{r['edr_systems_beaten']:>7}/5")
    return results


# ---------------------------------------------------------------------------
# Table 6 — Tool Comparison (experiment_comparison, synthetic corpus)
# ---------------------------------------------------------------------------
def table6_comparison():
    print(f"\n{HR}")
    print("  TABLE 6: Tool Comparison (Synthetic Corpus)")
    print(HR)

    corpus_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_corpus", "chatgpt_profile", "IndexedDB",
        "https_chatgpt.com_0.indexeddb.leveldb",
    )

    if not os.path.exists(corpus_dir):
        print("  [SKIP] Synthetic corpus not found. Run:")
        print("         python -m evaluation.generate_synthetic_corpus")
        print("         then re-run this script.")
        return None

    from evaluation.experiment_comparison import run_experiment
    results = run_experiment(corpus_dir, "chatgpt")

    print(f"\n{'Tool':<20} {'Prompts':>9} {'Convs':>7} {'Messages':>10} {'Time (s)':>10}")
    print("-" * 60)
    for r in results:
        print(f"{r['tool']:<20} {r['prompts']:>9} {r['conversations']:>7} "
              f"{r['messages']:>10} {r['elapsed_s']:>10.3f}")
    return results


# ---------------------------------------------------------------------------
# Table 7 — Ablation Study (experiment_ablation)
# ---------------------------------------------------------------------------
def table7_ablation():
    print(f"\n{HR}")
    print("  TABLE 7: Ablation Study")
    print(HR)

    from evaluation.experiment_ablation import run_experiment
    results = run_experiment()

    # Summarise by config
    from collections import defaultdict
    by_config = defaultdict(list)
    for r in results:
        by_config[r["config_name"]].append(r)

    print(f"\n{'Config':<25} {'Avg P':>8} {'Avg R':>8} {'Avg F1':>8} {'Cases':>7}")
    print("-" * 60)
    for cfg, rows in by_config.items():
        ap = sum(r["precision"] for r in rows) / len(rows)
        ar = sum(r["recall"] for r in rows) / len(rows)
        af = sum(r["f1"] for r in rows) / len(rows)
        print(f"{cfg:<25} {ap:>8.2f} {ar:>8.2f} {af:>8.2f} {len(rows):>7}")
    return results


# ---------------------------------------------------------------------------
# Table 8 — Unicode Recovery (experiment_unicode)
# ---------------------------------------------------------------------------
def table8_unicode():
    print(f"\n{HR}")
    print("  TABLE 8: Unicode Recovery")
    print(HR)

    from evaluation.experiment_unicode import run_experiment
    results = run_experiment()

    print(f"\n{'Language':<12} {'Encoding':<32} {'Platform':<10} "
          f"{'Jaccard':>8} {'Match':>6}")
    print("-" * 72)
    for r in results:
        match_str = "YES" if r["match"] else "NO"
        print(f"{r['language']:<12} {r['encoding_type']:<32} {r['platform']:<10} "
              f"{r['jaccard_score']:>8.2f} {match_str:>6}")
    return results


# ---------------------------------------------------------------------------
# Table 9 — Corruption Resilience (experiment_corruption)
# ---------------------------------------------------------------------------
def table9_corruption():
    print(f"\n{HR}")
    print("  TABLE 9: Corruption / Truncation Resilience")
    print(HR)

    from evaluation.experiment_corruption import run_experiment
    results = run_experiment()

    # Print summary by type
    from collections import defaultdict
    by_type = defaultdict(list)
    for r in results:
        by_type[r["corruption_type"]].append(r)

    print(f"\n{'Type':<18} {'Trials':>8} {'Avg Recovery %':>16} {'Crashes':>9}")
    print("-" * 55)
    for ct, rows in by_type.items():
        avg = sum(r["recovery_pct"] for r in rows) / len(rows)
        crashes = sum(1 for r in rows if r["crashed"])
        print(f"{ct:<18} {len(rows):>8} {avg:>15.1f}% {crashes:>9}")
    return results


# ---------------------------------------------------------------------------
# Schema-Drift Robustness (experiment_schema_drift)
# ---------------------------------------------------------------------------
def table_schema_drift():
    print(f"\n{HR}")
    print("  SCHEMA-DRIFT ROBUSTNESS: Structured vs. Full-Pipeline Recall")
    print(HR)

    from evaluation.experiment_schema_drift import run_experiment
    results = run_experiment()

    print(f"\n{'Mutation':<42} {'Struct R':>9} {'Full R':>8} {'Path':>10}")
    print("-" * 72)
    for r in results:
        print(f"{r['mutation']:<42} {r['structured_recall']:>9.2f} "
              f"{r['full_recall']:>8.2f} {r['recovering_path']:>10}")
    return results


# ---------------------------------------------------------------------------
# Role-Assignment Robustness (experiment_role_assignment)
# ---------------------------------------------------------------------------
def table_role_assignment():
    print(f"\n{HR}")
    print("  ROLE-ASSIGNMENT ROBUSTNESS: Parity Accuracy by Structure")
    print(HR)

    from evaluation.experiment_role_assignment import run_experiment
    results = run_experiment()

    print(f"\n{'Scenario':<38} {'Turns':>6} {'Correct':>8} {'Accuracy':>9}")
    print("-" * 64)
    for r in results:
        print(f"{r['scenario']:<38} {r['turns']:>6} "
              f"{r['roles_correct']:>8} {r['role_accuracy']:>9.2f}")
    total_c = sum(r["roles_correct"] for r in results)
    total_t = sum(r["turns"] for r in results)
    micro = total_c / total_t if total_t else 0.0
    print("-" * 64)
    print(f"{'micro-avg':<38} {total_t:>6} {total_c:>8} {micro:>9.2f}")
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(HR)
    print("  TINKER TAILOR — Reproducibility Script")
    print("  Reproducing Tables 4-9 + robustness experiments from the paper")
    print(HR)

    t0 = time.time()
    outcomes = {}

    experiments = [
        ("Table 4 — Recovery Rates",       table4_recovery),
        ("Table 5 — Speed Benchmark",       table5_speed),
        ("Table 6 — Tool Comparison",       table6_comparison),
        ("Table 7 — Ablation Study",        table7_ablation),
        ("Table 8 — Unicode Recovery",      table8_unicode),
        ("Table 9 — Corruption Resilience", table9_corruption),
        ("Schema-Drift Robustness",         table_schema_drift),
        ("Role-Assignment Robustness",      table_role_assignment),
    ]

    for label, func in experiments:
        try:
            result = func()
            outcomes[label] = "OK" if result else "SKIPPED"
        except Exception as exc:
            outcomes[label] = f"ERROR: {exc}"
            print(f"\n  [ERROR] {label}: {exc}")

    elapsed = time.time() - t0

    print(f"\n{HR}")
    print("  SUMMARY")
    print(HR)
    for label, status in outcomes.items():
        print(f"  {label:<40} {status}")
    print(f"\n  Total time: {elapsed:.1f}s")
    print(f"  Results written to: results/")
    print(HR)


if __name__ == "__main__":
    main()
