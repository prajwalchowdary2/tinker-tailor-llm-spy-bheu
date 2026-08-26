"""
Generate figures for the three robustness/analysis additions:

  * fig_persistence_model.pdf  — analytical persistence bound vs write rate
  * fig_schema_drift.pdf       — structured vs full-pipeline recall per mutation
  * fig_role_robustness.pdf    — role-assignment accuracy per conversation structure

The schema-drift and role-assignment figures pull their numbers directly
from the experiment modules (the same code paths that produce the paper
tables), so the figures cannot drift from the tables. The persistence
figure is computed from the closed-form model (M=4MB, k=4).
"""

import contextlib
import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
FIGURE_DIR = os.path.join(_REPO_ROOT, "paper", "figures")
os.makedirs(FIGURE_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

COLORS = {
    "primary": "#1565C0",
    "secondary": "#2E7D32",
    "accent": "#E65100",
    "danger": "#C62828",
    "purple": "#6A1B9A",
    "teal": "#00838F",
    "gray": "#546E7A",
}


def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def fig_persistence_model():
    """Analytical persistence bound T = M/W and kM/W (M=4MB, k=4)."""
    M_kb = 4 * 1024        # 4 MB memtable, in KB
    k = 4
    W = np.logspace(1, 4.2, 200)      # write rate, KB/day: 10 .. ~16000
    t_flush = M_kb / W
    t_reclaim = k * M_kb / W

    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    ax.plot(W, t_reclaim, color=COLORS["accent"], lw=2,
            label=r"$T_{\mathrm{reclaim}}=kM/W$ (approx. L0 trigger volume)")
    ax.plot(W, t_flush, color=COLORS["primary"], lw=2,
            label=r"$T_{\mathrm{flush}}=M/W$ (approx. WAL accumulation time)")

    # observed point: 83 days -> W ~= M/83
    w_obs = M_kb / 83.0
    ax.scatter([w_obs], [83], color=COLORS["danger"], zorder=5, s=45)
    ax.annotate("observed 83 d\n(W\u224849 KB/day)", xy=(w_obs, 83),
                xytext=(w_obs * 1.6, 83 * 2.1), fontsize=8,
                color=COLORS["danger"],
                arrowprops=dict(arrowstyle="->", color=COLORS["danger"], lw=1))

    ax.axhline(7, color=COLORS["gray"], ls=":", lw=1)
    ax.text(ax.get_xlim()[1], 7, " 7-day re-scan", va="center", ha="right",
            fontsize=7.5, color=COLORS["gray"])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Per-origin write rate $W$ (KB/day)")
    ax.set_ylabel("Persistence (days)")
    ax.set_title("Analytical persistence model (LevelDB $M{=}4$MB, $k{=}4$)",
                 fontweight="bold")
    ax.legend(loc="upper right")
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, "fig_persistence_model.pdf")
    plt.savefig(out)
    plt.close()
    print(f"[OK] {os.path.basename(out)}")


def fig_schema_drift():
    """Structured-only vs full-pipeline recall per schema mutation."""
    from evaluation.experiment_schema_drift import run_experiment
    rows = _quiet(run_experiment)

    # short labels for readability
    short = {
        "baseline (observed schema)": "baseline",
        "reordered keys (text before id)": "reorder keys",
        "renamed id field (id->uuid)": "rename id",
        "renamed anchor (messages->mapping)": "rename anchor",
        "added nesting (text one level deeper)": "add nesting",
        "renamed anchor + kept text field": "rename anchor (2)",
        "renamed text field (text->content)": "rename text",
        "combined drift (rename anchor+text)": "combined",
    }
    labels = [short.get(r["mutation"], r["mutation"]) for r in rows]
    struct = [r["structured_recall"] for r in rows]
    full = [r["full_recall"] for r in rows]

    x = np.arange(len(labels))
    w = 0.4
    fig, ax = plt.subplots(figsize=(7, 3.1))
    ax.bar(x - w / 2, struct, w, label="Structured parser only",
           color=COLORS["gray"], edgecolor="white")
    ax.bar(x + w / 2, full, w, label="Full pipeline (with fallback)",
           color=COLORS["primary"], edgecolor="white")

    ax.set_ylabel("Message-text recall")
    ax.set_ylim(0, 1.15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7.5)
    ax.set_title("Schema-drift robustness: fallback absorbs structural change",
                 fontweight="bold")
    ax.legend(loc="upper right")
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, "fig_schema_drift.pdf")
    plt.savefig(out)
    plt.close()
    print(f"[OK] {os.path.basename(out)}")


def fig_role_robustness():
    """Role-assignment accuracy per conversation structure."""
    from evaluation.experiment_role_assignment import run_experiment
    rows = _quiet(run_experiment)

    short = {
        "strict alternation (user first)": "strict alt.",
        "two regenerations": "2 regens",
        "one regenerated response": "1 regen",
        "interleaved tool call": "tool call",
        "leading system prompt": "system prompt",
        "assistant-first transcript": "assistant-first",
    }
    # sort by accuracy descending for a clean read
    rows = sorted(rows, key=lambda r: r["role_accuracy"], reverse=True)
    labels = [short.get(r["scenario"], r["scenario"]) for r in rows]
    acc = [r["role_accuracy"] for r in rows]
    colors = [COLORS["secondary"] if a >= 0.99 else
              (COLORS["accent"] if a >= 0.5 else COLORS["danger"]) for a in acc]

    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    bars = ax.bar(labels, acc, color=colors, edgecolor="white", width=0.6)
    for b, a in zip(bars, acc):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02,
                f"{a:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_ylabel("Role accuracy")
    ax.set_ylim(0, 1.15)
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax.set_title("Role assignment: exact under alternation, else cascades",
                 fontweight="bold")
    plt.tight_layout()
    out = os.path.join(FIGURE_DIR, "fig_role_robustness.pdf")
    plt.savefig(out)
    plt.close()
    print(f"[OK] {os.path.basename(out)}")


def generate_all():
    fig_persistence_model()
    fig_schema_drift()
    fig_role_robustness()


if __name__ == "__main__":
    print("[*] Generating robustness/analysis figures\n")
    generate_all()
    print(f"\n[+] Done. Figures in {FIGURE_DIR}/")
