"""
Layer 4: AI IDE & Desktop App Forensic Carver

Extracts Cursor IDE Composer conversations, agent executions, and tool calls
from global and workspace SQLite storage (state.vscdb).
"""

import os
import glob
import sqlite3
import json
from typing import List, Dict, Any


def scan_cursor_ide_storage() -> List[Dict[str, Any]]:
    """
    Carve Cursor AI IDE conversations from global and workspace state.vscdb files.
    """
    home = os.path.expanduser("~")
    cursor_artifacts = []

    global_db = os.path.join(home, "Library/Application Support/Cursor/User/globalStorage/state.vscdb")
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        win_global = os.path.join(appdata, "Cursor/User/globalStorage/state.vscdb")
        if os.path.exists(win_global):
            global_db = win_global

    if os.path.exists(global_db):
        try:
            conn = sqlite3.connect(f"file:{global_db}?mode=ro", uri=True)
            cursor = conn.cursor()

            # 1. Composer Headers
            cursor.execute("SELECT value FROM ItemTable WHERE key='composer.composerHeaders'")
            row = cursor.fetchone()
            if row:
                headers = json.loads(row[0])
                all_composers = headers.get("allComposers", []) if isinstance(headers, dict) else headers
                if isinstance(all_composers, list):
                    for c in all_composers:
                        cursor_artifacts.append({
                            "source": "Cursor Global Composer",
                            "composer_id": c.get("composerId"),
                            "name": c.get("name") or "Untitled Composer Session",
                            "created_at": c.get("createdAt"),
                            "last_updated": c.get("lastUpdatedAt"),
                            "is_agent": c.get("isAgent", False),
                        })

            # 2. Reactive Application User state for model configs and server tokens
            cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%applicationUser%'")
            row = cursor.fetchone()
            if row:
                app_data = json.loads(row[0])
                creds = app_data.get("cursorCreds", {})
                models = app_data.get("featureModelConfigs", {})
                if creds or models:
                    cursor_artifacts.append({
                        "source": "Cursor App Configuration",
                        "auth_client_id": creds.get("authClientId"),
                        "auth_domain": creds.get("authDomain"),
                        "active_models": list(models.keys()) if isinstance(models, dict) else [],
                    })

            conn.close()
        except Exception:
            pass

    return cursor_artifacts
