"""
Layer 6: Chromium SNSS Session Restore & Tab Carver

Parses Chromium binary Session_* and Tabs_* SNSS files to extract
active, closed, and background AI conversation tabs and exact URL parameters.
"""

import os
import glob
import re
from typing import List, Dict, Any


def scan_session_restore_files() -> List[Dict[str, Any]]:
    """
    Carve Chromium Sessions/ directory for AI tab visits and conversation URLs.
    """
    home = os.path.expanduser("~")
    session_artifacts = []

    search_patterns = [
        f"{home}/Library/Application Support/Google/Chrome/*/Sessions/Session_*",
        f"{home}/Library/Application Support/Google/Chrome/*/Sessions/Tabs_*",
        f"{home}/Library/Application Support/Microsoft Edge/*/Sessions/Session_*",
        f"{home}/Library/Application Support/Microsoft Edge/*/Sessions/Tabs_*",
    ]

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        search_patterns.extend([
            f"{local_app}/Google/Chrome/User Data/*/Sessions/Session_*",
            f"{local_app}/Google/Chrome/User Data/*/Sessions/Tabs_*",
            f"{local_app}/Microsoft/Edge/User Data/*/Sessions/Session_*",
            f"{local_app}/Microsoft/Edge/User Data/*/Sessions/Tabs_*",
        ])

    matched_files = []
    for pattern in search_patterns:
        matched_files.extend(glob.glob(pattern))

    for s_file in matched_files:
        profile = "Default"
        parts = s_file.split(os.sep)
        for part in parts:
            if part.startswith("Profile ") or part in ["Default", "System Profile"]:
                profile = part
                break

        try:
            sz = os.path.getsize(s_file)
            mtime = os.path.getmtime(s_file)
            with open(s_file, "rb") as fp:
                data = fp.read()

            if not data.startswith(b'SNSS'):
                continue

            # Find all AI URLs
            urls = re.findall(
                rb'https?://(?:chatgpt\.com|claude\.ai|gemini\.google\.com|perplexity\.ai|chat\.deepseek\.com)[^\s\x00\x01-\x1f\"\'<>]*',
                data
            )

            seen_in_file = set()
            for u_raw in urls:
                u_str = u_raw.decode("utf-8", errors="ignore")
                if u_str not in seen_in_file:
                    seen_in_file.add(u_str)

                    bot = "generic"
                    convo_id = ""
                    if "chatgpt.com" in u_str:
                        bot = "chatgpt"
                        m = re.search(r'/c/([a-f0-9-]+)', u_str)
                        if m:
                            convo_id = m.group(1)
                    elif "claude.ai" in u_str:
                        bot = "claude"
                        m = re.search(r'/chat/([a-f0-9-]+)', u_str)
                        if m:
                            convo_id = m.group(1)
                    elif "gemini.google.com" in u_str:
                        bot = "gemini"
                        m = re.search(r'/app/([a-f0-9-]+)', u_str)
                        if m:
                            convo_id = m.group(1)
                    elif "deepseek.com" in u_str:
                        bot = "deepseek"
                    elif "perplexity.ai" in u_str:
                        bot = "perplexity"

                    session_artifacts.append({
                        "profile": profile,
                        "file_type": "Session Restore (SNSS)",
                        "session_file": os.path.basename(s_file),
                        "bot": bot,
                        "url": u_str,
                        "conversation_id": convo_id,
                        "timestamp": mtime,
                        "size_bytes": sz,
                    })
        except Exception:
            pass

    return session_artifacts
