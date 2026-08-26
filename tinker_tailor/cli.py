"""
CLI Entry Point — Tinker Tailor LLM Spy

Provides a command-line interface for forensic carving of LLM chat
histories from local browser storage.

Usage:
    python -m tinker_tailor.cli --scan
    python -m tinker_tailor.cli --target /path/to/leveldb --bot chatgpt
    python -m tinker_tailor.cli --output results.json
"""

import argparse
import json
import os
import sys
import time

from tinker_tailor.carver.browser_paths import get_forensic_paths
from tinker_tailor.carver.engine import carve_leveldb_directory, carve_cursor_chats
from tinker_tailor.dlp.scanner import scan_evidence
from tinker_tailor.forensics.chain_of_custody import (
    generate_session_key,
    sign_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description="Tinker Tailor LLM Spy — Forensic LLM Chat Recovery",
    )
    parser.add_argument("--scan", action="store_true", help="Auto-detect and scan all browser profiles")
    parser.add_argument("--target", type=str, help="Path to a specific LevelDB directory")
    parser.add_argument("--bot", type=str, default="chatgpt", help="Bot name (chatgpt, claude, gemini, deepseek)")
    parser.add_argument("--output", type=str, default="evidence.json", help="Output file path")
    parser.add_argument("--dlp", action="store_true", help="Run DLP scanner on carved data")
    parser.add_argument("--sign", action="store_true", help="Sign evidence with HMAC-SHA256")
    parser.add_argument("--cursor", action="store_true", help="Include Cursor IDE transcripts")

    args = parser.parse_args()

    all_prompts = []
    all_conversations = []
    warnings = []

    if args.target:
        prompts, convs = carve_leveldb_directory(args.target, args.bot, warnings)
        all_prompts.extend(prompts)
        all_conversations.extend(convs)
    elif args.scan:
        paths = get_forensic_paths()
        for label, leveldb_path in paths.get("indexeddb", {}).items():
            if not os.path.exists(leveldb_path):
                continue
            bot = label.split("_")[0]
            print(f"[*] Scanning {label}: {leveldb_path}")
            prompts, convs = carve_leveldb_directory(leveldb_path, bot, warnings)
            all_prompts.extend(prompts)
            all_conversations.extend(convs)
            print(f"    -> {len(prompts)} prompts, {len(convs)} conversations")
    else:
        parser.print_help()
        sys.exit(1)

    if args.cursor:
        cursor_prompts, cursor_convs = carve_cursor_chats(warnings)
        all_prompts.extend(cursor_prompts)
        all_conversations.extend(cursor_convs)

    evidence = {
        "tool": "tinker_tailor",
        "version": "2.0.0",
        "timestamp": time.time(),
        "prompts": all_prompts,
        "conversations": all_conversations,
        "warnings": warnings,
        "stats": {
            "total_prompts": len(all_prompts),
            "total_conversations": len(all_conversations),
        },
    }

    if args.dlp:
        dlp_results = scan_evidence(evidence)
        evidence["dlp"] = dlp_results
        print(f"\n[DLP] {dlp_results['total_findings']} findings: "
              f"{dlp_results['credentials']} credentials, {dlp_results['pii']} PII")

    if args.sign:
        key = generate_session_key()
        evidence = sign_evidence(evidence, key)
        print(f"[*] Evidence signed (key_version=1)")

    with open(args.output, 'w') as f:
        json.dump(evidence, f, indent=2, default=str)

    print(f"\n[+] Done. {len(all_prompts)} prompts, {len(all_conversations)} conversations -> {args.output}")


if __name__ == "__main__":
    main()
