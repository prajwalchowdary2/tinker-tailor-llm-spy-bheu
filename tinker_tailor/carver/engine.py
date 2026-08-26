"""
Carver Engine — Unified Entry Point

Routes LevelDB value bytes through the appropriate platform-specific
carver (Claude TipTap, ChatGPT V8, or generic regex fallback) and
orchestrates full directory-level carving with deduplication.
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from tinker_tailor.carver.leveldb import parse_sstable, read_varint
from tinker_tailor.carver.claude import carve_claude_chats
from tinker_tailor.carver.chatgpt import carve_v8_structured, carve_keyword_fallback
from tinker_tailor.carver.generic import carve_generic_chats


def carve_value(value: bytes, bot_name: str, mtime: float = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Carve chat data from a single LevelDB value blob.

    Dispatches to the Claude TipTap carver for Claude data, the V8
    structured parser for ChatGPT, and falls back to keyword scanning
    then generic regex carving.
    """
    if "claude" in bot_name.lower():
        return carve_claude_chats(value, mtime)

    prompts, conversations = carve_v8_structured(value, bot_name, mtime)

    if not conversations:
        prompts, conversations = carve_keyword_fallback(value, bot_name, mtime)

    if not prompts and not conversations:
        return carve_generic_chats(value, bot_name, mtime)

    return prompts, conversations


def carve_leveldb_directory(
    leveldb_dir: str,
    bot_name: str,
    warnings_list: Optional[List] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Carve all chat data from a LevelDB directory.

    Parses every SSTable (.ldb/.sst) and WAL log (.log), feeds each
    value blob through the carver engine, and deduplicates conversations
    by (id, title) keeping the version with the most messages.
    """
    prompts = []
    all_convs = []

    if not leveldb_dir or not os.path.exists(leveldb_dir):
        return prompts, all_convs

    try:
        for filename in os.listdir(leveldb_dir):
            if not filename.endswith(('.log', '.ldb', '.sst')):
                continue

            file_path = os.path.join(leveldb_dir, filename)
            try:
                entries = []
                if filename.endswith(('.ldb', '.sst')):
                    entries = parse_sstable(file_path)
                else:
                    with open(file_path, 'rb') as f:
                        log_content = f.read()
                    entries = [(b"wal_entry", log_content)]

                mtime = os.path.getmtime(file_path)
                for key, value in entries:
                    if len(value) < 100:
                        continue
                    v_prompts, v_convs = carve_value(value, bot_name, mtime)
                    prompts.extend(v_prompts)
                    all_convs.extend(v_convs)
            except PermissionError:
                if warnings_list is not None and "tcc_permission_denied" not in warnings_list:
                    warnings_list.append("tcc_permission_denied")
            except Exception:
                continue

        deduped = {}
        for c in all_convs:
            conv_key = (c["id"], c["title"])
            if conv_key not in deduped or len(c["messages"]) > len(deduped[conv_key]["messages"]):
                deduped[conv_key] = c
        conversations = list(deduped.values())

    except PermissionError:
        if warnings_list is not None and "tcc_permission_denied" not in warnings_list:
            warnings_list.append("tcc_permission_denied")
        conversations = []
    except Exception:
        conversations = []

    return prompts, conversations


def carve_cursor_chats(warnings_list: Optional[List] = None) -> Tuple[List[Dict], List[Dict]]:
    """Carve Cursor IDE agent transcript JSONL files."""
    prompts = []
    conversations = []
    home = os.path.expanduser("~")
    cursor_projects_dir = os.path.join(home, ".cursor", "projects")
    if not os.path.exists(cursor_projects_dir):
        return prompts, conversations

    try:
        for root, dirs, files in os.walk(cursor_projects_dir):
            for f in files:
                if f.endswith(".jsonl") and "agent-transcripts" in root:
                    file_path = os.path.join(root, f)
                    try:
                        messages = []
                        mtime = os.path.getmtime(file_path)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as jf:
                            for line in jf:
                                if not line.strip():
                                    continue
                                try:
                                    data = json.loads(line)
                                    role = data.get("role", "")
                                    msg_data = data.get("message", {})
                                    content_list = msg_data.get("content", [])
                                    text_parts = []
                                    for part in content_list:
                                        if part.get("type") == "text":
                                            text_parts.append(part.get("text", ""))

                                    msg_text = "\n".join(text_parts).strip()
                                    if "<user_query>" in msg_text:
                                        uq = re.search(r'<user_query>\n?(.*?)\n?</user_query>', msg_text, re.DOTALL)
                                        if uq:
                                            msg_text = uq.group(1).strip()

                                    if msg_text:
                                        messages.append({
                                            "id": f"cursor-{f}-{len(messages)}",
                                            "text": msg_text,
                                            "index": len(messages) + 1,
                                            "role": role if role else "user",
                                        })
                                        prompts.append({
                                            "bot": "cursor",
                                            "role": role if role else "user",
                                            "parts": [msg_text],
                                            "deleted": True,
                                            "offset": len(prompts),
                                            "timestamp": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                                        })
                                except Exception:
                                    pass
                        if messages:
                            parent_dir = os.path.dirname(file_path)
                            composer_id = os.path.basename(parent_dir)
                            conversations.append({
                                "id": composer_id,
                                "title": f"Cursor Chat ({composer_id[:8]})",
                                "bot": "cursor",
                                "messages": messages,
                                "offset": 0,
                                "mtime": mtime,
                            })
                    except Exception:
                        pass
    except Exception:
        pass
    return prompts, conversations
