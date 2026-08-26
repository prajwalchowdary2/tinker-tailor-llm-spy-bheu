"""
Claude TipTap Draft Recovery

Recovers unsubmitted user prompts from Claude's TipTap editor state
stored in IndexedDB. Claude uses TipTap (a ProseMirror wrapper) for
its chat input, and the editor state is persisted as JSON to IndexedDB
on every keystroke — meaning partial, unsent drafts survive deletion.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

from tinker_tailor.carver.leveldb import read_varint


def extract_tiptap_text(node: dict) -> str:
    """Recursively extract plaintext from a TipTap ProseMirror document tree."""
    if not isinstance(node, dict):
        return ""
    text = ""
    if node.get("type") == "text" and "text" in node:
        text += node["text"]
    if "content" in node and isinstance(node["content"], list):
        for child in node["content"]:
            text += extract_tiptap_text(child)
    return text


def carve_claude_chats(value: bytes, mtime: float = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Carve Claude chat drafts from raw LevelDB value bytes.

    Searches for tipTapEditorState JSON objects, extracts the plaintext
    from the ProseMirror document tree, and deduplicates keystroke
    trails (keeping only the longest finished sentences).

    Returns (prompts, conversations).
    """
    prompts = []
    conversations = []

    text = value.decode('utf-8', errors='ignore')
    if "tipTapEditorState" not in text:
        return prompts, conversations

    pos = 0
    pattern = '"tipTapEditorState"'
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extracted_prompts = []

    while True:
        pos = text.find(pattern, pos)
        if pos == -1:
            break

        start_pos = text.rfind('{', 0, pos)
        if start_pos == -1:
            pos += len(pattern)
            continue

        brace_count = 0
        end_pos = -1
        for i in range(start_pos, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break

        if end_pos != -1:
            json_str = text[start_pos:end_pos]
            try:
                data = json.loads(json_str)
                if "tipTapEditorState" in data:
                    tiptap = data["tipTapEditorState"]
                else:
                    tiptap = data.get("state", {}).get("tipTapEditorState", {})
                extracted = extract_tiptap_text(tiptap)
                if extracted.strip():
                    extracted_prompts.append(extracted.strip())
            except Exception:
                pass
            pos = end_pos
        else:
            pos += len(pattern)

    deduped_prompts = []
    extracted_prompts.sort(key=len, reverse=True)
    for p in extracted_prompts:
        is_sub = False
        for kept in deduped_prompts:
            if p in kept:
                is_sub = True
                break
        if not is_sub:
            deduped_prompts.append(p)

    for idx, p in enumerate(deduped_prompts):
        prompts.append({
            "bot": "claude",
            "role": "user",
            "parts": [p],
            "deleted": True,
            "offset": idx,
            "timestamp": timestamp
        })

    return prompts, conversations
