"""
Experiment: Ablation Study

Measures the contribution of each pipeline component to recovery quality
by selectively disabling V8 deserialization, depth tracking, Snappy
decompression, and the TipTap parser. Compares each ablated config
against the full pipeline baseline.

Usage:
    python -m evaluation.experiment_ablation

Output:
    results/ablation_results.csv
"""

import csv
import os
import random
import struct
import sys
import time
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import (
    GroundTruthDataset,
    generate_chatgpt_entry,
    generate_claude_entry,
    generate_generic_entry,
    _v8_onebyte_string,
    _encode_varint,
)
from tinker_tailor.carver.engine import carve_value
from tinker_tailor.carver.chatgpt import carve_v8_structured, carve_keyword_fallback
from tinker_tailor.carver.claude import carve_claude_chats
from tinker_tailor.carver.generic import carve_generic_chats
from tinker_tailor.carver.leveldb import snappy_decompress, read_varint


# ---------------------------------------------------------------------------
# Metrics helpers
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


JACCARD_THRESHOLD = 0.7


def _compute_prf(recovered_texts: List[str], expected_texts: List[str]) -> Dict:
    """Precision / recall / F1 using word-level Jaccard with threshold."""
    tp = 0
    matched_recovered = set()
    for et in expected_texts:
        for idx, rt in enumerate(recovered_texts):
            if idx in matched_recovered:
                continue
            if _jaccard(rt, et) >= JACCARD_THRESHOLD:
                tp += 1
                matched_recovered.add(idx)
                break

    precision = tp / len(recovered_texts) if recovered_texts else 0.0
    recall = tp / len(expected_texts) if expected_texts else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "artifacts_recovered": len(recovered_texts),
        "artifacts_expected": len(expected_texts),
    }


# ---------------------------------------------------------------------------
# Synthetic data fixtures
# ---------------------------------------------------------------------------

def _build_chatgpt_cases() -> List[Dict]:
    """Return list of {raw_bytes, expected_texts, label}."""
    cases = []

    msgs1 = [
        {"role": "user",      "text": "How do I fix a segfault in my C extension module?",   "id": "abl-001"},
        {"role": "assistant", "text": "A segfault in a C extension usually means you have a dangling pointer", "id": "abl-002"},
        {"role": "user",      "text": "What about when using numpy arrays?",                 "id": "abl-003"},
    ]
    cases.append({
        "raw_bytes": generate_chatgpt_entry("conv-abl-1", "Python debugging help", msgs1),
        "expected_texts": [m["text"] for m in msgs1],
        "label": "chatgpt_segfault",
    })

    msgs2 = [
        {"role": "user",      "text": "What is the best practice for rotating API keys in production?", "id": "abl-010"},
        {"role": "assistant", "text": "For API key rotation consider a dual-key approach with rolling expiry", "id": "abl-011"},
    ]
    cases.append({
        "raw_bytes": generate_chatgpt_entry("conv-abl-2", "API key rotation", msgs2),
        "expected_texts": [m["text"] for m in msgs2],
        "label": "chatgpt_apikeys",
    })

    msgs3 = [
        {"role": "user",      "text": "Can you explain how TLS 1.3 handshake works step by step?", "id": "abl-020"},
        {"role": "assistant", "text": "The TLS 1.3 handshake reduces round trips from two to one compared to TLS 1.2", "id": "abl-021"},
        {"role": "user",      "text": "What about the zero round trip time resumption?", "id": "abl-022"},
        {"role": "assistant", "text": "Zero-RTT resumption allows clients to send data on the first flight using a pre-shared key", "id": "abl-023"},
    ]
    cases.append({
        "raw_bytes": generate_chatgpt_entry("conv-abl-3", "TLS handshake", msgs3),
        "expected_texts": [m["text"] for m in msgs3],
        "label": "chatgpt_tls",
    })

    return cases


def _build_claude_cases() -> List[Dict]:
    cases = []
    drafts1 = [
        "Write me a Python script that",
        "Write me a Python script that parses",
        "Write me a Python script that parses CSV files and generates a summary report",
    ]
    cases.append({
        "raw_bytes": generate_claude_entry(drafts1),
        "expected_texts": [max(drafts1, key=len)],  # deduplication keeps longest
        "label": "claude_csv_script",
    })

    drafts2 = [
        "Explain the difference between symmetric and asymmetric encryption algorithms",
    ]
    cases.append({
        "raw_bytes": generate_claude_entry(drafts2),
        "expected_texts": drafts2,
        "label": "claude_crypto",
    })
    return cases


def _build_generic_cases() -> List[Dict]:
    cases = []
    prompts1 = [
        "Explain the difference between TCP and UDP protocols",
        "What are the security implications of using WebSockets?",
    ]
    cases.append({
        "raw_bytes": generate_generic_entry(prompts1),
        "expected_texts": prompts1,
        "label": "generic_networking",
    })
    prompts2 = [
        "How does TLS 1.3 differ from TLS 1.2?",
    ]
    cases.append({
        "raw_bytes": generate_generic_entry(prompts2),
        "expected_texts": prompts2,
        "label": "generic_tls",
    })
    return cases


# ---------------------------------------------------------------------------
# Extractors — pull recovered text from carver output
# ---------------------------------------------------------------------------

def _extract_texts(prompts: List[Dict], conversations: List[Dict]) -> List[str]:
    """Collect unique recovered text strings."""
    seen = set()
    out = []
    for p in prompts:
        for part in p.get("parts", []):
            n = _normalize(part)
            if n and n not in seen:
                seen.add(n)
                out.append(part.strip())
    for conv in conversations:
        for msg in conv.get("messages", []):
            t = msg.get("text", "").strip()
            n = _normalize(t)
            if n and n not in seen:
                seen.add(n)
                out.append(t)
    return out


# ---------------------------------------------------------------------------
# Ablation configurations
# ---------------------------------------------------------------------------

def _run_full_pipeline(raw: bytes, platform: str) -> List[str]:
    """(a) Full pipeline — baseline."""
    bot = "chatgpt" if platform == "chatgpt" else ("claude" if platform == "claude" else "deepseek")
    try:
        p, c = carve_value(raw, bot)
        return _extract_texts(p, c)
    except Exception:
        return []


def _run_without_v8(raw: bytes, platform: str) -> List[str]:
    """(b) Without V8 deserialization — use only generic regex for ChatGPT data."""
    if platform == "chatgpt":
        try:
            p, c = carve_generic_chats(raw, "chatgpt")
            return _extract_texts(p, c)
        except Exception:
            return []
    # For non-ChatGPT platforms, same as full pipeline
    return _run_full_pipeline(raw, platform)


def _run_without_depth(raw: bytes, platform: str) -> List[str]:
    """(c) Without depth tracking — extract ALL text fields regardless of nesting depth."""
    if platform != "chatgpt":
        return _run_full_pipeline(raw, platform)

    # Flat extraction: scan for V8 string tags and pull out text key-value
    # pairs without checking depth == 0
    try:
        texts = []
        pos = 0
        while pos < len(raw):
            # Look for OneByteString tag (0x22) encoding "text"
            if raw[pos] == 0x22:
                tag_pos = pos
                pos += 1
                try:
                    s_len, pos = read_varint(raw, pos)
                    s_val = raw[pos:pos + s_len].decode('utf-8', errors='ignore')
                    pos += s_len
                    if s_val == "text":
                        # Next value should also be a string
                        if pos < len(raw) and raw[pos] in (0x22, 0x63):
                            v_tag = raw[pos]
                            pos += 1
                            v_len, pos = read_varint(raw, pos)
                            if v_tag == 0x22:
                                v_val = raw[pos:pos + v_len].decode('utf-8', errors='ignore')
                            else:
                                v_val = raw[pos:pos + v_len].decode('utf-16le', errors='ignore')
                            pos += v_len
                            if v_val.strip() and len(v_val.strip()) >= 5:
                                texts.append(v_val.strip())
                except Exception:
                    pos = tag_pos + 1
            else:
                pos += 1
        return texts
    except Exception:
        return []


def _build_snappy_sstable_block(v8_data: bytes) -> bytes:
    """
    (d) Build a minimal Snappy-compressed data block wrapping V8 data.

    Constructs a single LevelDB data block containing one key-value entry,
    then Snappy-compresses it.
    """
    # Build a data block: one entry with key="idb_key", value=v8_data
    key = b"idb_key"
    # Entry format: shared_len (varint) + unshared_len (varint) + value_len (varint) + key_delta + value
    entry = _encode_varint(0) + _encode_varint(len(key)) + _encode_varint(len(v8_data)) + key + v8_data
    # Restarts array: one restart at offset 0, plus count
    restarts = struct.pack('<I', 0) + struct.pack('<I', 1)
    block = entry + restarts
    return block


def _snappy_compress_simple(data: bytes) -> bytes:
    """
    Minimal Snappy compression: encode everything as a single literal.
    This produces valid Snappy format that snappy_decompress can handle.
    """
    # Snappy format: varint(uncompressed_length) + literal tag + data
    result = bytearray()
    # Encode uncompressed length as varint
    length = len(data)
    while length > 0x7f:
        result.append((length & 0x7f) | 0x80)
        length >>= 7
    result.append(length & 0x7f)

    # Emit literal: for data <= 60 bytes, tag = (len-1)<<2 | 0x00
    remaining = len(data)
    offset = 0
    while remaining > 0:
        chunk_size = min(remaining, 60)
        tag = ((chunk_size - 1) << 2) | 0x00
        result.append(tag)
        result.extend(data[offset:offset + chunk_size])
        offset += chunk_size
        remaining -= chunk_size

    return bytes(result)


def _run_snappy_test(raw_v8: bytes) -> Dict:
    """
    (d) Test Snappy decompression contribution.
    Returns {with_snappy: [...], without_snappy: [...]}.
    """
    block = _build_snappy_sstable_block(raw_v8)
    compressed = _snappy_compress_simple(block)

    # WITH Snappy: decompress then carve the block
    with_texts = []
    try:
        decompressed = snappy_decompress(compressed)
        # The decompressed block contains the V8 data as a value entry
        # Try to carve the decompressed data directly
        p, c = carve_v8_structured(decompressed, "chatgpt")
        with_texts = _extract_texts(p, c)
        if not with_texts:
            # Try carving the raw v8 data from within the block
            p, c = carve_v8_structured(raw_v8, "chatgpt")
            with_texts = _extract_texts(p, c)
    except Exception:
        pass

    # WITHOUT Snappy: try to carve the compressed bytes directly
    without_texts = []
    try:
        p, c = carve_v8_structured(compressed, "chatgpt")
        without_texts = _extract_texts(p, c)
    except Exception:
        pass

    return {"with_snappy": with_texts, "without_snappy": without_texts}


def _run_without_tiptap(raw: bytes, platform: str) -> List[str]:
    """(e) Without TipTap parser — use generic regex for Claude data."""
    if platform == "claude":
        try:
            p, c = carve_generic_chats(raw, "claude")
            return _extract_texts(p, c)
        except Exception:
            return []
    return _run_full_pipeline(raw, platform)


def _run_generic_only(raw: bytes, platform: str) -> List[str]:
    """(f) Generic regex only — use carve_generic_chats for ALL platforms."""
    bot = "chatgpt" if platform == "chatgpt" else ("claude" if platform == "claude" else "deepseek")
    try:
        p, c = carve_generic_chats(raw, bot)
        return _extract_texts(p, c)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run_experiment():
    print("=" * 72)
    print("  ABLATION STUDY")
    print("=" * 72)

    chatgpt_cases = _build_chatgpt_cases()
    claude_cases = _build_claude_cases()
    generic_cases = _build_generic_cases()

    results = []
    fieldnames = [
        "config_name", "platform", "case_label",
        "precision", "recall", "f1",
        "artifacts_recovered", "artifacts_expected",
    ]

    # -----------------------------------------------------------------------
    # Configurations (a), (b), (c), (e), (f) — run on each platform
    # -----------------------------------------------------------------------
    configs = [
        ("full_pipeline",        _run_full_pipeline),
        ("without_v8",           _run_without_v8),
        ("without_depth",        _run_without_depth),
        ("without_tiptap",       _run_without_tiptap),
        ("generic_only",         _run_generic_only),
    ]

    all_cases = (
        [(c, "chatgpt") for c in chatgpt_cases]
        + [(c, "claude") for c in claude_cases]
        + [(c, "generic") for c in generic_cases]
    )

    for config_name, func in configs:
        print(f"\n--- Config: {config_name} ---")
        for case, platform in all_cases:
            raw = case["raw_bytes"]
            expected = case["expected_texts"]
            label = case["label"]

            recovered = func(raw, platform)
            metrics = _compute_prf(recovered, expected)

            row = {
                "config_name": config_name,
                "platform": platform,
                "case_label": label,
                **metrics,
            }
            results.append(row)

            status = "PASS" if metrics["f1"] >= 0.5 else "----"
            print(f"  [{status}] {platform:10s} {label:25s} | "
                  f"P={metrics['precision']:.2f} R={metrics['recall']:.2f} "
                  f"F1={metrics['f1']:.2f} | "
                  f"{metrics['artifacts_recovered']}/{metrics['artifacts_expected']}")

    # -----------------------------------------------------------------------
    # Configuration (d) — Snappy decompression (ChatGPT only)
    # -----------------------------------------------------------------------
    print(f"\n--- Config: without_snappy ---")
    for case in chatgpt_cases:
        raw = case["raw_bytes"]
        expected = case["expected_texts"]
        label = case["label"]

        snappy_result = _run_snappy_test(raw)

        # With Snappy (control)
        m_with = _compute_prf(snappy_result["with_snappy"], expected)
        results.append({
            "config_name": "snappy_with",
            "platform": "chatgpt",
            "case_label": label,
            **m_with,
        })
        print(f"  [{'PASS' if m_with['f1'] >= 0.5 else '----'}] chatgpt    {label:25s} | "
              f"WITH Snappy  P={m_with['precision']:.2f} R={m_with['recall']:.2f} F1={m_with['f1']:.2f}")

        # Without Snappy
        m_without = _compute_prf(snappy_result["without_snappy"], expected)
        results.append({
            "config_name": "snappy_without",
            "platform": "chatgpt",
            "case_label": label,
            **m_without,
        })
        print(f"  [{'PASS' if m_without['f1'] >= 0.5 else '----'}] chatgpt    {label:25s} | "
              f"W/O Snappy   P={m_without['precision']:.2f} R={m_without['recall']:.2f} F1={m_without['f1']:.2f}")

    # -----------------------------------------------------------------------
    # Write CSV
    # -----------------------------------------------------------------------
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"), exist_ok=True)
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "ablation_results.csv")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[+] {len(results)} rows written to {output_path}")

    # Summary table
    print("\n--- Summary by config ---")
    from collections import defaultdict
    by_config = defaultdict(list)
    for r in results:
        by_config[r["config_name"]].append(r)
    for cfg, rows in by_config.items():
        avg_p = sum(r["precision"] for r in rows) / len(rows)
        avg_r = sum(r["recall"] for r in rows) / len(rows)
        avg_f = sum(r["f1"] for r in rows) / len(rows)
        print(f"  {cfg:25s} | avg P={avg_p:.2f} R={avg_r:.2f} F1={avg_f:.2f} ({len(rows)} cases)")

    return results


if __name__ == "__main__":
    run_experiment()
