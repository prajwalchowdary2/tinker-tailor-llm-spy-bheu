"""
Layer 5: Service Worker CacheStorage Carver

Scans Chromium Service Worker CacheStorage directories for cached AI API responses,
auth handshakes, and application state.
"""

import os
import glob
import re
from typing import List, Dict, Any


def scan_cache_storage() -> List[Dict[str, Any]]:
    """
    Search for AI-related cached responses and auth tokens in Service Worker CacheStorage.
    """
    home = os.path.expanduser("~")
    cache_artifacts = []

    search_patterns = [
        f"{home}/Library/Application Support/Google/Chrome/*/Service Worker/CacheStorage/*/*/*",
        f"{home}/Library/Application Support/Microsoft Edge/*/Service Worker/CacheStorage/*/*/*",
    ]

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        search_patterns.extend([
            f"{local_app}/Google/Chrome/User Data/*/Service Worker/CacheStorage/*/*/*",
            f"{local_app}/Microsoft/Edge/User Data/*/Service Worker/CacheStorage/*/*/*",
        ])

    matched_files = []
    for pattern in search_patterns:
        matched_files.extend(glob.glob(pattern))

    for c_file in matched_files:
        if not os.path.isfile(c_file) or c_file.endswith("index.txt"):
            continue

        profile = "Default"
        parts = c_file.split(os.sep)
        for part in parts:
            if part.startswith("Profile ") or part in ["Default", "System Profile"]:
                profile = part
                break

        try:
            sz = os.path.getsize(c_file)
            if sz == 0 or sz > 10 * 1024 * 1024:
                continue

            with open(c_file, "rb") as fp:
                data = fp.read(1024)

            urls = re.findall(rb'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s\x00\x01-\x1f\"\'<>]*', data)
            for u in urls:
                u_str = u.decode("utf-8", errors="ignore")
                if any(k in u_str for k in ["chatgpt", "openai", "claude", "anthropic", "gemini", "bard", "deepseek", "perplexity"]):
                    cache_artifacts.append({
                        "profile": profile,
                        "cache_file": os.path.basename(c_file),
                        "url": u_str,
                        "size_bytes": sz,
                    })
                    break
        except Exception:
            pass

    return cache_artifacts
