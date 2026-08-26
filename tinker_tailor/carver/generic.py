"""
Generic Regex-Based Fallback Carver

Last-resort carver that uses regex patterns to extract chat-like
content from raw LevelDB value bytes when neither the V8 structured
parser nor the TipTap parser matches the data.

Used for: DeepSeek, Perplexity, Cline, and any other LLM web app
that stores conversation data in IndexedDB without a known schema.
"""

import re
import time
from datetime import datetime
from typing import Dict, List, Tuple


CONTENT_PATTERNS = [
    r'"content"\s*:\s*"([^"]{10,2000})"',
    r'"prompt"\s*:\s*"([^"]{10,2000})"',
    r'"text"\s*:\s*"([^"]{10,2000})"',
    r'"query"\s*:\s*"([^"]{10,2000})"',
    r'"user_input"\s*:\s*"([^"]{10,2000})"',
    r'"input_text"\s*:\s*"([^"]{10,2000})"',
]

NOISE_KEYWORDS = [
    "content-type", "application/json", "text/html",
    "<svg", "bootstrap", "react", "font-family",
    "function()", "var ", "const ",
]


def carve_generic_chats(value: bytes, bot_name: str, mtime: float = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract chat-like content using regex pattern matching.

    Filters out common noise (HTML, JS, HTTP headers) and deduplicates
    substring matches.

    Returns (prompts, conversations).
    """
    prompts = []
    conversations = []

    text = value.decode('utf-8', errors='ignore')
    if len(text) < 30:
        return prompts, conversations

    extracted = []
    for pat in CONTENT_PATTERNS:
        matches = re.findall(pat, text)
        for m in matches:
            m_clean = m.strip().replace('\\n', '\n').replace('\\"', '"')
            if any(ignore in m_clean.lower() for ignore in NOISE_KEYWORDS):
                continue
            if len(m_clean) >= 10:
                extracted.append(m_clean)

    extracted.sort(key=len, reverse=True)
    deduped = []
    for s in extracted:
        if not any(s in existing for existing in deduped):
            deduped.append(s)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, p in enumerate(deduped):
        prompts.append({
            "bot": bot_name,
            "role": "user",
            "parts": [p],
            "deleted": True,
            "offset": idx,
            "timestamp": timestamp,
        })

    if prompts:
        msg_list = [
            {"id": f"{bot_name}-{i}", "text": p["parts"][0], "index": i + 1, "role": "user"}
            for i, p in enumerate(prompts[:20])
        ]
        conversations.append({
            "id": f"{bot_name}-feed",
            "title": f"{bot_name.upper()} Telemetry Capture ({len(prompts)} prompts)",
            "bot": bot_name,
            "messages": msg_list,
            "offset": 0,
            "mtime": mtime or time.time(),
        })

    return prompts, conversations
