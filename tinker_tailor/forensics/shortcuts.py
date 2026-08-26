"""
Layer 7: Omnibox & Search Intent Forensics

Carves Chromium Shortcuts and Network Action Predictor SQLite databases
to extract typed search queries, AI portal navigation shortcuts, and omnibox inputs.
"""

import os
import glob
import sqlite3
from typing import List, Dict, Any


def scan_omnibox_shortcuts() -> List[Dict[str, Any]]:
    """
    Query Chromium Shortcuts databases across all profiles.
    """
    home = os.path.expanduser("~")
    shortcut_artifacts = []

    search_patterns = [
        f"{home}/Library/Application Support/Google/Chrome/*/Shortcuts",
        f"{home}/Library/Application Support/Microsoft Edge/*/Shortcuts",
    ]

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        search_patterns.extend([
            f"{local_app}/Google/Chrome/User Data/*/Shortcuts",
            f"{local_app}/Microsoft/Edge/User Data/*/Shortcuts",
        ])

    matched_dbs = []
    for pattern in search_patterns:
        matched_dbs.extend(glob.glob(pattern))

    for db_path in matched_dbs:
        profile = "Default"
        parts = db_path.split(os.sep)
        for part in parts:
            if part.startswith("Profile ") or part in ["Default", "System Profile"]:
                profile = part
                break

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT text, url, contents, last_access_time FROM omni_box_shortcuts")
            rows = cursor.fetchall()
            conn.close()

            for text, url, title, last_access in rows:
                is_ai_related = any(k in (text + url + title).lower() for k in [
                    "chat", "gpt", "claude", "gemini", "bard", "deepseek", "perplexity", "openai", "anthropic", "llm"
                ])
                if is_ai_related or len(text) > 3:
                    shortcut_artifacts.append({
                        "profile": profile,
                        "typed_text": text,
                        "destination_url": url,
                        "page_title": title,
                        "last_access_chrome_epoch": last_access,
                        "is_ai_target": is_ai_related,
                    })
        except Exception:
            pass

    return shortcut_artifacts
