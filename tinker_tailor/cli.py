"""
CLI Entry Point — Tinker Tailor LLM Spy (13-Layer Forensic Suite v4.0)

Provides a comprehensive command-line interface for multi-tier forensic carving
of LLM chat histories across Chrome/Chromium browsers and Electron AI desktop
applications. Covers 13 vulnerability classes from LevelDB remanence through
extension API key leakage and cross-profile isolation failure.
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
from tinker_tailor.forensics.deep_chrome import (
    scan_saved_credentials,
    scan_session_cookies,
    scan_ai_history_with_titles,
    scan_ai_downloads,
    scan_extension_secrets,
    scan_desktop_app_keys,
    scan_cross_profile_isolation,
    scan_electron_app_cookies,
)


def main():
    parser = argparse.ArgumentParser(
        description="Tinker Tailor LLM Spy — 13-Layer Browser & AI Forensic Suite v4.0",
    )
    parser.add_argument("--scan", action="store_true", help="Auto-detect and scan all browser LevelDB profiles")
    parser.add_argument("--all", action="store_true", help="Execute complete 13-Layer forensic audit across all data sources")
    parser.add_argument("--target", type=str, help="Path to a specific LevelDB directory")
    parser.add_argument("--bot", type=str, default="chatgpt", help="Bot name (chatgpt, claude, gemini, deepseek)")
    parser.add_argument("--output", type=str, default="evidence.json", help="Output file path")
    parser.add_argument("--dlp", action="store_true", help="Run DLP credential & PII scanner on carved data")
    parser.add_argument("--sign", action="store_true", help="Sign evidence with HMAC-SHA256")
    parser.add_argument("--report", action="store_true", help="Generate interactive HTML forensic report (counts only, no raw data)")

    # Original 7 layers
    parser.add_argument("--blobs", action="store_true", help="Layer 2: Carve unencrypted uploaded document blobs")
    parser.add_argument("--sessions", action="store_true", help="Layer 6: Carve SNSS Session Restore for AI tabs")
    parser.add_argument("--shortcuts", action="store_true", help="Layer 7: Carve omnibox search queries")
    parser.add_argument("--cursor", action="store_true", help="Layer 4: Carve Cursor AI IDE Composer transcripts")
    parser.add_argument("--cache", action="store_true", help="Layer 5: Carve Service Worker CacheStorage")

    # Deep Chrome layers (8-13)
    parser.add_argument("--deep", action="store_true", help="Run deep Chrome analysis (Layers 8-13: cookies, history, downloads, extensions, desktop apps, isolation)")
    parser.add_argument("--cookies", action="store_true", help="Layer 8: Extract active AI session cookies")
    parser.add_argument("--history", action="store_true", help="Layer 9: Extract AI conversation URLs with titles")
    parser.add_argument("--downloads", action="store_true", help="Layer 10: Extract AI platform download records")
    parser.add_argument("--extensions", action="store_true", help="Layer 11: Scan extension storage for API keys & JWTs")
    parser.add_argument("--desktop", action="store_true", help="Layer 12: Scan desktop apps for private keys & tokens")
    parser.add_argument("--isolation", action="store_true", help="Layer 13: Check cross-profile OS-level isolation")

    args = parser.parse_args()

    has_layer = any([args.scan, args.all, args.target, args.blobs, args.sessions,
                     args.shortcuts, args.cursor, args.cache, args.deep,
                     args.cookies, args.history, args.downloads, args.extensions,
                     args.desktop, args.isolation, args.report])
    if not has_layer:
        parser.print_help()
        sys.exit(1)

    print("=" * 70)
    print("  Tinker Tailor LLM Spy — 13-Layer Forensic Suite v4.0.0-bheu")
    print("=" * 70)

    all_prompts = []
    all_conversations = []
    warnings = []

    # ── Layer 1: LevelDB Scanning ────────────────────────────────
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
            print(f"[L1] Scanning {label}: {leveldb_path}")
            prompts, convs = carve_leveldb_directory(leveldb_path, bot, warnings)
            all_prompts.extend(prompts)
            all_conversations.extend(convs)
            print(f"     -> {len(prompts)} prompts, {len(convs)} conversations")

    # ── Layer 2: Unencrypted Document Blobs ──────────────────────
    blobs = []
    if args.blobs or args.all:
        print("[L2] Scanning unencrypted document blobs (.indexeddb.blob/)...")
        blobs = scan_blob_directories()
        print(f"     -> {len(blobs)} document blobs recovered")

    # ── Layer 4: Cursor AI IDE ───────────────────────────────────
    cursor_items = []
    if args.cursor or args.all:
        print("[L4] Carving Cursor AI IDE Composer storage...")
        cursor_items = scan_cursor_ide_storage()
        print(f"     -> {len(cursor_items)} Cursor IDE sessions recovered")

    # ── Layer 5: CacheStorage ────────────────────────────────────
    cache_items = []
    if args.cache or args.all:
        print("[L5] Carving Service Worker CacheStorage...")
        cache_items = scan_cache_storage()
        print(f"     -> {len(cache_items)} cached AI responses recovered")

    # ── Layer 6: Session Restore ─────────────────────────────────
    sessions = []
    if args.sessions or args.all:
        print("[L6] Carving SNSS Session Restore logs...")
        sessions = scan_session_restore_files()
        print(f"     -> {len(sessions)} AI tab events recovered")

    # ── Layer 7: Omnibox Shortcuts ───────────────────────────────
    shortcuts = []
    if args.shortcuts or args.all:
        print("[L7] Carving Omnibox search shortcuts...")
        shortcuts = scan_omnibox_shortcuts()
        print(f"     -> {len(shortcuts)} search queries recovered")

    # ── Layer 8: Session Cookies ─────────────────────────────────
    cookies = []
    if args.cookies or args.deep or args.all:
        print("[L8] Extracting active AI session cookies...")
        cookies = scan_session_cookies()
        print(f"     -> {len(cookies)} AI session cookies found")

    # ── Layer 9: Conversation URLs with Titles ───────────────────
    ai_history = []
    if args.history or args.deep or args.all:
        print("[L9] Extracting AI conversation URLs with titles...")
        ai_history = scan_ai_history_with_titles()
        print(f"     -> {len(ai_history)} conversation URLs recovered")

    # ── Layer 10: AI Download Records ────────────────────────────
    ai_downloads = []
    if args.downloads or args.deep or args.all:
        print("[L10] Extracting AI platform download records...")
        ai_downloads = scan_ai_downloads()
        print(f"     -> {len(ai_downloads)} AI downloads found")

    # ── Layer 11: Extension API Key & JWT Leakage ────────────────
    ext_secrets = []
    if args.extensions or args.deep or args.all:
        print("[L11] Scanning extension storage for API keys & JWTs...")
        ext_secrets = scan_extension_secrets()
        print(f"     -> {len(ext_secrets)} leaked secrets found")

    # ── Layer 12: Desktop App Private Keys ───────────────────────
    desktop_keys = []
    electron_cookies = []
    if args.desktop or args.deep or args.all:
        print("[L12] Scanning Electron desktop apps for private keys...")
        desktop_keys = scan_desktop_app_keys()
        electron_cookies = scan_electron_app_cookies()
        print(f"     -> {len(desktop_keys)} desktop app secrets, {len(electron_cookies)} Electron cookies")

    # ── Layer 13: Cross-Profile Isolation ────────────────────────
    isolation = {}
    if args.isolation or args.deep or args.all:
        print("[L13] Checking cross-profile OS-level isolation...")
        isolation = scan_cross_profile_isolation()
        status = "FAILED" if isolation.get("isolation_failure") else "OK"
        print(f"     -> {isolation.get('total_profiles', 0)} profiles, isolation: {status}")

    # ── Build evidence bundle ────────────────────────────────────
    evidence = {
        "tool": "tinker_tailor",
        "version": "4.0.0-bheu",
        "timestamp": time.time(),
        "prompts": all_prompts,
        "conversations": all_conversations,
        "document_blobs": blobs,
        "session_restore_tabs": sessions,
        "omnibox_shortcuts": shortcuts,
        "cursor_ide_telemetry": cursor_items,
        "service_worker_cache": cache_items,
        "deep_chrome": {
            "session_cookies": cookies,
            "ai_history": ai_history,
            "ai_downloads": ai_downloads,
            "extension_secrets": ext_secrets,
            "desktop_app_keys": desktop_keys,
            "electron_app_cookies": electron_cookies,
            "cross_profile_isolation": isolation,
        },
        "warnings": warnings,
        "stats": {
            "total_prompts": len(all_prompts),
            "total_conversations": len(all_conversations),
            "total_document_blobs": len(blobs),
            "total_session_tabs": len(sessions),
            "total_shortcuts": len(shortcuts),
            "total_cursor_sessions": len(cursor_items),
            "total_cache_entries": len(cache_items),
            "total_session_cookies": len(cookies),
            "total_ai_history": len(ai_history),
            "total_ai_downloads": len(ai_downloads),
            "total_extension_secrets": len(ext_secrets),
            "total_desktop_keys": len(desktop_keys),
            "total_electron_cookies": len(electron_cookies),
            "cross_profile_isolation_failure": isolation.get("isolation_failure", False),
            "total_profiles_scanned": isolation.get("total_profiles", 0),
        },
    }

    # ── DLP Scanner ──────────────────────────────────────────────
    if args.dlp or args.all:
        dlp_results = scan_evidence(evidence)
        evidence["dlp"] = dlp_results
        print(f"\n[DLP] {dlp_results['total_findings']} findings: "
              f"{dlp_results['credentials']} credentials, {dlp_results['pii']} PII")

    # ── Evidence Signing ─────────────────────────────────────────
    if args.sign:
        key = generate_session_key()
        evidence = sign_evidence(evidence, key)
        print("[*] Evidence signed with HMAC-SHA256 (key_version=1)")

    # ── HTML Report Generation ───────────────────────────────────
    if args.report or args.all:
        try:
            from tinker_tailor.report import generate_forensic_report
            report_path = generate_forensic_report(evidence)
            print(f"\n[REPORT] HTML forensic report -> {report_path}")
        except ImportError:
            print("\n[REPORT] report.py not available, skipping HTML report")

    # ── Save JSON Evidence ───────────────────────────────────────
    with open(args.output, 'w') as f:
        json.dump(evidence, f, indent=2, default=str)

    total_artifacts = sum([
        len(all_prompts), len(all_conversations), len(blobs),
        len(sessions), len(shortcuts), len(cursor_items), len(cache_items),
        len(cookies), len(ai_history), len(ai_downloads),
        len(ext_secrets), len(desktop_keys), len(electron_cookies),
    ])
    print(f"\n{'=' * 70}")
    print(f"  13-Layer Forensic Audit Complete -> {args.output}")
    print(f"  Total Artifacts: {total_artifacts:,}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
