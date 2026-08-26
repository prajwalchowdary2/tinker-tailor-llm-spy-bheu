"""
Deep Chrome Forensic Scanner — Multi-Layer Artifact Extraction

Provides comprehensive forensic probing across all Chrome/Chromium
storage subsystems beyond IndexedDB, including:
- Saved credentials (Login Data)
- Active session cookies
- Autofill form submissions
- Favicon visit fingerprints
- Download history from AI portals
- Extension API key & JWT leakage
- Conversation URL history with titles
- Top Sites & frecency scoring
- Service Worker registrations
"""

import os
import glob
import re
import sqlite3
from typing import List, Dict, Any


def _get_profile(path: str) -> str:
    """Extract Chrome profile name from a filesystem path."""
    parts = path.split(os.sep)
    for part in parts:
        if part.startswith("Profile ") or part in ["Default", "System Profile", "Guest Profile"]:
            return part
    return "Unknown"


def _chrome_base() -> str:
    """Return Chrome user data base directory for current platform."""
    home = os.path.expanduser("~")
    import sys
    if sys.platform == "darwin":
        return os.path.join(home, "Library/Application Support/Google/Chrome")
    elif sys.platform == "win32":
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google/Chrome/User Data")
    else:
        return os.path.join(home, ".config/google-chrome")


def scan_saved_credentials() -> List[Dict[str, Any]]:
    """Extract saved usernames for AI/dev platforms from Login Data databases."""
    results = []
    base = _chrome_base()
    for db_path in glob.glob(f"{base}/*/Login Data"):
        profile = _get_profile(db_path)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            c = conn.cursor()
            c.execute("SELECT origin_url, username_value, length(password_value), date_created FROM logins")
            for url, user, pw_len, created in c.fetchall():
                if any(k in url.lower() for k in [
                    'openai', 'chatgpt', 'claude', 'anthropic', 'gemini',
                    'deepseek', 'perplexity', 'huggingface', 'github',
                ]):
                    results.append({
                        "profile": profile,
                        "origin_url": url,
                        "username": user,
                        "password_blob_bytes": pw_len,
                        "date_created": created,
                    })
            conn.close()
        except Exception:
            pass
    return results


def scan_session_cookies() -> List[Dict[str, Any]]:
    """Extract active session cookies for AI platforms."""
    results = []
    base = _chrome_base()
    for db_path in glob.glob(f"{base}/*/Cookies") + glob.glob(f"{base}/*/Network/Cookies"):
        profile = _get_profile(db_path)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            c = conn.cursor()
            c.execute("""
                SELECT host_key, name, length(encrypted_value), expires_utc, is_httponly, is_secure
                FROM cookies
                WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%'
                   OR host_key LIKE '%claude%' OR host_key LIKE '%anthropic%'
                   OR host_key LIKE '%gemini%' OR host_key LIKE '%deepseek%'
                   OR host_key LIKE '%perplexity%'
            """)
            for host, name, enc_len, expires, httponly, secure in c.fetchall():
                results.append({
                    "profile": profile,
                    "host": host,
                    "cookie_name": name,
                    "encrypted_value_bytes": enc_len,
                    "expires_utc": expires,
                    "httponly": bool(httponly),
                    "secure": bool(secure),
                })
            conn.close()
        except Exception:
            pass
    return results


def scan_ai_history_with_titles() -> List[Dict[str, Any]]:
    """Extract browsing history for AI platforms with conversation titles."""
    results = []
    base = _chrome_base()
    for db_path in glob.glob(f"{base}/*/History"):
        profile = _get_profile(db_path)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            c = conn.cursor()
            c.execute("""
                SELECT url, title, visit_count, last_visit_time FROM urls
                WHERE url LIKE '%chatgpt.com/c/%' OR url LIKE '%claude.ai/chat/%'
                   OR url LIKE '%gemini.google.com/app/%' OR url LIKE '%chat.deepseek.com%'
                   OR url LIKE '%perplexity.ai/search%'
                ORDER BY last_visit_time DESC
            """)
            for url, title, visits, last_visit in c.fetchall():
                convo_id = ""
                m = re.search(r'/(?:c|chat|app)/([a-f0-9-]+)', url)
                if m:
                    convo_id = m.group(1)
                results.append({
                    "profile": profile,
                    "url": url,
                    "title": title or "",
                    "visit_count": visits,
                    "last_visit_chrome_epoch": last_visit,
                    "conversation_id": convo_id,
                })
            conn.close()
        except Exception:
            pass
    return results


def scan_ai_downloads() -> List[Dict[str, Any]]:
    """Extract download records sourced from AI platforms."""
    results = []
    base = _chrome_base()
    for db_path in glob.glob(f"{base}/*/History"):
        profile = _get_profile(db_path)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            c = conn.cursor()
            c.execute("""
                SELECT tab_url, target_path, total_bytes, mime_type, start_time, end_time
                FROM downloads
                WHERE tab_url LIKE '%chatgpt%' OR tab_url LIKE '%claude%'
                   OR tab_url LIKE '%gemini%' OR tab_url LIKE '%deepseek%'
                   OR tab_url LIKE '%perplexity%'
            """)
            for url, path, sz, mime, start, end in c.fetchall():
                results.append({
                    "profile": profile,
                    "source_url": url,
                    "target_path": path,
                    "total_bytes": sz,
                    "mime_type": mime,
                    "start_time": start,
                    "end_time": end,
                })
            conn.close()
        except Exception:
            pass
    return results


def scan_extension_secrets() -> List[Dict[str, Any]]:
    """Scan Chrome extension Local Storage for leaked API keys, JWTs, and tokens."""
    results = []
    base = _chrome_base()
    for ext_dir in glob.glob(f"{base}/*/Local Extension Settings/*"):
        profile = _get_profile(ext_dir)
        ext_id = os.path.basename(ext_dir)
        for f in glob.glob(f"{ext_dir}/*.ldb") + glob.glob(f"{ext_dir}/*.log"):
            try:
                with open(f, 'rb') as fh:
                    data = fh.read()
                # API Keys
                for pattern, label in [
                    (rb'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
                    (rb'AKIA[0-9A-Z]{16}', "AWS Access Key"),
                    (rb'ghp_[a-zA-Z0-9]{36}', "GitHub PAT"),
                    (rb'glpat-[a-zA-Z0-9-]{20,}', "GitLab PAT"),
                    (rb'xox[baprs]-[0-9a-zA-Z-]{10,}', "Slack Token"),
                ]:
                    for match in re.findall(pattern, data):
                        key = match.decode('ascii', errors='ignore')
                        results.append({
                            "profile": profile,
                            "extension_id": ext_id,
                            "secret_type": label,
                            "secret_preview": f"{key[:12]}...{key[-4:]}",
                            "secret_length": len(key),
                            "source_file": os.path.basename(f),
                        })
                # JWTs
                for jwt in re.findall(rb'eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}', data):
                    tok = jwt.decode('ascii', errors='ignore')
                    results.append({
                        "profile": profile,
                        "extension_id": ext_id,
                        "secret_type": "JWT Token",
                        "secret_preview": f"{tok[:30]}...{tok[-8:]}",
                        "secret_length": len(tok),
                        "source_file": os.path.basename(f),
                    })
            except Exception:
                pass
    return results


def scan_desktop_app_keys() -> List[Dict[str, Any]]:
    """Extract private keys, bearer tokens, and user IDs from Electron desktop apps."""
    results = []
    home = os.path.expanduser("~")
    app_dirs = [
        ("ChatGPT Desktop (com.openai.atlas)", f"{home}/Library/Application Support/com.openai.atlas"),
        ("ChatGPT Desktop (com.openai.chat)", f"{home}/Library/Application Support/com.openai.chat"),
        ("Claude Desktop", f"{home}/Library/Application Support/Claude"),
    ]
    for app_name, app_dir in app_dirs:
        if not os.path.exists(app_dir):
            continue
        for root, _, files in os.walk(app_dir):
            for fname in files:
                fp = os.path.join(root, fname)
                if fname.endswith(('.ldb', '.log', '.sst')) and os.path.getsize(fp) > 100:
                    try:
                        with open(fp, 'rb') as fh:
                            data = fh.read()
                        # Private keys
                        for pk in re.findall(rb'-----BEGIN (?:EC |RSA |)PRIVATE KEY-----[^-]+-----END (?:EC |RSA |)PRIVATE KEY-----', data, re.DOTALL):
                            results.append({
                                "app": app_name,
                                "secret_type": "Private Cryptographic Key (PEM)",
                                "key_size_bytes": len(pk),
                                "source_file": fp.replace(app_dir, ""),
                            })
                        # User IDs
                        for uid in set(re.findall(rb'user-[a-zA-Z0-9]{20,}', data)):
                            results.append({
                                "app": app_name,
                                "secret_type": "User ID",
                                "value": uid.decode('ascii', errors='ignore'),
                                "source_file": fp.replace(app_dir, ""),
                            })
                        # Conversation titles
                        titles = re.findall(rb'"title"\s*:\s*"([^"]{5,80})"', data)
                        if titles:
                            results.append({
                                "app": app_name,
                                "secret_type": "Conversation Titles",
                                "count": len(titles),
                                "sample": [t.decode('utf-8', errors='ignore') for t in titles[:5]],
                                "source_file": fp.replace(app_dir, ""),
                            })
                    except Exception:
                        pass
    return results
