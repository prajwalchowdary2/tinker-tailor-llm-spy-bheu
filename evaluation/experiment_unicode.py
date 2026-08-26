"""
Experiment: Unicode Recovery

Tests recovery of non-ASCII content (emoji, CJK, Devanagari, math
symbols, mixed multilingual) across ChatGPT V8, Claude TipTap, and
generic carvers.  Checks whether OneByteString (0x22, UTF-8) and
TwoByteString (0x63, UTF-16LE) encodings are handled correctly.

Usage:
    python -m evaluation.experiment_unicode

Output:
    results/unicode_results.csv
"""

import csv
import os
import struct
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import (
    generate_chatgpt_entry,
    generate_claude_entry,
    generate_generic_entry,
    _v8_onebyte_string,
    _encode_varint,
)
from tinker_tailor.carver.chatgpt import carve_v8_structured
from tinker_tailor.carver.claude import carve_claude_chats
from tinker_tailor.carver.generic import carve_generic_chats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _jaccard(a: str, b: str) -> float:
    wa = set(_normalize(a).split())
    wb = set(_normalize(b).split())
    if not wa and not wb:
        return 1.0
    union = wa | wb
    return len(wa & wb) / len(union) if union else 0.0


def _v8_twobyte_string(text: str) -> bytes:
    """Encode a string as a V8 TwoByteString (tag 0x63, UTF-16LE)."""
    encoded = text.encode('utf-16le')
    byte_len = len(encoded)
    return b'\x63' + _encode_varint(byte_len) + encoded


def _generate_chatgpt_entry_twobyte(
    conversation_id: str,
    title: str,
    messages: List[Dict],
) -> bytes:
    """
    Generate a ChatGPT V8 blob using TwoByteString (0x63) for message text.
    Uses OneByteString for structural keys (id, title, messages, text) since
    those are always ASCII, but encodes the actual content values as
    TwoByteString (UTF-16LE).
    """
    parts = []

    # id key + value
    parts.append(_v8_onebyte_string("id"))
    parts.append(_v8_onebyte_string(conversation_id))

    # title key + value (use TwoByteString for title value too)
    parts.append(_v8_onebyte_string("title"))
    parts.append(_v8_twobyte_string(title))

    # messages array header
    parts.append(b"\x22\x08messages\x61")
    parts.append(_encode_varint(len(messages)))

    for idx, msg in enumerate(messages):
        smi_idx = (idx + 1) * 2
        parts.append(b'\x49')
        parts.append(_encode_varint(smi_idx))

        parts.append(b'\x6f')  # BeginObject

        # id field
        parts.append(_v8_onebyte_string("id"))
        msg_id = msg.get("id", f"msg-u-{idx}")
        parts.append(_v8_onebyte_string(msg_id))

        # text field — use TwoByteString for the value
        parts.append(_v8_onebyte_string("text"))
        parts.append(_v8_twobyte_string(msg["text"]))

        parts.append(b'\x7b')  # EndObject

    return b''.join(parts)


def _is_ascii_safe(text: str) -> bool:
    """Check if text can be fully encoded as ASCII/Latin-1."""
    try:
        text.encode('latin-1')
        return True
    except UnicodeEncodeError:
        return False


def _extract_recovered_texts(prompts, conversations) -> List[str]:
    """Collect unique recovered text strings."""
    seen = set()
    out = []
    for p in prompts:
        for part in p.get("parts", []):
            t = part.strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    for conv in conversations:
        for msg in conv.get("messages", []):
            t = msg.get("text", "").strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

UNICODE_CASES = [
    {
        "language": "English",
        "text": "How do I fix a segfault in my C program?",
        "encoding_note": "ASCII-only",
    },
    {
        "language": "Emoji",
        "text": "Help me debug this \U0001f41b in my code \U0001f4bb it keeps crashing \U0001f4a5",
        "encoding_note": "Emoji (astral plane)",
    },
    {
        "language": "Hindi",
        "text": "मुझे Python में sorting algorithm समझाइए",
        "encoding_note": "Devanagari script",
    },
    {
        "language": "Chinese",
        "text": "请帮我优化这个SQL查询语句",
        "encoding_note": "CJK Unified Ideographs",
    },
    {
        "language": "Japanese",
        "text": "このエラーメッセージの意味を教えてください",
        "encoding_note": "Hiragana + Katakana",
    },
    {
        "language": "Math",
        "text": "Prove that ∀x∈ℝ, |sin(x)| ≤ 1 using the ε-δ definition",
        "encoding_note": "Mathematical symbols + Greek",
    },
    {
        "language": "Mixed",
        "text": "Debug this código \U0001f527: def hello(): print('こんにちは世界 \U0001f30d')",
        "encoding_note": "Latin + Emoji + CJK + Hiragana",
    },
]


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment():
    print("=" * 72)
    print("  UNICODE RECOVERY EXPERIMENT")
    print("=" * 72)

    results = []
    fieldnames = [
        "language", "encoding_type", "platform",
        "recovered_text", "match", "jaccard_score",
        "note",
    ]

    for case in UNICODE_CASES:
        lang = case["language"]
        text = case["text"]
        enc_note = case["encoding_note"]
        ascii_safe = _is_ascii_safe(text)

        print(f"\n--- {lang} ({enc_note}) ---")
        print(f"    Input: {text[:60]}{'...' if len(text) > 60 else ''}")

        # ---------------------------------------------------------------
        # ChatGPT — OneByteString (standard generate_chatgpt_entry uses UTF-8 bytes)
        # ---------------------------------------------------------------
        msgs = [{"role": "user", "text": text, "id": f"uni-{lang[:3]}-1"}]

        # Try OneByteString encoding (UTF-8 bytes with 0x22 tag)
        try:
            raw_one = generate_chatgpt_entry(f"conv-uni-{lang}", f"Unicode {lang}", msgs)
            p, c = carve_v8_structured(raw_one, "chatgpt")
            recovered_one = _extract_recovered_texts(p, c)
        except Exception as e:
            recovered_one = []

        best_match_one = ""
        best_jaccard_one = 0.0
        for rt in recovered_one:
            j = _jaccard(rt, text)
            if j > best_jaccard_one:
                best_jaccard_one = j
                best_match_one = rt

        results.append({
            "language": lang,
            "encoding_type": "OneByteString (0x22 UTF-8)",
            "platform": "chatgpt",
            "recovered_text": best_match_one[:200] if best_match_one else "(none)",
            "match": best_jaccard_one >= 0.7,
            "jaccard_score": round(best_jaccard_one, 4),
            "note": "ASCII-safe" if ascii_safe else "non-ASCII via UTF-8",
        })
        status = "PASS" if best_jaccard_one >= 0.7 else "FAIL"
        print(f"  [{status}] ChatGPT OneByteString  J={best_jaccard_one:.2f}  recovered={len(recovered_one)} texts")

        # Try TwoByteString encoding (UTF-16LE with 0x63 tag)
        try:
            raw_two = _generate_chatgpt_entry_twobyte(f"conv-uni2-{lang}", f"Unicode {lang}", msgs)
            p2, c2 = carve_v8_structured(raw_two, "chatgpt")
            recovered_two = _extract_recovered_texts(p2, c2)
        except Exception as e:
            recovered_two = []

        best_match_two = ""
        best_jaccard_two = 0.0
        for rt in recovered_two:
            j = _jaccard(rt, text)
            if j > best_jaccard_two:
                best_jaccard_two = j
                best_match_two = rt

        results.append({
            "language": lang,
            "encoding_type": "TwoByteString (0x63 UTF-16LE)",
            "platform": "chatgpt",
            "recovered_text": best_match_two[:200] if best_match_two else "(none)",
            "match": best_jaccard_two >= 0.7,
            "jaccard_score": round(best_jaccard_two, 4),
            "note": "native V8 wide string",
        })
        status = "PASS" if best_jaccard_two >= 0.7 else "FAIL"
        print(f"  [{status}] ChatGPT TwoByteString  J={best_jaccard_two:.2f}  recovered={len(recovered_two)} texts")

        # ---------------------------------------------------------------
        # Claude — TipTap JSON (Unicode in JSON should work regardless)
        # ---------------------------------------------------------------
        try:
            raw_claude = generate_claude_entry([text])
            p3, c3 = carve_claude_chats(raw_claude)
            recovered_claude = _extract_recovered_texts(p3, c3)
        except Exception:
            recovered_claude = []

        best_match_cl = ""
        best_jaccard_cl = 0.0
        for rt in recovered_claude:
            j = _jaccard(rt, text)
            if j > best_jaccard_cl:
                best_jaccard_cl = j
                best_match_cl = rt

        results.append({
            "language": lang,
            "encoding_type": "TipTap JSON (UTF-8)",
            "platform": "claude",
            "recovered_text": best_match_cl[:200] if best_match_cl else "(none)",
            "match": best_jaccard_cl >= 0.7,
            "jaccard_score": round(best_jaccard_cl, 4),
            "note": "JSON handles Unicode natively",
        })
        status = "PASS" if best_jaccard_cl >= 0.7 else "FAIL"
        print(f"  [{status}] Claude TipTap          J={best_jaccard_cl:.2f}  recovered={len(recovered_claude)} texts")

        # ---------------------------------------------------------------
        # Generic — regex on JSON (content field)
        # ---------------------------------------------------------------
        try:
            raw_generic = generate_generic_entry([text])
            p4, c4 = carve_generic_chats(raw_generic, "deepseek")
            recovered_gen = _extract_recovered_texts(p4, c4)
        except Exception:
            recovered_gen = []

        best_match_gen = ""
        best_jaccard_gen = 0.0
        for rt in recovered_gen:
            j = _jaccard(rt, text)
            if j > best_jaccard_gen:
                best_jaccard_gen = j
                best_match_gen = rt

        results.append({
            "language": lang,
            "encoding_type": "Generic JSON regex",
            "platform": "generic",
            "recovered_text": best_match_gen[:200] if best_match_gen else "(none)",
            "match": best_jaccard_gen >= 0.7,
            "jaccard_score": round(best_jaccard_gen, 4),
            "note": "regex pattern on JSON content field",
        })
        status = "PASS" if best_jaccard_gen >= 0.7 else "FAIL"
        print(f"  [{status}] Generic regex           J={best_jaccard_gen:.2f}  recovered={len(recovered_gen)} texts")

    # -------------------------------------------------------------------
    # Write CSV
    # -------------------------------------------------------------------
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"), exist_ok=True)
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "unicode_results.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[+] {len(results)} rows written to {output_path}")

    # Summary
    total = len(results)
    matched = sum(1 for r in results if r["match"])
    print(f"\n--- Summary ---")
    print(f"  Total cases: {total}")
    print(f"  Matched (Jaccard >= 0.7): {matched} ({matched*100//total}%)")

    by_platform = {}
    for r in results:
        p = r["platform"]
        if p not in by_platform:
            by_platform[p] = {"total": 0, "matched": 0}
        by_platform[p]["total"] += 1
        if r["match"]:
            by_platform[p]["matched"] += 1
    for p, stats in by_platform.items():
        pct = stats["matched"] * 100 // stats["total"] if stats["total"] else 0
        print(f"  {p:12s}: {stats['matched']}/{stats['total']} matched ({pct}%)")

    return results


if __name__ == "__main__":
    run_experiment()
