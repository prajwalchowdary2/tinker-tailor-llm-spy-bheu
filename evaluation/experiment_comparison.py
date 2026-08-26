"""
Experiment 4: Tool Comparison

Compares Tinker Tailor against baseline approaches for recovering
LLM chat data from Chromium LevelDB:

1. Tinker Tailor (our tool) — V8-aware structured carving
2. Raw string search (grep baseline) — regex over raw bytes
3. JSON key scan — searches for known JSON keys without V8 parsing

Usage:
    python -m evaluation.experiment_comparison --target /path/to/leveldb --bot chatgpt

Output:
    results/tool_comparison.csv
"""

import csv
import os
import re
import sys
import time
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinker_tailor.carver.engine import carve_leveldb_directory
from tinker_tailor.carver.leveldb import parse_sstable


def baseline_grep(leveldb_dir: str) -> Tuple[int, float]:
    """
    Baseline 1: Raw string search.

    Reads all LevelDB files and counts regex matches for chat-like content.
    This is what a responder would get with grep/strings.
    """
    t0 = time.time()
    matches = 0
    patterns = [
        rb'"content"\s*:\s*"[^"]{10,}"',
        rb'"text"\s*:\s*"[^"]{10,}"',
        rb'"prompt"\s*:\s*"[^"]{10,}"',
    ]

    if not os.path.exists(leveldb_dir):
        return 0, 0.0

    for filename in os.listdir(leveldb_dir):
        if not filename.endswith(('.log', '.ldb', '.sst')):
            continue
        filepath = os.path.join(leveldb_dir, filename)
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            for pat in patterns:
                matches += len(re.findall(pat, content))
        except Exception:
            continue

    elapsed = time.time() - t0
    return matches, elapsed


def baseline_json_scan(leveldb_dir: str) -> Tuple[int, int, float]:
    """
    Baseline 2: JSON key scanning.

    Parses SSTables but only looks for JSON-parseable content,
    missing V8 binary-serialized data entirely.
    """
    t0 = time.time()
    prompts = 0
    conversations = 0

    if not os.path.exists(leveldb_dir):
        return 0, 0, 0.0

    for filename in os.listdir(leveldb_dir):
        if not filename.endswith(('.log', '.ldb', '.sst')):
            continue
        filepath = os.path.join(leveldb_dir, filename)
        try:
            if filename.endswith(('.ldb', '.sst')):
                entries = parse_sstable(filepath)
            else:
                with open(filepath, 'rb') as f:
                    entries = [(b"wal", f.read())]

            for key, value in entries:
                text = value.decode('utf-8', errors='ignore')
                try:
                    import json
                    data = json.loads(text)
                    if isinstance(data, dict):
                        if "messages" in data or "text" in data or "content" in data:
                            prompts += 1
                        if "title" in data and "messages" in data:
                            conversations += 1
                except (json.JSONDecodeError, ValueError):
                    pass
        except Exception:
            continue

    elapsed = time.time() - t0
    return prompts, conversations, elapsed


def run_experiment(leveldb_dir: str, bot_name: str):
    """Run the full tool comparison experiment."""
    print(f"[*] Tool comparison experiment")
    print(f"    Target: {leveldb_dir}")
    print(f"    Bot: {bot_name}\n")

    results = []

    # Tool 1: Tinker Tailor
    t0 = time.time()
    tt_prompts, tt_convs = carve_leveldb_directory(leveldb_dir, bot_name)
    tt_elapsed = time.time() - t0
    tt_messages = sum(len(c.get("messages", [])) for c in tt_convs)

    results.append({
        "tool": "tinker_tailor",
        "bot": bot_name,
        "prompts": len(tt_prompts),
        "conversations": len(tt_convs),
        "messages": tt_messages,
        "elapsed_s": round(tt_elapsed, 3),
    })
    print(f"  Tinker Tailor    | {len(tt_prompts):4d} prompts, {len(tt_convs):3d} convs, "
          f"{tt_messages:4d} msgs | {tt_elapsed:.3f}s")

    # Tool 2: Grep baseline
    grep_matches, grep_elapsed = baseline_grep(leveldb_dir)
    results.append({
        "tool": "grep_baseline",
        "bot": bot_name,
        "prompts": grep_matches,
        "conversations": 0,
        "messages": grep_matches,
        "elapsed_s": round(grep_elapsed, 3),
    })
    print(f"  Grep baseline    | {grep_matches:4d} matches                         | {grep_elapsed:.3f}s")

    # Tool 3: JSON scan baseline
    json_prompts, json_convs, json_elapsed = baseline_json_scan(leveldb_dir)
    results.append({
        "tool": "json_scan",
        "bot": bot_name,
        "prompts": json_prompts,
        "conversations": json_convs,
        "messages": json_prompts,
        "elapsed_s": round(json_elapsed, 3),
    })
    print(f"  JSON scan        | {json_prompts:4d} prompts, {json_convs:3d} convs                | {json_elapsed:.3f}s")

    # Write results
    os.makedirs("results", exist_ok=True)
    output_path = "results/tool_comparison.csv"
    fieldnames = ["tool", "bot", "prompts", "conversations", "messages", "elapsed_s"]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    if len(tt_prompts) > 0:
        grep_ratio = grep_matches / len(tt_prompts) if len(tt_prompts) > 0 else 0
        json_ratio = json_prompts / len(tt_prompts) if len(tt_prompts) > 0 else 0
        print(f"\n    Grep recovers {grep_ratio:.0%} of what Tinker Tailor finds")
        print(f"    JSON scan recovers {json_ratio:.0%} of what Tinker Tailor finds")

    print(f"\n[+] Results written to {output_path}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Path to LevelDB directory")
    parser.add_argument("--bot", default="chatgpt", help="Bot name")
    args = parser.parse_args()
    run_experiment(args.target, args.bot)
