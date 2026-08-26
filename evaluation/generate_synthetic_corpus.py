#!/usr/bin/env python3
"""Generate a synthetic LevelDB-like test corpus for TINKER TAILOR."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import (
    generate_chatgpt_entry,
    generate_claude_entry,
    generate_generic_entry,
)

CORPUS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_corpus"
)


def create_corpus():
    manifest = {"description": "Synthetic test corpus for TINKER TAILOR", "profiles": []}

    # ChatGPT profile
    chatgpt_dir = os.path.join(CORPUS_DIR, "chatgpt_profile", "IndexedDB",
                               "https_chatgpt.com_0.indexeddb.leveldb")
    os.makedirs(chatgpt_dir, exist_ok=True)

    chatgpt_entries = [
        generate_chatgpt_entry("conv-001", "Python debugging help", [
            {"id": "m1", "text": "How do I fix a segfault in my C program?"},
            {"id": "m2", "text": "A segfault usually means you're accessing invalid memory."},
            {"id": "m3", "text": "Thanks, I found the null pointer dereference."},
        ]),
        generate_chatgpt_entry("conv-002", "API key rotation", [
            {"id": "m4", "text": "What's the best practice for rotating API keys?"},
            {"id": "m5", "text": "Use a secrets manager and implement graceful key rotation."},
        ]),
        generate_chatgpt_entry("conv-003", "Unicode test conversation", [
            {"id": "m6", "text": "Help me debug this \U0001f41b in my code \U0001f4bb"},
            {"id": "m7", "text": "请帮我优化这个SQL查询语句"},
        ]),
    ]
    wal_data = b"\x00".join(chatgpt_entries)
    with open(os.path.join(chatgpt_dir, "000003.log"), "wb") as f:
        f.write(wal_data)

    manifest["profiles"].append({
        "name": "chatgpt_profile",
        "platform": "chatgpt",
        "expected_conversations": 3,
        "expected_messages": 7,
        "path": "chatgpt_profile/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb",
    })

    # Claude profile
    claude_dir = os.path.join(CORPUS_DIR, "claude_profile", "IndexedDB",
                              "https_claude.ai_0.indexeddb.leveldb")
    os.makedirs(claude_dir, exist_ok=True)

    claude_entries = [
        generate_claude_entry([
            "Write me a Python script",
            "Write me a Python script that",
            "Write me a Python script that sorts a list",
            "Write me a Python script that sorts a list of dictionaries by key",
        ]),
        generate_claude_entry([
            "Explain quantum computing in simple terms",
        ]),
        generate_claude_entry([
            "मुझे Python में sorting algorithm समझाइए",
        ]),
    ]
    wal_data = b"\x00".join(claude_entries)
    with open(os.path.join(claude_dir, "000003.log"), "wb") as f:
        f.write(wal_data)

    manifest["profiles"].append({
        "name": "claude_profile",
        "platform": "claude",
        "expected_drafts": 6,
        "path": "claude_profile/IndexedDB/https_claude.ai_0.indexeddb.leveldb",
    })

    # Generic profile (DeepSeek / Perplexity)
    generic_dir = os.path.join(CORPUS_DIR, "generic_profile", "IndexedDB",
                               "https_chat.deepseek.com_0.indexeddb.leveldb")
    os.makedirs(generic_dir, exist_ok=True)

    generic_entries = [
        generate_generic_entry([
            "What is the difference between TCP and UDP?",
            "Explain WebSockets vs HTTP polling",
        ], field="content"),
        generate_generic_entry([
            "Compare TLS 1.3 vs TLS 1.2 performance",
        ], field="content"),
    ]
    wal_data = b"\x00".join(generic_entries)
    with open(os.path.join(generic_dir, "000003.log"), "wb") as f:
        f.write(wal_data)

    manifest["profiles"].append({
        "name": "generic_profile",
        "platform": "deepseek",
        "expected_prompts": 3,
        "path": "generic_profile/IndexedDB/https_chat.deepseek.com_0.indexeddb.leveldb",
    })

    with open(os.path.join(CORPUS_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[+] Synthetic corpus created at {CORPUS_DIR}/")
    print(f"    ChatGPT: 3 conversations, 7 messages (incl. Unicode)")
    print(f"    Claude:  6 TipTap drafts (incl. Hindi)")
    print(f"    Generic: 3 prompts")
    print(f"    Manifest: {CORPUS_DIR}/manifest.json")


if __name__ == "__main__":
    create_corpus()
