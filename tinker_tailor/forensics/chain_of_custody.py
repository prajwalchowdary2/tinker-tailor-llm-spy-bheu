"""
Chain of Custody — HMAC-SHA256 Evidence Signing

Provides tamper-evident envelopes for carved evidence. Each piece of
extracted data is signed with a session key, enabling forensic
examiners to verify that evidence was not modified after extraction.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict


def generate_session_key() -> bytes:
    """Generate a cryptographically random 32-byte HMAC key for this session."""
    return secrets.token_bytes(32)


def get_file_sha256(path: str) -> str:
    """Calculate SHA-256 hash of a file for chain of custody verification."""
    if not os.path.exists(path):
        return "N/A"
    sha = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return "ERROR_HASH_FAILED"


def sign_payload(payload: Any, key: bytes) -> str:
    """Compute HMAC-SHA256 signature over canonically sorted JSON."""
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hmac.new(key, serialized.encode('utf-8'), hashlib.sha256).hexdigest()


def sign_evidence(payload: Any, key: bytes, key_version: int = 1) -> Dict:
    """
    Create a tamper-evident evidence envelope.

    Returns a dict with the original payload, its HMAC-SHA256 signature,
    the key version, and the signing timestamp.
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    mac = hmac.new(key, serialized, hashlib.sha256).hexdigest()
    return {
        "payload": payload,
        "hmac_sha256": mac,
        "key_version": key_version,
        "timestamp": time.time(),
    }


def verify_evidence(envelope: Dict, key: bytes) -> bool:
    """Verify that an evidence envelope has not been tampered with."""
    payload = envelope.get("payload")
    expected_mac = envelope.get("hmac_sha256", "")
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    actual_mac = hmac.new(key, serialized, hashlib.sha256).hexdigest()
    return hmac.compare_digest(actual_mac, expected_mac)
