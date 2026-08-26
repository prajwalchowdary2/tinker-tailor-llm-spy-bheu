"""
Layer 2: IndexedDB Binary Blob Carver

Scans Chromium and Electron .indexeddb.blob directories for unencrypted
uploaded files, documents, source code, and serialized objects.
"""

import os
import glob
import hashlib
from typing import List, Dict, Any


def get_magic_file_type(data: bytes) -> str:
    """Identify file type by magic byte signatures."""
    if data.startswith(b'%PDF'):
        return "PDF Document"
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG Image"
    elif data.startswith(b'\xff\xd8\xff'):
        return "JPEG Image"
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return "GIF Image"
    elif data.startswith(b'PK\x03\x04'):
        return "ZIP / DOCX / XLSX Archive"
    elif data.startswith(b'{\n') or data.startswith(b'{"') or data.startswith(b'[{'):
        return "JSON Payload"
    elif data.startswith(b'---\n') or data.startswith(b'# '):
        return "Markdown Document"
    elif b'import ' in data[:200] or b'def ' in data[:200]:
        return "Python / Source Code"
    elif b'\x22\x08messages\x61' in data or data.startswith(b'\xff\r\xff'):
        return "V8 Serialized Structured Clone"
    else:
        try:
            sample = data[:512].decode('utf-8')
            if all(c.isprintable() or c in '\r\n\t ' for c in sample):
                return "Plaintext / Code Document"
        except Exception:
            pass
        return "Binary Data Blob"


def scan_blob_directories() -> List[Dict[str, Any]]:
    """
    Search for all .indexeddb.blob directories and extract file artifacts.
    """
    home = os.path.expanduser("~")
    blob_artifacts = []

    search_patterns = [
        f"{home}/Library/Application Support/Google/Chrome/*/IndexedDB/*.indexeddb.blob",
        f"{home}/Library/Application Support/Google/Chrome/*/IndexedDB/*.indexeddb.blob/*",
        f"{home}/Library/Application Support/Microsoft Edge/*/IndexedDB/*.indexeddb.blob",
        f"{home}/Library/Application Support/Claude/IndexedDB/*.indexeddb.blob",
        f"{home}/Library/Application Support/com.openai.chat/IndexedDB/*.indexeddb.blob",
        f"{home}/Library/Application Support/com.openai.atlas/IndexedDB/*.indexeddb.blob",
    ]

    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        search_patterns.extend([
            f"{local_app}/Google/Chrome/User Data/*/IndexedDB/*.indexeddb.blob",
            f"{local_app}/Google/Chrome/User Data/*/IndexedDB/*.indexeddb.blob/*",
            f"{local_app}/Microsoft/Edge/User Data/*/IndexedDB/*.indexeddb.blob",
        ])

    matched_dirs = []
    for pattern in search_patterns:
        for p in glob.glob(pattern):
            if os.path.isdir(p):
                matched_dirs.append(p)

    matched_dirs = list(set(matched_dirs))

    for b_dir in matched_dirs:
        origin = os.path.basename(b_dir).replace(".indexeddb.blob", "")
        profile = "Default"
        parts = b_dir.split(os.sep)
        for part in parts:
            if part.startswith("Profile ") or part in ["Default", "System Profile"]:
                profile = part
                break

        for root, _, files in os.walk(b_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    try:
                        sz = os.path.getsize(file_path)
                        if sz == 0:
                            continue
                        mtime = os.path.getmtime(file_path)

                        with open(file_path, "rb") as fp:
                            header = fp.read(4096)
                            fp.seek(0)
                            sha256 = hashlib.sha256(fp.read()).hexdigest()

                        file_type = get_magic_file_type(header)

                        preview = ""
                        if "PDF" in file_type:
                            preview = f"PDF Document ({sz // 1024} KB)"
                        elif "JSON" in file_type or "Plaintext" in file_type or "Markdown" in file_type:
                            try:
                                preview = header[:300].decode("utf-8", errors="ignore").replace("\n", " ").strip()
                            except:
                                pass
                        elif "V8" in file_type:
                            preview = f"V8 Serialized Chat Blob ({sz // 1024} KB)"

                        blob_artifacts.append({
                            "origin": origin,
                            "profile": profile,
                            "file_path": file_path,
                            "file_name": file,
                            "size_bytes": sz,
                            "file_type": file_type,
                            "sha256": sha256,
                            "modified_timestamp": mtime,
                            "preview": preview,
                        })
                    except Exception:
                        pass

    return blob_artifacts
