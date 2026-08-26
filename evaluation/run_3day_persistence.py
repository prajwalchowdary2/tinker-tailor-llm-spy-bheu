"""
3-Day Longitudinal Persistence Experiment Across All Profiles

Scans all active Chromium & Desktop App LevelDB directories hourly for 72 hours (3 days),
logging prompt counts, conversation counts, file counts (log/sst), and total byte sizes to results/persistence_timeline.csv.
"""
import time
import os
import sys
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinker_tailor.carver.browser_paths import get_forensic_paths
from tinker_tailor.carver.engine import carve_leveldb_directory


def run_3day_study(interval_seconds=3600, duration_hours=72, single_run=False):
    print(f"[*] Starting Persistence Study")
    print(f"    Interval: {interval_seconds}s ({interval_seconds/3600:.1f}h)")
    print(f"    Duration: {duration_hours}h (3 days)")
    
    os.makedirs("results", exist_ok=True)
    output_path = "results/persistence_timeline.csv"
    
    fieldnames = [
        "run_id", "timestamp", "epoch", "label", "bot", "leveldb_dir",
        "prompts_recovered", "conversations_recovered", "messages_recovered",
        "bytes_recovered", "log_files", "ldb_files", "sst_files", "carve_time_ms"
    ]
    
    run_id = datetime.now().strftime("run3d_%Y%m%d_%H%M%S")
    start_time = time.time()
    end_time = start_time + duration_hours * 3600
    snapshot_index = 0

    while time.time() < end_time:
        snapshot_index += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_epoch = time.time()
        
        paths_dict = get_forensic_paths().get("indexeddb", {})
        active_paths = {k: v for k, v in paths_dict.items() if os.path.exists(v)}
        
        file_exists = os.path.exists(output_path)
        with open(output_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            total_p = 0
            total_c = 0
            for label, p_dir in active_paths.items():
                bot_name = label.split('_')[0]
                t0 = time.time()
                warnings = []
                prompts, convs = carve_leveldb_directory(p_dir, bot_name, warnings)
                carve_ms = round((time.time() - t0) * 1000, 2)
                
                total_messages = sum(len(c.get("messages", [])) for c in convs)
                total_bytes = sum(
                    sum(len(part) for part in p.get("parts", []))
                    for p in prompts
                )
                
                db_files = {"log": 0, "ldb": 0, "sst": 0}
                for filename in os.listdir(p_dir):
                    ext = os.path.splitext(filename)[1].lstrip('.')
                    if ext in db_files:
                        db_files[ext] += 1
                
                row = {
                    "run_id": run_id,
                    "timestamp": now_str,
                    "epoch": now_epoch,
                    "label": label,
                    "bot": bot_name,
                    "leveldb_dir": p_dir,
                    "prompts_recovered": len(prompts),
                    "conversations_recovered": len(convs),
                    "messages_recovered": total_messages,
                    "bytes_recovered": total_bytes,
                    "log_files": db_files["log"],
                    "ldb_files": db_files["ldb"],
                    "sst_files": db_files["sst"],
                    "carve_time_ms": carve_ms,
                }
                writer.writerow(row)
                total_p += len(prompts)
                total_c += len(convs)
        
        elapsed_h = (time.time() - start_time) / 3600
        print(f"[{snapshot_index}] {now_str} | Scanned {len(active_paths)} dirs | Total Prompts: {total_p} | Convs: {total_c} | Elapsed: {elapsed_h:.2f}h / {duration_hours}h", flush=True)
        
        if single_run or (time.time() + interval_seconds > end_time):
            break
        time.sleep(interval_seconds)


if __name__ == "__main__":
    single = "--single" in sys.argv
    run_3day_study(single_run=single)
