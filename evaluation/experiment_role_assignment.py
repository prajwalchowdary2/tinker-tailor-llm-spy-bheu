"""
Experiment: Role-Assignment Robustness

Motivation. The ChatGPT carver assigns each recovered message a role using
the parity of its (Smi-decoded) array index:

    role = "user" if (idx // 2) % 2 == 1 else "assistant"

This assumes strict user/assistant alternation beginning with a user turn
(Section 5.3, and flagged as a limitation in Section 8.4). This experiment
quantifies how often that heuristic misassigns roles when a conversation
violates strict alternation: a leading system prompt, a regenerated
response (two assistant turns in a row), an interleaved tool/plugin call,
or an assistant-first transcript.

We synthesize conversations with a *known* role for every turn, run the
real carver (carve_v8_structured), align recovered messages to ground
truth by position, and report per-scenario role accuracy. No real browser
data is used.

Usage:
    python -m evaluation.experiment_role_assignment

Output:
    results/role_assignment_results.csv
"""

import csv
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import generate_chatgpt_entry
from tinker_tailor.carver.chatgpt import carve_v8_structured


def _texts(role_seq: List[str]) -> List[Dict]:
    """Build a message list with a distinct text per turn and a true role."""
    msgs = []
    for i, role in enumerate(role_seq):
        msgs.append({
            "role": role,                       # ground-truth role
            "text": f"Turn {i} content marker delta {i:03d} unique phrase alpha",
            "id": f"role-{i:03d}",
        })
    return msgs


# Each scenario: a ground-truth role sequence. The carver only ever emits
# "user"/"assistant"; system/tool turns therefore cannot be represented and
# are always counted as misassigned (which is the point).
SCENARIOS = [
    {"label": "strict alternation (user first)",
     "roles": ["user", "assistant", "user", "assistant", "user", "assistant"]},
    {"label": "leading system prompt",
     "roles": ["system", "user", "assistant", "user", "assistant", "user"]},
    {"label": "one regenerated response",
     "roles": ["user", "assistant", "assistant", "user", "assistant", "user"]},
    {"label": "two regenerations",
     "roles": ["user", "assistant", "assistant", "assistant", "user", "assistant"]},
    {"label": "interleaved tool call",
     "roles": ["user", "tool", "assistant", "user", "assistant", "user"]},
    {"label": "assistant-first transcript",
     "roles": ["assistant", "user", "assistant", "user", "assistant", "user"]},
]


def run_experiment():
    print("=" * 78)
    print("  ROLE-ASSIGNMENT ROBUSTNESS  (synthetic edge cases, real carver)")
    print("=" * 78)

    rows = []
    total_correct = total_msgs = 0
    for sc in SCENARIOS:
        true_roles = sc["roles"]
        raw = generate_chatgpt_entry("conv-role", "Role test", _texts(true_roles))
        _, convs = carve_v8_structured(raw, "chatgpt")

        recovered = convs[0]["messages"] if convs else []
        # recovered preserves array order; align by position
        n = min(len(recovered), len(true_roles))
        correct = sum(1 for i in range(n) if recovered[i]["role"] == true_roles[i])
        acc = correct / len(true_roles) if true_roles else 0.0

        rows.append({
            "scenario": sc["label"],
            "turns": len(true_roles),
            "roles_correct": correct,
            "role_accuracy": round(acc, 3),
        })
        total_correct += correct
        total_msgs += len(true_roles)
        print(f"  {sc['label']:34s} | {correct}/{len(true_roles)} correct "
              f"(acc={acc:.2f})")

    micro = total_correct / total_msgs if total_msgs else 0.0
    print(f"\n  micro-avg role accuracy across scenarios: {micro:.3f} "
          f"({total_correct}/{total_msgs})")

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "role_assignment_results.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "turns", "roles_correct", "role_accuracy"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n[+] {len(rows)} rows written to {out_path}")
    return rows


if __name__ == "__main__":
    run_experiment()
