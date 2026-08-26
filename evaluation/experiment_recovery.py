"""
Experiment 1: Recovery Rate Measurement

Injects known ground-truth conversations into synthetic LevelDB value
blobs, runs each platform-specific carver, and measures precision,
recall, and F1 score.

Usage:
    python -m evaluation.experiment_recovery

Output:
    results/recovery_rates.csv
"""

import csv
import os
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import GroundTruthDataset
from tinker_tailor.carver.engine import carve_value
from tinker_tailor.carver.claude import carve_claude_chats
from tinker_tailor.carver.chatgpt import carve_v8_structured
from tinker_tailor.carver.generic import carve_generic_chats


def _normalize(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    return " ".join(text.lower().split())


def _text_overlap(recovered: str, expected: str) -> float:
    """Word-level Jaccard similarity between recovered and expected text."""
    r_words = set(_normalize(recovered).split())
    e_words = set(_normalize(expected).split())
    if not e_words:
        return 0.0
    intersection = r_words & e_words
    union = r_words | e_words
    return len(intersection) / len(union) if union else 0.0


def evaluate_chatgpt_case(case: Dict) -> Dict:
    """Evaluate recovery for a single ChatGPT ground-truth case."""
    raw = case["raw_bytes"]
    expected = case["expected_messages"]

    prompts, conversations = carve_v8_structured(raw, "chatgpt")

    recovered_texts = set()
    for p in prompts:
        for part in p.get("parts", []):
            recovered_texts.add(_normalize(part))
    for conv in conversations:
        for msg in conv.get("messages", []):
            recovered_texts.add(_normalize(msg.get("text", "")))

    expected_texts = {_normalize(m["text"]) for m in expected}

    true_positives = 0
    for et in expected_texts:
        for rt in recovered_texts:
            if _text_overlap(rt, et) > 0.7:
                true_positives += 1
                break

    precision = true_positives / len(recovered_texts) if recovered_texts else 0.0
    recall = true_positives / len(expected_texts) if expected_texts else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "platform": "chatgpt",
        "case_id": case.get("conversation_id", ""),
        "expected_count": len(expected_texts),
        "recovered_count": len(recovered_texts),
        "true_positives": true_positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_claude_case(case: Dict) -> Dict:
    """Evaluate recovery for a single Claude ground-truth case."""
    raw = case["raw_bytes"]
    expected_drafts = case["expected_drafts"]

    prompts, _ = carve_claude_chats(raw)

    recovered_texts = set()
    for p in prompts:
        for part in p.get("parts", []):
            recovered_texts.add(_normalize(part))

    longest_expected = _normalize(max(expected_drafts, key=len))

    true_positives = 0
    for rt in recovered_texts:
        if _text_overlap(rt, longest_expected) > 0.7:
            true_positives += 1

    precision = true_positives / len(recovered_texts) if recovered_texts else 0.0
    recall = 1.0 if true_positives > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "platform": "claude",
        "case_id": "claude_draft",
        "expected_count": 1,
        "recovered_count": len(recovered_texts),
        "true_positives": true_positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_generic_case(case: Dict) -> Dict:
    """Evaluate recovery for a generic platform ground-truth case."""
    raw = case["raw_bytes"]
    expected_prompts = case["expected_prompts"]
    bot_name = case["bot_name"]

    prompts, _ = carve_generic_chats(raw, bot_name)

    recovered_texts = set()
    for p in prompts:
        for part in p.get("parts", []):
            recovered_texts.add(_normalize(part))

    expected_texts = {_normalize(p) for p in expected_prompts}

    true_positives = 0
    for et in expected_texts:
        for rt in recovered_texts:
            if _text_overlap(rt, et) > 0.7:
                true_positives += 1
                break

    precision = true_positives / len(recovered_texts) if recovered_texts else 0.0
    recall = true_positives / len(expected_texts) if expected_texts else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "platform": bot_name,
        "case_id": f"{bot_name}_generic",
        "expected_count": len(expected_texts),
        "recovered_count": len(recovered_texts),
        "true_positives": true_positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def run_experiment():
    """Run the full recovery rate experiment across all platforms."""
    dataset = GroundTruthDataset().build_standard_dataset()
    results = []

    print(f"[*] Running recovery rate experiment on {len(dataset)} test cases\n")

    for case in dataset:
        platform = case["platform"]
        t0 = time.time()

        if platform == "chatgpt":
            result = evaluate_chatgpt_case(case)
        elif platform == "claude":
            result = evaluate_claude_case(case)
        else:
            result = evaluate_generic_case(case)

        elapsed = time.time() - t0
        result["elapsed_ms"] = round(elapsed * 1000, 2)
        results.append(result)

        status = "PASS" if result["f1"] >= 0.5 else "WARN"
        print(f"  [{status}] {result['platform']:12s} | P={result['precision']:.2f} R={result['recall']:.2f} F1={result['f1']:.2f} | "
              f"{result['recovered_count']}/{result['expected_count']} msgs | {result['elapsed_ms']:.1f}ms")

    os.makedirs("results", exist_ok=True)
    output_path = "results/recovery_rates.csv"
    fieldnames = ["platform", "case_id", "expected_count", "recovered_count",
                  "true_positives", "precision", "recall", "f1", "elapsed_ms"]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_f1 = sum(r["f1"] for r in results) / len(results)

    print(f"\n[+] Results written to {output_path}")
    print(f"    Average: P={avg_precision:.2f} R={avg_recall:.2f} F1={avg_f1:.2f}")

    return results


if __name__ == "__main__":
    run_experiment()
