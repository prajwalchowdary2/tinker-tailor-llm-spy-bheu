"""
Experiment 2: Infostealer Speed Benchmark

Multi-trial benchmark measuring how fast the carver can extract LLM
chat data, compared against published EDR detection windows.
Demonstrates that extraction completes before endpoint detection
can intervene.

Usage:
    python -m evaluation.experiment_speed [--trials 1000]

Output:
    results/speed_benchmark.csv
"""

import argparse
import csv
import math
import os
import statistics
import sys
import time
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import GroundTruthDataset
from tinker_tailor.carver.engine import carve_value


EDR_DETECTION_WINDOWS_MS = {
    "CrowdStrike Falcon": 250,
    "Microsoft Defender": 500,
    "SentinelOne": 300,
    "Carbon Black": 1000,
    "Elastic Security": 750,
}


def benchmark_single_carve(raw_bytes: bytes, bot_name: str) -> float:
    """Time a single carve operation. Returns elapsed milliseconds."""
    t0 = time.perf_counter()
    carve_value(raw_bytes, bot_name)
    return (time.perf_counter() - t0) * 1000


def confidence_interval_95(data: List[float]) -> tuple:
    """Calculate 95% confidence interval assuming normal distribution."""
    n = len(data)
    if n < 2:
        return (0.0, 0.0)
    mean = statistics.mean(data)
    stderr = statistics.stdev(data) / math.sqrt(n)
    margin = 1.96 * stderr
    return (mean - margin, mean + margin)


def run_experiment(trials: int = 1000):
    """Run the speed benchmark experiment."""
    dataset = GroundTruthDataset().build_standard_dataset()

    print(f"[*] Speed benchmark: {trials} trials per test case\n")

    results = []
    all_times = []

    for case in dataset:
        platform = case["platform"]
        bot_name = case["bot_name"]
        raw = case["raw_bytes"]

        times = []
        for _ in range(trials):
            elapsed = benchmark_single_carve(raw, bot_name)
            times.append(elapsed)

        all_times.extend(times)

        mean_ms = statistics.mean(times)
        median_ms = statistics.median(times)
        stdev_ms = statistics.stdev(times) if len(times) > 1 else 0.0
        p95 = sorted(times)[int(0.95 * len(times))]
        p99 = sorted(times)[int(0.99 * len(times))]
        ci_low, ci_high = confidence_interval_95(times)

        edr_beaten = sum(1 for name, window in EDR_DETECTION_WINDOWS_MS.items() if p99 < window)

        result = {
            "platform": platform,
            "bot_name": bot_name,
            "trials": trials,
            "input_bytes": len(raw),
            "mean_ms": round(mean_ms, 3),
            "median_ms": round(median_ms, 3),
            "stdev_ms": round(stdev_ms, 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
            "p95_ms": round(p95, 3),
            "p99_ms": round(p99, 3),
            "ci95_low_ms": round(ci_low, 3),
            "ci95_high_ms": round(ci_high, 3),
            "edr_systems_beaten": edr_beaten,
        }
        results.append(result)

        print(f"  {platform:12s} | mean={mean_ms:.2f}ms median={median_ms:.2f}ms "
              f"p95={p95:.2f}ms p99={p99:.2f}ms | beats {edr_beaten}/{len(EDR_DETECTION_WINDOWS_MS)} EDRs")

    os.makedirs("results", exist_ok=True)

    output_path = "results/speed_benchmark.csv"
    fieldnames = ["platform", "bot_name", "trials", "input_bytes",
                  "mean_ms", "median_ms", "stdev_ms", "min_ms", "max_ms",
                  "p95_ms", "p99_ms", "ci95_low_ms", "ci95_high_ms",
                  "edr_systems_beaten"]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    overall_p99 = sorted(all_times)[int(0.99 * len(all_times))]
    print(f"\n[+] Results written to {output_path}")
    print(f"    Overall p99: {overall_p99:.2f}ms")
    print(f"\n    EDR Detection Windows:")
    for name, window in sorted(EDR_DETECTION_WINDOWS_MS.items(), key=lambda x: x[1]):
        status = "BEATEN" if overall_p99 < window else "DETECTED"
        print(f"      {name:25s} {window:6d}ms  [{status}]")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=1000)
    args = parser.parse_args()
    run_experiment(args.trials)
