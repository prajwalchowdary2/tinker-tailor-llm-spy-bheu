"""
Experiment: Corrupted / Truncated Data Recovery

Measures how well the V8 structured carver degrades under truncation,
random byte corruption, and contiguous zero-fill. Uses a known-good
synthetic ChatGPT blob with 5 messages as the reference.

Usage:
    python -m evaluation.experiment_corruption

Output:
    results/corruption_results.csv
"""

import csv
import os
import random
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import generate_chatgpt_entry
from tinker_tailor.carver.chatgpt import carve_v8_structured


# ---------------------------------------------------------------------------
# Reference blob — 5 messages
# ---------------------------------------------------------------------------

REFERENCE_MESSAGES = [
    {"role": "user",      "text": "What is the difference between stack and heap memory allocation?",     "id": "cor-001"},
    {"role": "assistant", "text": "Stack allocation is automatic and follows LIFO ordering while heap is manual",     "id": "cor-002"},
    {"role": "user",      "text": "Can you show me an example of a buffer overflow vulnerability?",       "id": "cor-003"},
    {"role": "assistant", "text": "A classic buffer overflow occurs when you write past the bounds of an array",      "id": "cor-004"},
    {"role": "user",      "text": "How does address space layout randomization help prevent exploitation?", "id": "cor-005"},
]

REFERENCE_EXPECTED = [m["text"] for m in REFERENCE_MESSAGES]
NUM_EXPECTED = len(REFERENCE_MESSAGES)


def _build_reference_blob() -> bytes:
    return generate_chatgpt_entry("conv-corrupt-1", "Memory safety questions", REFERENCE_MESSAGES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _jaccard(a: str, b: str) -> float:
    wa = set(_normalize(a).split())
    wb = set(_normalize(b).split())
    if not wa and not wb:
        return 1.0
    union = wa | wb
    return len(wa & wb) / len(union) if union else 0.0


def _count_recovered(raw: bytes) -> tuple:
    """
    Run carve_v8_structured on raw bytes.
    Returns (messages_recovered, crashed: bool).
    """
    try:
        prompts, conversations = carve_v8_structured(raw, "chatgpt")
        # Count unique recovered messages that match any expected message
        recovered_texts = set()
        for p in prompts:
            for part in p.get("parts", []):
                recovered_texts.add(part.strip())
        for conv in conversations:
            for msg in conv.get("messages", []):
                t = msg.get("text", "").strip()
                if t:
                    recovered_texts.add(t)

        # Count how many of the 5 expected messages were recovered
        matched = 0
        for expected in REFERENCE_EXPECTED:
            for rt in recovered_texts:
                if _jaccard(rt, expected) >= 0.5:
                    matched += 1
                    break

        return matched, False
    except Exception:
        return 0, True


# ---------------------------------------------------------------------------
# Corruption generators
# ---------------------------------------------------------------------------

def truncate(blob: bytes, pct: float) -> bytes:
    """Cut the blob at pct% of its length."""
    cut_point = int(len(blob) * pct)
    return blob[:cut_point]


def random_byte_corruption(blob: bytes, pct: float, seed: int = 42) -> bytes:
    """Randomly flip pct% of bytes."""
    rng = random.Random(seed)
    data = bytearray(blob)
    num_flips = max(1, int(len(data) * pct))
    positions = rng.sample(range(len(data)), min(num_flips, len(data)))
    for pos in positions:
        data[pos] = rng.randint(0, 255)
    return bytes(data)


def zero_fill(blob: bytes, position_pct: float, block_pct: float = 0.10) -> bytes:
    """Zero out a contiguous block starting at position_pct of the blob."""
    data = bytearray(blob)
    block_size = max(1, int(len(data) * block_pct))
    start = int(len(data) * position_pct)
    start = min(start, len(data) - block_size)
    if start < 0:
        start = 0
    for i in range(start, min(start + block_size, len(data))):
        data[i] = 0
    return bytes(data)


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment():
    print("=" * 72)
    print("  CORRUPTION / TRUNCATION RECOVERY EXPERIMENT")
    print("=" * 72)

    blob = _build_reference_blob()
    print(f"  Reference blob: {len(blob)} bytes, {NUM_EXPECTED} messages")

    # Verify baseline recovers all 5
    baseline_recovered, baseline_crashed = _count_recovered(blob)
    print(f"  Baseline recovery: {baseline_recovered}/{NUM_EXPECTED} messages"
          f" (crashed={baseline_crashed})")
    print()

    results = []
    fieldnames = [
        "corruption_type", "corruption_level", "trial",
        "messages_expected", "messages_recovered", "recovery_pct",
        "crashed",
    ]

    # -------------------------------------------------------------------
    # (a) Truncation
    # -------------------------------------------------------------------
    print("--- (a) Truncation ---")
    for pct in [0.95, 0.90, 0.75, 0.60, 0.50, 0.25, 0.10]:
        truncated = truncate(blob, pct)
        recovered, crashed = _count_recovered(truncated)
        recovery_pct = round(recovered / NUM_EXPECTED * 100, 1)

        row = {
            "corruption_type": "truncation",
            "corruption_level": f"{int(pct*100)}%",
            "trial": 1,
            "messages_expected": NUM_EXPECTED,
            "messages_recovered": recovered,
            "recovery_pct": recovery_pct,
            "crashed": crashed,
        }
        results.append(row)
        print(f"  Truncated at {int(pct*100)}% ({len(truncated)} bytes): "
              f"{recovered}/{NUM_EXPECTED} msgs ({recovery_pct}%) crashed={crashed}")

    # -------------------------------------------------------------------
    # (b) Random byte corruption — 10 trials per level
    # -------------------------------------------------------------------
    print("\n--- (b) Random byte corruption ---")
    for corruption_pct in [0.01, 0.02, 0.03, 0.05, 0.10, 0.20]:
        trial_results = []
        for trial in range(1, 11):
            corrupted = random_byte_corruption(blob, corruption_pct, seed=trial * 1000 + int(corruption_pct * 100))
            recovered, crashed = _count_recovered(corrupted)
            recovery_pct = round(recovered / NUM_EXPECTED * 100, 1)

            row = {
                "corruption_type": "random_byte",
                "corruption_level": f"{int(corruption_pct*100)}%",
                "trial": trial,
                "messages_expected": NUM_EXPECTED,
                "messages_recovered": recovered,
                "recovery_pct": recovery_pct,
                "crashed": crashed,
            }
            results.append(row)
            trial_results.append(recovered)

        mean_recovered = sum(trial_results) / len(trial_results)
        mean_pct = round(mean_recovered / NUM_EXPECTED * 100, 1)
        print(f"  {int(corruption_pct*100)}% corruption: mean {mean_recovered:.1f}/{NUM_EXPECTED} msgs "
              f"({mean_pct}%) over 10 trials  "
              f"[min={min(trial_results)} max={max(trial_results)}]")

    # -------------------------------------------------------------------
    # (c) Zero-fill corruption — block at 25%, 50%, 75% position
    # -------------------------------------------------------------------
    print("\n--- (c) Zero-fill corruption (10% block) ---")
    for position_pct in [0.10, 0.25, 0.50, 0.75, 0.90]:
        zeroed = zero_fill(blob, position_pct, block_pct=0.10)
        recovered, crashed = _count_recovered(zeroed)
        recovery_pct = round(recovered / NUM_EXPECTED * 100, 1)

        row = {
            "corruption_type": "zero_fill",
            "corruption_level": f"pos={int(position_pct*100)}%_block=10%",
            "trial": 1,
            "messages_expected": NUM_EXPECTED,
            "messages_recovered": recovered,
            "recovery_pct": recovery_pct,
            "crashed": crashed,
        }
        results.append(row)
        print(f"  Zero-fill at position {int(position_pct*100)}%: "
              f"{recovered}/{NUM_EXPECTED} msgs ({recovery_pct}%) crashed={crashed}")

    # -------------------------------------------------------------------
    # Write CSV
    # -------------------------------------------------------------------
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"), exist_ok=True)
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "corruption_results.csv")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[+] {len(results)} rows written to {output_path}")

    # Summary
    print("\n--- Summary ---")
    from collections import defaultdict
    by_type = defaultdict(list)
    for r in results:
        by_type[r["corruption_type"]].append(r["recovery_pct"])
    for ct, pcts in by_type.items():
        avg = sum(pcts) / len(pcts)
        print(f"  {ct:15s}: avg recovery {avg:.1f}% over {len(pcts)} trials")

    crash_count = sum(1 for r in results if r["crashed"])
    print(f"  Crashes: {crash_count}/{len(results)}")

    return results


if __name__ == "__main__":
    run_experiment()
