"""
Figure Generator for USENIX Paper

Reads experiment CSV results and generates publication-quality
matplotlib figures for the paper.

Usage:
    python -m evaluation.generate_figures

Output:
    paper/figures/*.pdf
"""

import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[!] matplotlib not installed. Install with: pip install matplotlib")
    print("    Generating placeholder text files instead.\n")


FIGURE_DIR = "paper/figures"


def _ensure_dir():
    os.makedirs(FIGURE_DIR, exist_ok=True)


def generate_recovery_rates():
    """Fig 2: Recovery rate bar chart (precision/recall per platform)."""
    _ensure_dir()
    csv_path = "results/recovery_rates.csv"
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_path} not found — run experiment_recovery first")
        return

    rows = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    platforms = defaultdict(lambda: {"precision": [], "recall": [], "f1": []})
    for row in rows:
        p = row["platform"]
        platforms[p]["precision"].append(float(row["precision"]))
        platforms[p]["recall"].append(float(row["recall"]))
        platforms[p]["f1"].append(float(row["f1"]))

    if not HAS_MATPLOTLIB:
        with open(os.path.join(FIGURE_DIR, "fig2_recovery_rates.txt"), 'w') as f:
            for p, metrics in platforms.items():
                avg_p = sum(metrics["precision"]) / len(metrics["precision"])
                avg_r = sum(metrics["recall"]) / len(metrics["recall"])
                avg_f1 = sum(metrics["f1"]) / len(metrics["f1"])
                f.write(f"{p}: P={avg_p:.2f} R={avg_r:.2f} F1={avg_f1:.2f}\n")
        print("  [OK] fig2_recovery_rates.txt (placeholder)")
        return

    names = list(platforms.keys())
    avg_p = [sum(platforms[n]["precision"]) / len(platforms[n]["precision"]) for n in names]
    avg_r = [sum(platforms[n]["recall"]) / len(platforms[n]["recall"]) for n in names]
    avg_f1 = [sum(platforms[n]["f1"]) / len(platforms[n]["f1"]) for n in names]

    x = range(len(names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - width for i in x], avg_p, width, label='Precision', color='#2196F3')
    ax.bar(x, avg_r, width, label='Recall', color='#4CAF50')
    ax.bar([i + width for i in x], avg_f1, width, label='F1', color='#FF9800')

    ax.set_ylabel('Score')
    ax.set_xticks(x)
    ax.set_xticklabels([n.capitalize() for n in names])
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.set_title('Recovery Rates by Platform')

    plt.tight_layout()
    out_path = os.path.join(FIGURE_DIR, "fig2_recovery_rates.pdf")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {out_path}")


def generate_speed_benchmark():
    """Fig 3: Speed benchmark histogram + EDR threshold lines."""
    _ensure_dir()
    csv_path = "results/speed_benchmark.csv"
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_path} not found — run experiment_speed first")
        return

    rows = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    if not HAS_MATPLOTLIB:
        with open(os.path.join(FIGURE_DIR, "fig3_speed_benchmark.txt"), 'w') as f:
            for row in rows:
                f.write(f"{row['platform']}: mean={row['mean_ms']}ms p99={row['p99_ms']}ms\n")
        print("  [OK] fig3_speed_benchmark.txt (placeholder)")
        return

    fig, ax = plt.subplots(figsize=(8, 4))

    platforms = [row["platform"] for row in rows]
    means = [float(row["mean_ms"]) for row in rows]
    p99s = [float(row["p99_ms"]) for row in rows]

    x = range(len(platforms))
    ax.bar(x, means, color='#2196F3', alpha=0.8, label='Mean')
    ax.bar(x, [p - m for p, m in zip(p99s, means)], bottom=means, color='#FF9800', alpha=0.6, label='p99')

    edr_colors = ['#E91E63', '#9C27B0', '#00BCD4', '#795548', '#607D8B']
    edr_items = sorted(
        [("CrowdStrike Falcon", 250), ("Microsoft Defender", 500),
         ("SentinelOne", 300), ("Carbon Black", 1000), ("Elastic Security", 750)],
        key=lambda x: x[1],
    )
    for (name, window), color in zip(edr_items, edr_colors):
        ax.axhline(y=window, color=color, linestyle='--', alpha=0.7, label=f'{name} ({window}ms)')

    ax.set_ylabel('Time (ms)')
    ax.set_xticks(x)
    ax.set_xticklabels([p.capitalize() for p in platforms])
    ax.legend(fontsize=7, loc='upper right')
    ax.set_title('Carving Speed vs EDR Detection Windows')

    plt.tight_layout()
    out_path = os.path.join(FIGURE_DIR, "fig3_speed_benchmark.pdf")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {out_path}")


def generate_persistence_timeline():
    """Fig 1: Persistence decay curve (messages recoverable vs time since deletion)."""
    _ensure_dir()
    csv_path = "results/persistence_timeline.csv"
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_path} not found — run experiment_persistence first")
        return

    rows = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    if not rows:
        print(f"  [SKIP] {csv_path} is empty")
        return

    if not HAS_MATPLOTLIB:
        with open(os.path.join(FIGURE_DIR, "fig1_persistence.txt"), 'w') as f:
            for row in rows:
                f.write(f"{row['timestamp']}: {row['messages_recovered']} msgs\n")
        print("  [OK] fig1_persistence.txt (placeholder)")
        return

    epochs = [float(row["epoch"]) for row in rows]
    messages = [int(row["messages_recovered"]) for row in rows]

    t0 = min(epochs)
    hours = [(e - t0) / 3600 for e in epochs]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hours, messages, 'o-', color='#E91E63', markersize=3)
    ax.set_xlabel('Hours Since First Snapshot')
    ax.set_ylabel('Messages Recoverable')
    ax.set_title('Data Persistence After Deletion')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(FIGURE_DIR, "fig1_persistence.pdf")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {out_path}")


def generate_tool_comparison():
    """Fig 4: Tool comparison bar chart."""
    _ensure_dir()
    csv_path = "results/tool_comparison.csv"
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_path} not found — run experiment_comparison first")
        return

    rows = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    if not HAS_MATPLOTLIB:
        with open(os.path.join(FIGURE_DIR, "fig4_tool_comparison.txt"), 'w') as f:
            for row in rows:
                f.write(f"{row['tool']}: {row['prompts']} prompts, {row['conversations']} convs\n")
        print("  [OK] fig4_tool_comparison.txt (placeholder)")
        return

    tools = [row["tool"] for row in rows]
    prompts = [int(row["prompts"]) for row in rows]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['#4CAF50', '#FF9800', '#2196F3']
    ax.barh(tools, prompts, color=colors[:len(tools)])
    ax.set_xlabel('Items Recovered')
    ax.set_title('Tool Comparison: Recovery Coverage')

    plt.tight_layout()
    out_path = os.path.join(FIGURE_DIR, "fig4_tool_comparison.pdf")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {out_path}")


def main():
    print("[*] Generating paper figures\n")
    generate_persistence_timeline()
    generate_recovery_rates()
    generate_speed_benchmark()
    generate_tool_comparison()
    print(f"\n[+] Done. Figures in {FIGURE_DIR}/")


if __name__ == "__main__":
    main()
