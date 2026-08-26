"""
Real Ground Truth Evaluation Scaffolding

This script evaluates the recovery of deleted ChatGPT/Claude conversations
against real (non-synthetic) ground truth data, using user data exports.

IMPORTANT (IRB / ETHICS NOTE):
Because this script processes real user conversation exports containing potentially 
sensitive, personally identifiable, or confidential information, it must ONLY be 
used under an approved IRB protocol. Ensure that participants have provided informed 
consent for data export analysis and that all data is handled and stored securely 
on encrypted volumes. De-identification should be applied where possible.

Usage:
  python -m evaluation.real_ground_truth \
    --export-file path/to/export.json \
    --deleted-ids id1,id2 \
    --participant-id P01 \
    --platform chatgpt \
    --wait-hours 1.0
"""

import argparse
import csv
import json
import os
import sys
import time
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from tinker_tailor where appropriate
try:
    from tinker_tailor.carver.engine import carve_value
except ImportError:
    pass

def compute_word_jaccard(text1: str, text2: str) -> float:
    """
    Computes word-level Jaccard similarity between two texts.
    Matches the existing synthetic evaluation logic in experiment_recovery.py.
    """
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())
    
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
        
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)

def run_tinker_tailor_recovery(platform: str) -> List[dict]:
    """
    Scaffolding for running the actual carver to recover deleted conversations.
    """
    print("[*] Running Tinker Tailor recovery...")
    recovered_items = []
    
    from tinker_tailor.carver.browser_paths import get_forensic_paths
    from tinker_tailor.carver.engine import carve_leveldb_directory
    
    paths = get_forensic_paths()
    warnings = []
    for label, leveldb_path in paths.get("indexeddb", {}).items():
        if platform in label.lower():
            prompts, convs = carve_leveldb_directory(leveldb_path, platform, warnings)
            for p in prompts:
                parts = p.get("parts", [])
                text = parts[0] if parts else ""
                recovered_items.append({"text": text, "raw": p})
            
    return recovered_items

def evaluate_recovery(
    export_file: str,
    deleted_ids: List[str],
    participant_id: str,
    platform: str,
    wait_hours: float
):
    """
    Evaluates recovered data against known deleted conversations in the export.
    """
    print(f"[*] Starting evaluation for Participant: {participant_id} (Platform: {platform})")
    
    # 1. Load ground truth from the export file
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
    except Exception as e:
        print(f"[-] Failed to load export file: {e}")
        return
        
    # 2. Wait the configurable interval
    if wait_hours > 0:
        wait_seconds = int(wait_hours * 3600)
        print(f"[*] Waiting {wait_hours} hours ({wait_seconds}s) to allow natural browser cache/leveldb churn...")
        # time.sleep(wait_seconds) # Uncomment in real deployment
    
    # 3. Run recovery
    recovered_items = run_tinker_tailor_recovery(platform)
    recovered_texts = [item.get('text', '') for item in recovered_items]
    
    # 4. Compare using Jaccard similarity
    precision, recall, f1 = 0.0, 0.0, 0.0
    
    # 5. Output results
    os.makedirs("results", exist_ok=True)
    out_file = "results/real_ground_truth_eval.csv"
    
    file_exists = os.path.exists(out_file)
    
    fieldnames = [
        "participant_id", "platform", "conversations_deleted", 
        "conversations_recovered", "precision", "recall", "f1", 
        "hours_since_deletion"
    ]
    
    with open(out_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
            
        writer.writerow({
            "participant_id": participant_id,
            "platform": platform,
            "conversations_deleted": len(deleted_ids),
            "conversations_recovered": len(recovered_items),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "hours_since_deletion": wait_hours
        })
        
    print(f"[+] Evaluation complete. Results appended to {out_file}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate recovery on real ground truth exports")
    parser.add_argument("--export-file", required=True, help="Path to the JSON data export")
    parser.add_argument("--deleted-ids", required=True, help="Comma-separated list of conversation IDs that were deleted")
    parser.add_argument("--participant-id", required=True, help="Anonymous identifier for the participant")
    parser.add_argument("--platform", required=True, choices=["chatgpt", "claude"], help="Platform being evaluated")
    parser.add_argument("--wait-hours", type=float, default=1.0, help="Hours to wait after deletion before running recovery")
    
    args = parser.parse_args()
    
    deleted_ids_list = [i.strip() for i in args.deleted_ids.split(",")]
    
    evaluate_recovery(
        args.export_file,
        deleted_ids_list,
        args.participant_id,
        args.platform,
        args.wait_hours
    )

if __name__ == "__main__":
    main()
