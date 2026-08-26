"""
Ground Truth Generator

Creates synthetic but realistic LevelDB entries matching each LLM
platform's V8 serialization schema. These known-content entries
enable precise measurement of precision, recall, and F1 for each
carver module.

Supported schemas:
- ChatGPT: V8 structured message tree with Smi-shifted indices
- Claude: TipTap ProseMirror editor state JSON
- Generic: Simple JSON content/text fields
"""

import json
import os
import struct
import time
import uuid
from typing import Dict, List, Tuple


def _encode_varint(value: int) -> bytes:
    """Encode an integer as a Protocol Buffer-style varint."""
    buf = bytearray()
    while value > 0x7f:
        buf.append((value & 0x7f) | 0x80)
        value >>= 7
    buf.append(value & 0x7f)
    return bytes(buf)


def _v8_onebyte_string(key: str) -> bytes:
    """Encode a string as a V8 OneByteString (tag 0x22)."""
    encoded = key.encode('utf-8')
    return b'\x22' + _encode_varint(len(encoded)) + encoded


def generate_chatgpt_entry(
    conversation_id: str,
    title: str,
    messages: List[Dict],
) -> bytes:
    """
    Generate a synthetic V8-serialized ChatGPT conversation.

    Each message dict should have 'role' and 'text' fields.
    Produces a binary blob that the V8 structured carver can parse.
    """
    parts = []

    parts.append(_v8_onebyte_string("id"))
    parts.append(_v8_onebyte_string(conversation_id))

    parts.append(_v8_onebyte_string("title"))
    parts.append(_v8_onebyte_string(title))

    parts.append(b"\x22\x08messages\x61")
    parts.append(_encode_varint(len(messages)))

    for idx, msg in enumerate(messages):
        smi_idx = (idx + 1) * 2
        parts.append(b'\x49')
        parts.append(_encode_varint(smi_idx))

        parts.append(b'\x6f')

        parts.append(_v8_onebyte_string("id"))
        msg_id = msg.get("id", f"msg-{uuid.uuid4().hex[:8]}")
        parts.append(_v8_onebyte_string(msg_id))

        parts.append(_v8_onebyte_string("text"))
        parts.append(_v8_onebyte_string(msg["text"]))

        parts.append(b'\x7b')

    return b''.join(parts)


def generate_claude_entry(drafts: List[str]) -> bytes:
    """
    Generate a synthetic Claude TipTap editor state entry.

    Each string in `drafts` becomes a separate tipTapEditorState object,
    simulating the keystroke trail that Claude stores in IndexedDB.
    """
    entries = []
    for draft in drafts:
        tiptap_doc = {
            "tipTapEditorState": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": draft}
                        ]
                    }
                ]
            }
        }
        entries.append(json.dumps(tiptap_doc))

    return ("\x00".join(entries)).encode('utf-8')


def generate_generic_entry(prompts: List[str], field: str = "content") -> bytes:
    """
    Generate a synthetic generic JSON entry for fallback carver testing.

    Creates a series of JSON objects with the specified field name
    containing the prompt text.
    """
    entries = []
    for prompt in prompts:
        entries.append(json.dumps({field: prompt}))
    return ("\n".join(entries)).encode('utf-8')


class GroundTruthDataset:
    """
    A collection of ground-truth test cases for evaluation.

    Each test case includes the raw bytes, the expected carver output,
    and metadata about the platform and content.
    """

    def __init__(self):
        self.cases: List[Dict] = []

    def add_chatgpt_case(
        self,
        title: str,
        messages: List[Dict],
        conversation_id: str = None,
    ):
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        raw = generate_chatgpt_entry(conversation_id, title, messages)
        self.cases.append({
            "platform": "chatgpt",
            "bot_name": "chatgpt",
            "raw_bytes": raw,
            "expected_messages": messages,
            "expected_title": title,
            "conversation_id": conversation_id,
        })

    def add_claude_case(self, drafts: List[str]):
        raw = generate_claude_entry(drafts)
        self.cases.append({
            "platform": "claude",
            "bot_name": "claude",
            "raw_bytes": raw,
            "expected_drafts": drafts,
        })

    def add_generic_case(self, prompts: List[str], bot_name: str = "deepseek"):
        raw = generate_generic_entry(prompts)
        self.cases.append({
            "platform": "generic",
            "bot_name": bot_name,
            "raw_bytes": raw,
            "expected_prompts": prompts,
        })

    def build_standard_dataset(self) -> "GroundTruthDataset":
        """Populate with a standard set of test cases across all platforms."""

        self.add_chatgpt_case(
            title="Python debugging help",
            messages=[
                {"role": "user", "text": "How do I fix a segfault in my C extension module?", "id": "msg-001"},
                {"role": "assistant", "text": "A segfault in a C extension usually means...", "id": "msg-002"},
                {"role": "user", "text": "What about when using numpy arrays?", "id": "msg-003"},
            ],
        )

        self.add_chatgpt_case(
            title="API key rotation strategy",
            messages=[
                {"role": "user", "text": "What's the best practice for rotating API keys in production?", "id": "msg-010"},
                {"role": "assistant", "text": "For API key rotation, consider a dual-key approach...", "id": "msg-011"},
            ],
        )

        self.add_chatgpt_case(
            title="SQL query optimization",
            messages=[
                {"role": "user", "text": "My database password is hunter2 and the query SELECT * FROM users WHERE...", "id": "msg-020"},
                {"role": "assistant", "text": "I notice you included a password in your message...", "id": "msg-021"},
            ],
        )

        self.add_claude_case([
            "Write me a Python script that",
            "Write me a Python script that parses",
            "Write me a Python script that parses CSV files and generates a summary report",
        ])

        self.add_claude_case([
            "My AWS access key is AKIAIOSFODNN7EXAMPLE and I need help with",
        ])

        self.add_generic_case([
            "Explain the difference between TCP and UDP protocols",
            "What are the security implications of using WebSockets?",
        ], bot_name="deepseek")

        self.add_generic_case([
            "How does TLS 1.3 differ from TLS 1.2?",
        ], bot_name="perplexity")

        return self

    def __len__(self):
        return len(self.cases)

    def __iter__(self):
        return iter(self.cases)
