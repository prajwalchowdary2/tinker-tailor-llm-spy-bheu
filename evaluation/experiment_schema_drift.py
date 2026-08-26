"""
Experiment: Schema-Drift Robustness

Motivation. The ChatGPT V8 carver (Section 5.3) is tuned to the schema we
observed: a top-level ``messages`` array whose elements are objects with
top-level ``id`` and ``text`` fields. A natural reviewer question is how
brittle this is to the platform silently changing its schema (a field
rename, a reordering, an extra layer of nesting, or a renamed array
anchor). This experiment measures that brittleness *without any real
browser data* by synthetically mutating the schema and running the actual
carver code (``carve_v8_structured`` plus the keyword fallback that the
engine invokes when the structured anchor is absent).

For each mutation we report:
  * structured-only recall  (carve_v8_structured alone), and
  * full-pipeline recall    (engine: structured -> keyword fallback -> generic),
so the table shows both where the primary parser breaks and how much of
that loss the fallback recovers.

Usage:
    python -m evaluation.experiment_schema_drift

Output:
    results/schema_drift_results.csv
"""

import csv
import os
import sys
import uuid
from typing import Callable, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ground_truth import _v8_onebyte_string, _encode_varint
from tinker_tailor.carver.engine import carve_value
from tinker_tailor.carver.chatgpt import carve_v8_structured


# ---------------------------------------------------------------------------
# Metrics
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


def _recall(recovered: List[str], expected: List[str]) -> float:
    matched = set()
    tp = 0
    for et in expected:
        for i, rt in enumerate(recovered):
            if i in matched:
                continue
            if _jaccard(rt, et) >= JACCARD_THRESHOLD:
                tp += 1
                matched.add(i)
                break
    return tp / len(expected) if expected else 0.0


def _extract_texts(prompts: List[Dict], conversations: List[Dict]) -> List[str]:
    seen, out = set(), []
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
# Flexible V8 conversation generator with schema-mutation knobs
# ---------------------------------------------------------------------------

def _v8_obj(pairs: List[bytes]) -> bytes:
    """Wrap key/value byte-pairs in BeginObject(0x6f)/EndObject(0x7b)."""
    return b"\x6f" + b"".join(pairs) + b"\x7b"


def build_conv(
    messages: List[Dict],
    *,
    anchor: str = "messages",
    text_key: str = "text",
    id_key: str = "id",
    reorder: bool = False,
    nest_text: bool = False,
    conv_id: str = None,
    title: str = "Schema drift test",
) -> bytes:
    """
    Build a V8-serialized conversation, applying the requested mutation.

    Knobs (each models a plausible real schema change):
      anchor     : name of the array field ("messages" is what the carver expects)
      text_key   : field name holding message text (carver expects "text")
      id_key     : field name holding message id (carver expects "id")
      reorder    : emit text before id inside each message object
      nest_text  : wrap the text field one level deeper: {id, content:{text}}
    """
    if conv_id is None:
        conv_id = str(uuid.uuid4())

    parts: List[bytes] = []
    parts.append(_v8_onebyte_string("id"))
    parts.append(_v8_onebyte_string(conv_id))
    parts.append(_v8_onebyte_string("title"))
    parts.append(_v8_onebyte_string(title))

    # array anchor: OneByteString(anchor) immediately followed by BeginArray(0x61)
    parts.append(b"\x22" + _encode_varint(len(anchor)) + anchor.encode() + b"\x61")
    parts.append(_encode_varint(len(messages)))

    for idx, msg in enumerate(messages):
        smi_idx = (idx + 1) * 2
        parts.append(b"\x49")
        parts.append(_encode_varint(smi_idx))

        id_pair = _v8_onebyte_string(id_key) + _v8_onebyte_string(
            msg.get("id", f"msg-{uuid.uuid4().hex[:8]}"))

        if nest_text:
            # message = { id, content: { <text_key>: <str> } }
            inner = _v8_onebyte_string(text_key) + _v8_onebyte_string(msg["text"])
            text_pair = _v8_onebyte_string("content") + _v8_obj([inner])
        else:
            text_pair = _v8_onebyte_string(text_key) + _v8_onebyte_string(msg["text"])

        body = [text_pair, id_pair] if reorder else [id_pair, text_pair]
        parts.append(_v8_obj(body))

    return b"".join(parts)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

MESSAGES = [
    {"role": "user",      "text": "How do I configure mutual TLS between two microservices?", "id": "sd-1"},
    {"role": "assistant", "text": "Mutual TLS requires each service to present a client certificate signed by a trusted CA", "id": "sd-2"},
    {"role": "user",      "text": "What is the recommended certificate rotation interval for production?", "id": "sd-3"},
    {"role": "assistant", "text": "A common practice is rotating leaf certificates every ninety days with automated issuance", "id": "sd-4"},
]
EXPECTED = [m["text"] for m in MESSAGES]

MUTATIONS: List[Dict[str, object]] = [
    {"label": "baseline (observed schema)", "kwargs": {}},
    {"label": "reordered keys (text before id)", "kwargs": {"reorder": True}},
    {"label": "renamed id field (id->uuid)", "kwargs": {"id_key": "uuid"}},
    {"label": "renamed text field (text->content)", "kwargs": {"text_key": "content"}},
    {"label": "renamed anchor (messages->mapping)", "kwargs": {"anchor": "mapping"}},
    {"label": "added nesting (text one level deeper)", "kwargs": {"nest_text": True}},
    {"label": "renamed anchor + kept text field", "kwargs": {"anchor": "conversation"}},
    {"label": "combined drift (rename anchor+text)", "kwargs": {"anchor": "mapping", "text_key": "content"}},
]


def run_experiment():
    print("=" * 78)
    print("  SCHEMA-DRIFT ROBUSTNESS  (synthetic mutations, real carver code)")
    print("=" * 78)

    rows = []
    for mut in MUTATIONS:
        raw = build_conv(MESSAGES, **mut["kwargs"])

        # structured-only path
        sp, sc = carve_v8_structured(raw, "chatgpt")
        struct_recall = _recall(_extract_texts(sp, sc), EXPECTED)

        # full engine (structured -> keyword fallback -> generic)
        fp, fc = carve_value(raw, "chatgpt")
        full_recall = _recall(_extract_texts(fp, fc), EXPECTED)

        # which path carried the recovery?
        if struct_recall > 0:
            path = "structured"
        elif full_recall > 0:
            path = "fallback"
        else:
            path = "none"

        rows.append({
            "mutation": mut["label"],
            "structured_recall": round(struct_recall, 3),
            "full_recall": round(full_recall, 3),
            "recovering_path": path,
        })
        print(f"  {mut['label']:38s} | struct R={struct_recall:.2f} "
              f"full R={full_recall:.2f} via {path}")

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "schema_drift_results.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mutation", "structured_recall", "full_recall", "recovering_path"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n[+] {len(rows)} rows written to {out_path}")
    return rows


if __name__ == "__main__":
    run_experiment()
