"""
Experiment 3: Persistence Timeline Study

Measures how long deleted LLM conversations remain recoverable in
LevelDB storage after deletion. This experiment is designed to be
run over 7 days on real machines — the script handles scheduling
and logging.

Usage:
    python -m evaluation.experiment_persistence --target /path/to/leveldb --bot chatgpt --interval 3600

Output:
    results/persistence_timeline.csv (appended on each run)
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinker_tailor.carver.engine import carve_leveldb_directory


def take_snapshot(leveldb_dir: str, bot_name: str, run_id: str) -> dict:
    """Take a single recovery snapshot of the target LevelDB directory."""
    t0 = time.time()
    prompts, conversations = carve_leveldb_directory(leveldb_dir, bot_name)
    elapsed = time.time() - t0

    total_messages = sum(len(c.get("messages", [])) for c in conversations)
    total_bytes = sum(
        sum(len(part) for part in p.get("parts", []))
        for p in prompts
    )

    db_files = {"log": 0, "ldb": 0, "sst": 0}
    if os.path.exists(leveldb_dir):
        for f in os.listdir(leveldb_dir):
            ext = os.path.splitext(f)[1].lstrip('.')
            if ext in db_files:
                db_files[ext] += 1

    return {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "bot": bot_name,
        "leveldb_dir": leveldb_dir,
        "prompts_recovered": len(prompts),
        "conversations_recovered": len(conversations),
        "messages_recovered": total_messages,
        "bytes_recovered": total_bytes,
        "log_files": db_files["log"],
        "ldb_files": db_files["ldb"],
        "sst_files": db_files["sst"],
        "carve_time_ms": round(elapsed * 1000, 2),
    }


def run_experiment(
    leveldb_dir: str,
    bot_name: str,
    interval_seconds: int = 3600,
    duration_hours: int = 168,
    run_id: str = None,
):
    """
    Run the persistence timeline experiment.

    Takes snapshots at regular intervals and appends results to CSV.
    Default: every hour for 7 days (168 hours).
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs("results", exist_ok=True)
    output_path = "results/persistence_timeline.csv"

    fieldnames = [
        "run_id", "timestamp", "epoch", "bot", "leveldb_dir",
        "prompts_recovered", "conversations_recovered",
        "messages_recovered", "bytes_recovered",
        "log_files", "ldb_files", "sst_files", "carve_time_ms",
    ]

    file_exists = os.path.exists(output_path)

    total_snapshots = (duration_hours * 3600) // interval_seconds
    print(f"[*] Persistence timeline experiment")
    print(f"    Target: {leveldb_dir}")
    print(f"    Bot: {bot_name}")
    print(f"    Interval: {interval_seconds}s | Duration: {duration_hours}h | Snapshots: {total_snapshots}")
    print(f"    Run ID: {run_id}")
    print()

    snapshot_count = 0
    start_time = time.time()
    end_time = start_time + duration_hours * 3600

    while time.time() < end_time:
        snapshot = take_snapshot(leveldb_dir, bot_name, run_id)
        snapshot_count += 1

        with open(output_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                file_exists = True
            writer.writerow(snapshot)

        hours_elapsed = (time.time() - start_time) / 3600
        print(f"  [{snapshot_count}/{total_snapshots}] {snapshot['timestamp']} | "
              f"{snapshot['prompts_recovered']} prompts, "
              f"{snapshot['conversations_recovered']} convs, "
              f"{snapshot['messages_recovered']} msgs, "
              f"{snapshot['bytes_recovered']} bytes | "
              f"{hours_elapsed:.1f}h elapsed")

        if time.time() + interval_seconds > end_time:
            break
        time.sleep(interval_seconds)

    print(f"\n[+] Experiment complete. {snapshot_count} snapshots -> {output_path}")


def single_snapshot(leveldb_dir: str, bot_name: str):
    """Take a single snapshot (for scripted/cron usage)."""
    run_id = "single_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = take_snapshot(leveldb_dir, bot_name, run_id)

    os.makedirs("results", exist_ok=True)
    output_path = "results/persistence_timeline.csv"
    fieldnames = list(snapshot.keys())
    file_exists = os.path.exists(output_path)

    with open(output_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(snapshot)

    print(f"[+] Snapshot: {snapshot['prompts_recovered']} prompts, "
          f"{snapshot['conversations_recovered']} convs -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Path to LevelDB directory")
    parser.add_argument("--bot", default="chatgpt", help="Bot name")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between snapshots")
    parser.add_argument("--duration", type=int, default=168, help="Total hours to run")
    parser.add_argument("--single", action="store_true", help="Take a single snapshot and exit")
    args = parser.parse_args()

    if args.single:
        single_snapshot(args.target, args.bot)
    else:
        run_experiment(args.target, args.bot, args.interval, args.duration)
