"""
DLP Scanner — Credential and PII Detection in Carved Prompts

Scans recovered LLM conversations for leaked credentials, API keys,
passwords, and personally identifiable information. This demonstrates
the data exfiltration risk: users paste secrets into LLM prompts,
which then persist in unencrypted IndexedDB storage.
"""

import re
from typing import Dict, List, Tuple


CREDENTIAL_PATTERNS: List[Tuple[str, str]] = [
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', "API Key"),
    (r'(?:password|passwd|pwd)\s*[:=]\s*["\']?(\S{6,})', "Password"),
    (r'(?:secret|token)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', "Secret/Token"),
    (r'(sk-[A-Za-z0-9]{20,})', "OpenAI API Key"),
    (r'(ghp_[A-Za-z0-9]{36,})', "GitHub PAT"),
    (r'(AKIA[0-9A-Z]{16})', "AWS Access Key"),
    (r'(xox[bsp]-[A-Za-z0-9\-]+)', "Slack Token"),
    (r'Bearer\s+([A-Za-z0-9_\-.~+/]+=*)', "Bearer Token"),
]

PII_PATTERNS: List[Tuple[str, str]] = [
    (r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', "SSN"),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "Email"),
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "Credit Card"),
    (r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', "Phone Number"),
]


def scan_text(text: str) -> List[Dict]:
    """
    Scan a text string for credentials and PII.

    Returns a list of findings, each with type, pattern_name, match, and
    character position.
    """
    findings = []

    for pattern, name in CREDENTIAL_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "type": "credential",
                "pattern_name": name,
                "match": m.group(0)[:50],
                "position": m.start(),
            })

    for pattern, name in PII_PATTERNS:
        for m in re.finditer(pattern, text):
            findings.append({
                "type": "pii",
                "pattern_name": name,
                "match": m.group(0)[:50],
                "position": m.start(),
            })

    return findings


def scan_conversation(messages: List[Dict]) -> List[Dict]:
    """
    Scan all messages in a conversation for sensitive data.

    Each message dict should have a "text" or "parts" field.
    Returns findings with message index attached.
    """
    all_findings = []
    for idx, msg in enumerate(messages):
        text = msg.get("text", "")
        if not text and "parts" in msg:
            text = " ".join(msg["parts"])
        if not text:
            continue

        msg_findings = scan_text(text)
        for f in msg_findings:
            f["message_index"] = idx
            f["role"] = msg.get("role", "unknown")
        all_findings.extend(msg_findings)

    return all_findings


def scan_evidence(evidence: Dict) -> Dict:
    """
    Scan a full evidence payload and produce a DLP summary.

    Returns a dict with total findings count, breakdown by type,
    and the individual findings list.
    """
    findings = []

    prompts = evidence.get("prompts", [])
    for idx, prompt in enumerate(prompts):
        text = " ".join(prompt.get("parts", []))
        if text:
            for f in scan_text(text):
                f["source"] = "prompt"
                f["source_index"] = idx
                f["bot"] = prompt.get("bot", "unknown")
                findings.append(f)

    conversations = evidence.get("conversations", [])
    for conv in conversations:
        messages = conv.get("messages", [])
        for f in scan_conversation(messages):
            f["source"] = "conversation"
            f["conversation_id"] = conv.get("id", "")
            f["bot"] = conv.get("bot", "unknown")
            findings.append(f)

    cred_count = sum(1 for f in findings if f["type"] == "credential")
    pii_count = sum(1 for f in findings if f["type"] == "pii")

    return {
        "total_findings": len(findings),
        "credentials": cred_count,
        "pii": pii_count,
        "findings": findings,
    }
