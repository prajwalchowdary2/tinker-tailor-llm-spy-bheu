"""
Browser History and Cookie Extraction

Extracts browsing history, downloads, and cookies from Chrome, Edge,
Safari, and Firefox by copying locked SQLite databases and querying
them safely. Uses direct file copy with WAL support, falling back to
the SQLite Online Backup API when files are locked.
"""

import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional


_db_copy_failures: set = set()


def safe_copy_db(src_path: str, dest_name: str, temp_dir: str, warnings_list: Optional[List] = None) -> Optional[str]:
    """
    Copy a locked SQLite database for safe read access.

    Tries direct file copy (including WAL/SHM) first for speed,
    falls back to the SQLite Online Backup API for locked files.
    """
    if not src_path or not os.path.exists(src_path):
        return None

    os.makedirs(temp_dir, exist_ok=True)
    dest_path = os.path.join(temp_dir, dest_name)

    try:
        shutil.copy2(src_path, dest_path)
        for suffix in ("-wal", "-shm"):
            aux = src_path + suffix
            if os.path.exists(aux):
                shutil.copy2(aux, dest_path + suffix)
        _db_copy_failures.discard(src_path)
        return dest_path
    except (PermissionError, OSError):
        pass

    try:
        src_conn = sqlite3.connect(src_path)
        dest_conn = sqlite3.connect(dest_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()
        _db_copy_failures.discard(src_path)
        return dest_path
    except PermissionError:
        _db_copy_failures.add(src_path)
        if warnings_list is not None and "tcc_permission_denied" not in warnings_list:
            warnings_list.append("tcc_permission_denied")
        return None
    except Exception:
        _db_copy_failures.add(src_path)
        return None


def parse_chrome_history(db_path: str) -> List[Dict]:
    """Extract visits to AI platforms from a Chrome/Edge history database copy."""
    results = []
    if not db_path or not os.path.exists(db_path):
        return results
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.url, u.title, v.visit_time, u.visit_count
            FROM urls u JOIN visits v ON u.id = v.url
            WHERE u.url LIKE '%chat.openai.com%'
               OR u.url LIKE '%chatgpt.com%'
               OR u.url LIKE '%claude.ai%'
               OR u.url LIKE '%gemini.google.com%'
               OR u.url LIKE '%bard.google.com%'
               OR u.url LIKE '%chat.deepseek.com%'
               OR u.url LIKE '%perplexity.ai%'
            ORDER BY v.visit_time DESC
        """)
        for row in cursor.fetchall():
            url, title, visit_time, count = row
            ts = datetime(1601, 1, 1, tzinfo=timezone.utc)
            ts = ts.replace(microsecond=0)
            try:
                from datetime import timedelta
                ts = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=visit_time)
            except Exception:
                pass
            results.append({
                "url": url,
                "title": title or "",
                "visit_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "visit_count": count,
            })
        conn.close()
    except Exception:
        pass
    return results


def parse_safari_history(db_path: str) -> List[Dict]:
    """Extract visits to AI platforms from Safari's History.db."""
    results = []
    if not db_path or not os.path.exists(db_path):
        return results
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hi.url, hv.title, hv.visit_time
            FROM history_items hi JOIN history_visits hv ON hi.id = hv.history_item
            WHERE hi.url LIKE '%chat.openai.com%'
               OR hi.url LIKE '%chatgpt.com%'
               OR hi.url LIKE '%claude.ai%'
               OR hi.url LIKE '%gemini.google.com%'
               OR hi.url LIKE '%chat.deepseek.com%'
               OR hi.url LIKE '%perplexity.ai%'
            ORDER BY hv.visit_time DESC
        """)
        for row in cursor.fetchall():
            url, title, visit_time = row
            try:
                from datetime import timedelta
                ts = datetime(2001, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=visit_time)
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_str = str(visit_time)
            results.append({
                "url": url,
                "title": title or "",
                "visit_time": ts_str,
            })
        conn.close()
    except Exception:
        pass
    return results


def parse_firefox_history(db_path: str) -> List[Dict]:
    """Extract visits to AI platforms from Firefox's places.sqlite."""
    results = []
    if not db_path or not os.path.exists(db_path):
        return results
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.url, p.title, h.visit_date
            FROM moz_places p JOIN moz_historyvisits h ON p.id = h.place_id
            WHERE p.url LIKE '%chat.openai.com%'
               OR p.url LIKE '%chatgpt.com%'
               OR p.url LIKE '%claude.ai%'
               OR p.url LIKE '%gemini.google.com%'
               OR p.url LIKE '%chat.deepseek.com%'
               OR p.url LIKE '%perplexity.ai%'
            ORDER BY h.visit_date DESC
        """)
        for row in cursor.fetchall():
            url, title, visit_date = row
            try:
                ts = datetime.fromtimestamp(visit_date / 1_000_000, tz=timezone.utc)
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_str = str(visit_date)
            results.append({
                "url": url,
                "title": title or "",
                "visit_time": ts_str,
            })
        conn.close()
    except Exception:
        pass
    return results


def extract_browser_history(paths: Dict) -> Dict[str, List[Dict]]:
    """
    Extract AI visits across all detected browser history databases.
    """
    history_data = {}
    if paths.get("chrome_history") and os.path.exists(paths["chrome_history"]):
        history_data["chrome"] = parse_chrome_history(paths["chrome_history"])
    if paths.get("edge_history") and os.path.exists(paths["edge_history"]):
        history_data["edge"] = parse_chrome_history(paths["edge_history"])
    if paths.get("safari_history") and os.path.exists(paths["safari_history"]):
        history_data["safari"] = parse_safari_history(paths["safari_history"])
    if paths.get("firefox_history") and os.path.exists(paths["firefox_history"]):
        history_data["firefox"] = parse_firefox_history(paths["firefox_history"])
    return history_data

