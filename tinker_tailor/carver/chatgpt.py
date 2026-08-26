"""
ChatGPT / V8-Serialized Chat Carver

Recovers ChatGPT conversations from Chromium IndexedDB by parsing
V8's internal serialization format. ChatGPT stores its message tree
as a V8-serialized structured clone in IndexedDB, using:

- Smi-shifted array indices (encoded = actual << 1)
- OneByteString tag (0x22) and TwoByteString tag (0x63, UTF-16LE)
- Nesting depth tracking with 0x6f (Object), 0x61 (Array), 0x7b (ObjectEnd)
- Role inference from index parity (odd = user, even = assistant)

This module also handles the fallback keyword carver used when the
structured V8 pattern is not found.
"""

import re
import time
from datetime import datetime
from typing import Dict, List, Tuple

from tinker_tailor.carver.leveldb import read_varint


def carve_v8_structured(value: bytes, bot_name: str, mtime: float = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Carve chat messages using V8 structured array pattern matching.

    Searches for the V8 binary pattern b"\\x22\\x08messages\\x61" which marks
    the start of a serialized messages array in ChatGPT's IndexedDB schema.

    Returns (prompts, conversations).
    """
    prompts = []
    conversations = []

    v8_pattern = b"\x22\x08messages\x61"
    pos = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    while True:
        pos = value.find(v8_pattern, pos)
        if pos == -1:
            break

        try:
            val_pos = pos + len(v8_pattern)
            array_len, next_pos = read_varint(value, val_pos)

            title = "Unknown Chat"
            title_pattern = b"\x22\x05title\x22"
            title_pos = value.rfind(title_pattern, max(0, pos - 600), pos)
            if title_pos != -1:
                t_val_pos = title_pos + len(title_pattern)
                t_len, t_next_pos = read_varint(value, t_val_pos)
                title = value[t_next_pos : t_next_pos + t_len].decode('utf-8', errors='ignore')

            conv_id = "Unknown ID"
            id_pattern = b"\x22\x02id\x22"
            id_pos = value.rfind(id_pattern, max(0, pos - 1000), pos)
            if id_pos != -1:
                id_val_pos = id_pos + len(id_pattern)
                id_len, id_next_pos = read_varint(value, id_val_pos)
                conv_id = value[id_next_pos : id_next_pos + id_len].decode('utf-8', errors='ignore')

            messages = []
            curr_pos = next_pos

            for _ in range(array_len):
                while curr_pos < len(value) and value[curr_pos] != 0x49:
                    curr_pos += 1
                if curr_pos >= len(value):
                    break
                curr_pos += 1
                idx, curr_pos = read_varint(value, curr_pos)

                if curr_pos >= len(value) or value[curr_pos] != 0x6f:
                    break
                curr_pos += 1

                msg_id = ""
                msg_text = ""

                depth = 0
                for _ in range(1000):
                    if curr_pos >= len(value):
                        break
                    b = value[curr_pos]

                    if b == 0x7b:
                        curr_pos += 1
                        if depth == 0:
                            break
                        else:
                            depth -= 1
                        continue

                    if b in (0x6f, 0x61):
                        depth += 1
                        curr_pos += 1
                        continue

                    if b in (0x22, 0x63):
                        tag = b
                        curr_pos += 1
                        s_len, curr_pos = read_varint(value, curr_pos)

                        if tag == 0x22:
                            val_bytes = value[curr_pos : curr_pos + s_len]
                            curr_pos += s_len
                            if depth == 0:
                                val = val_bytes.decode('utf-8', errors='ignore')
                        else:
                            val_bytes = value[curr_pos : curr_pos + s_len]
                            curr_pos += s_len
                            if depth == 0:
                                val = val_bytes.decode('utf-16le', errors='ignore')

                        if depth == 0:
                            key = val

                            if curr_pos < len(value):
                                while curr_pos < len(value) and value[curr_pos] == 0:
                                    curr_pos += 1

                            if curr_pos < len(value):
                                v_tag = value[curr_pos]
                                if v_tag in (0x22, 0x63):
                                    curr_pos += 1
                                    v_len, curr_pos = read_varint(value, curr_pos)
                                    if v_tag == 0x22:
                                        v_val = value[curr_pos : curr_pos + v_len].decode('utf-8', errors='ignore')
                                        curr_pos += v_len
                                    else:
                                        v_val = value[curr_pos : curr_pos + v_len].decode('utf-16le', errors='ignore')
                                        curr_pos += v_len

                                    if key == "id":
                                        msg_id = v_val
                                    elif key == "text":
                                        msg_text = v_val
                                elif v_tag in (0x6f, 0x61):
                                    pass
                                elif v_tag == 0x4e:
                                    curr_pos += 9
                                elif v_tag in (0x49, 0x55):
                                    curr_pos += 1
                                    _, curr_pos = read_varint(value, curr_pos)
                                else:
                                    curr_pos += 1
                        continue

                    if b == 0x4e:
                        curr_pos += 9
                        continue
                    if b in (0x49, 0x55):
                        curr_pos += 1
                        _, curr_pos = read_varint(value, curr_pos)
                        continue
                    curr_pos += 1

                if msg_text.strip():
                    role = "user" if (idx // 2) % 2 == 1 else "assistant"
                    messages.append({
                        "id": msg_id or f"node-{conv_id}-{idx}",
                        "text": msg_text,
                        "index": idx,
                        "role": role
                    })

                    prompts.append({
                        "bot": bot_name,
                        "role": role,
                        "parts": [msg_text],
                        "deleted": True,
                        "offset": pos,
                        "timestamp": timestamp
                    })

            if messages:
                conversations.append({
                    "id": conv_id,
                    "title": title,
                    "bot": bot_name,
                    "messages": messages,
                    "offset": pos,
                    "mtime": mtime or time.time()
                })
        except Exception:
            pass

        pos += len(v8_pattern)

    return prompts, conversations


def carve_keyword_fallback(value: bytes, bot_name: str, mtime: float = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Fallback carver using V8 string tag scanning when the structured
    messages array pattern is not found. Extracts individual title/text/id
    fields and groups messages by preceding title.
    """
    prompts = []
    conversations = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    title_pattern = b"\x22\x05title\x22"
    text_pattern = b"\x22\x04text\x22"
    id_pattern = b"\x22\x02id\x22"

    titles = []
    pos = 0
    while True:
        pos = value.find(title_pattern, pos)
        if pos == -1:
            break
        val_pos = pos + len(title_pattern)
        try:
            length, next_pos = read_varint(value, val_pos)
            title_str = value[next_pos : next_pos + length].decode('utf-8', errors='ignore')
            titles.append((pos, title_str))
        except Exception:
            pass
        pos += len(title_pattern)

    messages = []
    pos = 0
    while True:
        pos = value.find(text_pattern, pos)
        if pos == -1:
            break
        val_pos = pos + len(text_pattern)
        try:
            length, next_pos = read_varint(value, val_pos)
            msg_str = value[next_pos : next_pos + length].decode('utf-8', errors='ignore')

            msg_id = "client-created-root"
            id_pos = value.rfind(id_pattern, max(0, pos - 150), pos)
            if id_pos != -1:
                id_val_pos = id_pos + len(id_pattern)
                id_len, id_next_pos = read_varint(value, id_val_pos)
                msg_id = value[id_next_pos : id_next_pos + id_len].decode('utf-8', errors='ignore')

            messages.append((pos, msg_id, msg_str))
        except Exception:
            pass
        pos += len(text_pattern)

    if messages:
        conv_groups = {}
        for m_pos, m_id, m_text in messages:
            if not m_text.strip():
                continue

            preceding_title = None
            for t_pos, t_str in reversed(titles):
                if t_pos < m_pos:
                    conv_id = "Unknown ID"
                    id_pos = value.rfind(id_pattern, max(0, t_pos - 150), t_pos)
                    if id_pos != -1:
                        id_val_pos = id_pos + len(id_pattern)
                        id_len, id_next_pos = read_varint(value, id_val_pos)
                        conv_id = value[id_next_pos : id_next_pos + id_len].decode('utf-8', errors='ignore')
                    preceding_title = (t_str, conv_id, t_pos)
                    break

            if preceding_title:
                t_str, conv_id, t_pos = preceding_title
                block_key = (conv_id, t_str, t_pos)
            else:
                block_key = ("Unknown ID", "Active Live Session", 0)

            if block_key not in conv_groups:
                conv_groups[block_key] = []
            conv_groups[block_key].append((m_id, m_text))

            role = "user"
            if len(conv_groups[block_key]) % 2 == 0:
                role = "assistant"

            prompts.append({
                "bot": bot_name,
                "role": role,
                "parts": [m_text],
                "deleted": True,
                "offset": m_pos,
                "timestamp": timestamp
            })

        for (conv_id, t_str, t_pos), msgs in conv_groups.items():
            if conv_id == "Unknown ID" and len(msgs) <= 1:
                continue
            msg_list = []
            for idx, (m_id, m_text) in enumerate(msgs):
                msg_list.append({
                    "id": m_id,
                    "text": m_text,
                    "index": idx + 1
                })
            conversations.append({
                "id": conv_id,
                "title": t_str,
                "bot": bot_name,
                "messages": msg_list,
                "offset": t_pos,
                "mtime": mtime or time.time()
            })

    return prompts, conversations
