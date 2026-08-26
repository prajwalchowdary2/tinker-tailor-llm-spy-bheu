#!/usr/bin/env python3
"""
Reproduce all figures from the USENIX Security paper.

Runs generate_paper_figures.py (Figures 1-7) and
generate_extra_figures.py (supplementary figures), printing
which figures were generated and where they were saved.

Usage:
    python reproduce_figures.py

Requires: matplotlib, numpy  (pip install -r requirements.txt)
"""

import os
import sys
import time

# Ensure imports resolve from the project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HR = "=" * 72
FIGURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper", "figures")


def list_figures_before():
    """Return set of existing figure files."""
    if not os.path.isdir(FIGURE_DIR):
        return set()
    return set(os.listdir(FIGURE_DIR))


def main():
    print(HR)
    print("  TINKER TAILOR — Figure Reproduction")
    print(HR)

    t0 = time.time()
    results = {}

    # ------------------------------------------------------------------
    # Paper figures (Figures 1-7)
    # ------------------------------------------------------------------
    print(f"\n--- Paper Figures (generate_paper_figures.py) ---\n")
    before = list_figures_before()
    try:
        from evaluation.generate_paper_figures import (
            fig1_architecture,
            fig2_tool_comparison,
            fig3_speed_benchmark,
            fig4_recovery_rates,
            fig5_profile_breakdown,
            fig6_data_flow,
            fig7_v8_format,
        )

        figure_funcs = [
            ("Figure 1: Pipeline Architecture",        fig1_architecture),
            ("Figure 2: Tool Comparison",              fig2_tool_comparison),
            ("Figure 3: Speed vs EDR Detection",       fig3_speed_benchmark),
            ("Figure 4: Recovery Rates",               fig4_recovery_rates),
            ("Figure 5: Profile Breakdown",            fig5_profile_breakdown),
            ("Figure 6: Deletion Persistence Flow",    fig6_data_flow),
            ("Figure 7: V8 Serialization Format",      fig7_v8_format),
        ]

        for label, func in figure_funcs:
            try:
                func()
                results[label] = "OK"
            except Exception as exc:
                results[label] = f"ERROR: {exc}"
                print(f"  [ERROR] {label}: {exc}")

    except ImportError as exc:
        msg = f"Import error: {exc}. Install matplotlib: pip install -r requirements.txt"
        print(f"  [ERROR] {msg}")
        for i in range(1, 8):
            results[f"Figure {i}"] = msg

    # ------------------------------------------------------------------
    # Extra / supplementary figures
    # ------------------------------------------------------------------
    print(f"\n--- Extra Figures (generate_extra_figures.py) ---\n")
    try:
        from evaluation.generate_extra_figures import (
            fig_prompt_length_distribution,
            fig_data_source,
            fig_leveldb_storage,
            fig_realworld_speed,
        )

        extra_funcs = [
            ("Extra: Prompt Length Distribution",   fig_prompt_length_distribution),
            ("Extra: WAL vs SSTable Source",        fig_data_source),
            ("Extra: LevelDB Storage by Profile",  fig_leveldb_storage),
            ("Extra: Real-world Speed",            fig_realworld_speed),
        ]

        for label, func in extra_funcs:
            try:
                func()
                results[label] = "OK"
            except Exception as exc:
                results[label] = f"ERROR: {exc}"
                print(f"  [ERROR] {label}: {exc}")

    except ImportError as exc:
        msg = f"Import error: {exc}"
        print(f"  [ERROR] {msg}")
        for name in ["Prompt Length", "Data Source", "LevelDB Storage", "Real-world Speed"]:
            results[f"Extra: {name}"] = msg

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    after = list_figures_before()
    new_files = after - before
    elapsed = time.time() - t0

    print(f"\n{HR}")
    print("  SUMMARY")
    print(HR)
    for label, status in results.items():
        print(f"  {label:<42} {status}")

    print(f"\n  Output directory: {FIGURE_DIR}/")
    if new_files:
        print(f"  New/updated files: {len(new_files)}")
        for f in sorted(new_files):
            print(f"    - {f}")
    else:
        print(f"  Total figure files: {len(after)}")

    print(f"  Time: {elapsed:.1f}s")
    print(HR)


if __name__ == "__main__":
    main()
