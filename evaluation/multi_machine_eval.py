"""
Multi-Machine Evaluation Scaffolding

This script serves as scaffolding for running multi-machine evaluations,
as requested per USENIX reviewer feedback. It facilitates running the 
Tinker Tailor tool across multiple distinct machines, collecting per-machine 
statistics, and aggregating them for paper reporting.

Usage:
  python -m evaluation.multi_machine_eval --machine-id M1
  python -m evaluation.multi_machine_eval --aggregate
"""

import argparse
import csv
import glob
import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from tinker_tailor
try:
    from tinker_tailor.carver.engine import carve_value
except ImportError:
    pass

def collect_machine_stats(machine_id: str):
    """
    Runs a scan on the current machine and records the findings to a CSV file.
    """
    print(f"[*] Starting collection for machine: {machine_id}")
    
    start_time = time.perf_counter()
    
    # --- STUB: Replace with actual Tinker Tailor scanning logic ---
    os_version = platform.platform()
    chrome_version = "Unknown"
    num_profiles = 0
    num_active_dirs = 0
    total_prompts = 0
    chatgpt_prompts = 0
    claude_drafts = 0
    total_conversations = 0
    total_leveldb_size_kb = 0.0
    # -------------------------------------------------------------
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    os.makedirs("results/multi_machine", exist_ok=True)
    out_file = f"results/multi_machine/{machine_id}_stats.csv"
    
    fieldnames = [
        "machine_id", "os_version", "chrome_version", "num_profiles",
        "num_active_dirs", "total_prompts", "chatgpt_prompts", 
        "claude_drafts", "total_conversations", "total_scan_time_ms", 
        "total_leveldb_size_kb"
    ]
    
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "machine_id": machine_id,
            "os_version": os_version,
            "chrome_version": chrome_version,
            "num_profiles": num_profiles,
            "num_active_dirs": num_active_dirs,
            "total_prompts": total_prompts,
            "chatgpt_prompts": chatgpt_prompts,
            "claude_drafts": claude_drafts,
            "total_conversations": total_conversations,
            "total_scan_time_ms": round(elapsed_ms, 2),
            "total_leveldb_size_kb": round(total_leveldb_size_kb, 2)
        })
        
    print(f"[+] Saved stats to {out_file}")

def aggregate_results():
    """
    Reads all individual machine CSV files and computes summary statistics.
    """
    csv_files = glob.glob("results/multi_machine/*_stats.csv")
    if not csv_files:
        print("[-] No machine stats files found in results/multi_machine/")
        return
        
    metrics = {
        "num_profiles": [],
        "num_active_dirs": [],
        "total_prompts": [],
        "chatgpt_prompts": [],
        "claude_drafts": [],
        "total_conversations": [],
        "total_scan_time_ms": [],
        "total_leveldb_size_kb": []
    }
    
    print(f"[*] Aggregating data from {len(csv_files)} machines...")
    
    for fpath in csv_files:
        with open(fpath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k in metrics.keys():
                    if k in row:
                        metrics[k].append(float(row[k]))
                        
    out_file = "results/multi_machine_aggregated.csv"
    stats_results = []
    
    for metric, values in metrics.items():
        if not values:
            continue
        stats_results.append({
            "metric": metric,
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "std": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
            "min": round(min(values), 2),
            "max": round(max(values), 2)
        })
        
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "mean", "median", "std", "min", "max"])
        writer.writeheader()
        writer.writerows(stats_results)
        
    print(f"[+] Aggregation complete. Results saved to {out_file}")
    for res in stats_results:
        print(f"  {res['metric']:25s} | mean: {res['mean']:8.2f} | std: {res['std']:8.2f}")

def main():
    parser = argparse.ArgumentParser(description="Multi-machine evaluation scaffolding")
    parser.add_argument("--machine-id", type=str, help="Run scan on this machine and save as machine ID")
    parser.add_argument("--aggregate", action="store_true", help="Aggregate all machine CSVs into summary statistics")
    args = parser.parse_args()
    
    if args.aggregate:
        aggregate_results()
    elif args.machine_id:
        collect_machine_stats(args.machine_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
