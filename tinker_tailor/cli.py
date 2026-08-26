"""
CLI Entry Point — Tinker Tailor LLM Spy (7-Layer Forensic Suite)

Provides a comprehensive command-line interface for multi-tier forensic carving
of LLM chat histories, uploaded document blobs, session restore tabs, omnibox
shortcuts, and AI IDE transcripts.
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
from tinker_tailor.forensics.blobs import scan_blob_directories
from tinker_tailor.forensics.sessions import scan_session_restore_files
from tinker_tailor.forensics.shortcuts import scan_omnibox_shortcuts
from tinker_tailor.forensics.cursor import scan_cursor_ide_storage
from tinker_tailor.forensics.cache import scan_cache_storage


def main():
    parser = argparse.ArgumentParser(
        description="Tinker Tailor LLM Spy — 7-Layer Browser & AI Forensic Suite",
    )
    parser.add_argument("--scan", action="store_true", help="Auto-detect and scan all browser LevelDB profiles")
    parser.add_argument("--all", action="store_true", help="Execute complete 7-Layer forensic audit across all data sources")
    parser.add_argument("--target", type=str, help="Path to a specific LevelDB directory")
    parser.add_argument("--bot", type=str, default="chatgpt", help="Bot name (chatgpt, claude, gemini, deepseek)")
    parser.add_argument("--output", type=str, default="evidence.json", help="Output file path")
    parser.add_argument("--dlp", action="store_true", help="Run DLP credential & PII scanner on carved data")
    parser.add_argument("--sign", action="store_true", help="Sign evidence with HMAC-SHA256")
    parser.add_argument("--blobs", action="store_true", help="Carve unencrypted uploaded document blobs (.indexeddb.blob/)")
    parser.add_argument("--sessions", action="store_true", help="Carve binary SNSS Session Restore files for AI tabs")
    parser.add_argument("--shortcuts", action="store_true", help="Carve typed omnibox search queries and AI shortcuts")
    parser.add_argument("--cursor", action="store_true", help="Carve Cursor AI IDE Composer transcripts & configs")
    parser.add_argument("--cache", action="store_true", help="Carve Service Worker CacheStorage for AI API responses")

    args = parser.parse_args()

    if not any([args.scan, args.all, args.target, args.blobs, args.sessions, args.shortcuts, args.cursor, args.cache]):
        parser.print_help()
        sys.exit(1)

    all_prompts = []
    all_conversations = []
    warnings = []

    # 1. LevelDB Scanning
    if args.target:
        prompts, convs = carve_leveldb_directory(args.target, args.bot, warnings)
        all_prompts.extend(prompts)
        all_conversations.extend(convs)
    elif args.scan or args.all:
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

    # 2. Blobs Scanning (Layer 2)
    blobs = []
    if args.blobs or args.all:
        print("[*] Scanning unencrypted document blobs (.indexeddb.blob/)...")
        blobs = scan_blob_directories()
        print(f"    -> {len(blobs)} document & file blobs recovered")

    # 3. Session Restore (Layer 6)
    sessions = []
    if args.sessions or args.all:
        print("[*] Carving binary SNSS Session Restore logs...")
        sessions = scan_session_restore_files()
        print(f"    -> {len(sessions)} active/closed AI conversation tab events recovered")

    # 4. Shortcuts & Omnibox (Layer 7)
    shortcuts = []
    if args.shortcuts or args.all:
        print("[*] Carving Omnibox search intent & shortcut databases...")
        shortcuts = scan_omnibox_shortcuts()
        print(f"    -> {len(shortcuts)} omnibox search queries recovered")

    # 5. Cursor AI IDE (Layer 4)
    cursor_items = []
    if args.cursor or args.all:
        print("[*] Carving Cursor AI IDE Composer global storage...")
        cursor_items = scan_cursor_ide_storage()
        print(f"    -> {len(cursor_items)} Cursor IDE Composer sessions & configs recovered")

    # 6. CacheStorage (Layer 5)
    cache_items = []
    if args.cache or args.all:
        print("[*] Carving Service Worker CacheStorage...")
        cache_items = scan_cache_storage()
        print(f"    -> {len(cache_items)} cached AI responses recovered")

    evidence = {
        "tool": "tinker_tailor",
        "version": "3.0.0-bheu",
        "timestamp": time.time(),
        "prompts": all_prompts,
        "conversations": all_conversations,
        "document_blobs": blobs,
        "session_restore_tabs": sessions,
        "omnibox_shortcuts": shortcuts,
        "cursor_ide_telemetry": cursor_items,
        "service_worker_cache": cache_items,
        "warnings": warnings,
        "stats": {
            "total_prompts": len(all_prompts),
            "total_conversations": len(all_conversations),
            "total_document_blobs": len(blobs),
            "total_session_tabs": len(sessions),
            "total_shortcuts": len(shortcuts),
            "total_cursor_sessions": len(cursor_items),
            "total_cache_entries": len(cache_items),
        },
    }

    if args.dlp or args.all:
        dlp_results = scan_evidence(evidence)
        evidence["dlp"] = dlp_results
        print(f"\n[DLP] {dlp_results['total_findings']} findings: "
              f"{dlp_results['credentials']} credentials, {dlp_results['pii']} PII")

    if args.sign:
        key = generate_session_key()
        evidence = sign_evidence(evidence, key)
        print(f"[*] Evidence signed with HMAC-SHA256 (key_version=1)")

    with open(args.output, 'w') as f:
        json.dump(evidence, f, indent=2, default=str)

    print(f"\n[+] Comprehensive 7-Layer Forensic Audit Complete -> {args.output}")


if __name__ == "__main__":
    main()
