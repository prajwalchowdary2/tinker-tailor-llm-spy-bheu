"""
Cross-Platform Browser Profile Discovery

Auto-detects Chromium-based browser profiles (Chrome, Edge) and native
desktop apps (ChatGPT, Claude) on macOS and Windows. Returns paths to
History databases, cookie stores, and IndexedDB LevelDB directories
for all installed profiles.

Supports: Chrome, Edge, Safari, Firefox, ChatGPT Desktop, Claude Desktop
"""

import os
import sys
from typing import Dict, Optional


BOT_HOSTS_MAC = [
    ("chatgpt", "https_chatgpt.com_0"),
    ("claude", "https_claude.ai_0"),
    ("gemini", "https_gemini.google.com_0"),
]

BOT_HOSTS_WIN = [
    ("chatgpt", "https_chatgpt.com_0"),
    ("claude", "https_claude.ai_0"),
    ("gemini", "https_gemini.google.com_0"),
    ("gemini", "https_bard.google.com_0"),
    ("deepseek", "https_chat.deepseek.com_0"),
    ("deepseek", "https_platform.deepseek.com_0"),
    ("perplexity", "https_perplexity.ai_0"),
    ("cline", "https_cline.bot_0"),
]


def get_firefox_profile_dir(base_path: str) -> Optional[str]:
    """Find the active Firefox profile directory containing places.sqlite."""
    if not os.path.exists(base_path):
        return None
    try:
        for item in os.listdir(base_path):
            profile_path = os.path.join(base_path, item)
            if os.path.isdir(profile_path) and os.path.exists(os.path.join(profile_path, "places.sqlite")):
                return profile_path
    except Exception:
        pass
    return None


def _scan_chromium_profiles(user_data_dir: str, browser_tag: str, bot_hosts: list, paths: Dict):
    """Scan a Chromium user data directory for all profiles with IndexedDB."""
    if not os.path.exists(user_data_dir):
        return
    for item in os.listdir(user_data_dir):
        profile_path = os.path.join(user_data_dir, item)
        if os.path.isdir(profile_path) and (item == "Default" or item.startswith("Profile ")):
            idb_dir = os.path.join(profile_path, "IndexedDB")
            if os.path.exists(idb_dir):
                for bot, host in bot_hosts:
                    db_p = os.path.join(idb_dir, f"{host}.indexeddb.leveldb")
                    if os.path.exists(db_p):
                        paths["indexeddb"][f"{bot}_browser_{browser_tag}_{item}"] = db_p


def get_forensic_paths() -> Dict:
    """
    Detect browser and desktop app data paths on macOS and Windows.

    Returns a dict with keys: chrome_history, chrome_cookies,
    edge_history, edge_cookies, firefox_history, firefox_cookies,
    safari_history, and indexeddb (dict mapping bot labels to
    LevelDB directory paths).
    """
    home = os.path.expanduser("~")
    paths = {
        "chrome_history": "",
        "chrome_cookies": "",
        "edge_history": "",
        "edge_cookies": "",
        "firefox_history": "",
        "firefox_cookies": "",
        "safari_history": "",
        "indexeddb": {},
    }

    if sys.platform == "darwin":
        chrome_base = os.path.join(home, "Library/Application Support/Google/Chrome/Default")
        paths["chrome_history"] = os.path.join(chrome_base, "History")
        cookie_path = os.path.join(chrome_base, "Network", "Cookies")
        if not os.path.exists(cookie_path):
            cookie_path = os.path.join(chrome_base, "Cookies")
        paths["chrome_cookies"] = cookie_path

        edge_base = os.path.join(home, "Library/Application Support/Microsoft Edge/Default")
        paths["edge_history"] = os.path.join(edge_base, "History")
        edge_cookie = os.path.join(edge_base, "Network", "Cookies")
        if not os.path.exists(edge_cookie):
            edge_cookie = os.path.join(edge_base, "Cookies")
        paths["edge_cookies"] = edge_cookie

        paths["safari_history"] = os.path.join(home, "Library/Safari/History.db")

        ff_base = os.path.join(home, "Library/Application Support/Firefox/Profiles")
        ff_profile = get_firefox_profile_dir(ff_base)
        if ff_profile:
            paths["firefox_history"] = os.path.join(ff_profile, "places.sqlite")
            paths["firefox_cookies"] = os.path.join(ff_profile, "cookies.sqlite")

        _scan_chromium_profiles(
            os.path.join(home, "Library/Application Support/Google/Chrome"),
            "chrome", BOT_HOSTS_MAC, paths,
        )
        _scan_chromium_profiles(
            os.path.join(home, "Library/Application Support/Microsoft Edge"),
            "edge", BOT_HOSTS_MAC, paths,
        )

        paths["indexeddb"]["chatgpt_desktop"] = os.path.join(
            home, "Library/Application Support/com.openai.chat/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb"
        )
        paths["indexeddb"]["claude_desktop"] = os.path.join(
            home, "Library/Application Support/Claude/IndexedDB/https_claude.ai_0.indexeddb.leveldb"
        )

    elif sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")

        chrome_base = os.path.join(local_app, "Google/Chrome/User Data/Default")
        paths["chrome_history"] = os.path.join(chrome_base, "History")
        cookie_path = os.path.join(chrome_base, "Network", "Cookies")
        if not os.path.exists(cookie_path):
            cookie_path = os.path.join(chrome_base, "Cookies")
        paths["chrome_cookies"] = cookie_path

        edge_base = os.path.join(local_app, "Microsoft/Edge/User Data/Default")
        paths["edge_history"] = os.path.join(edge_base, "History")
        edge_cookie = os.path.join(edge_base, "Network", "Cookies")
        if not os.path.exists(edge_cookie):
            edge_cookie = os.path.join(edge_base, "Cookies")
        paths["edge_cookies"] = edge_cookie

        ff_base = os.path.join(app_data, "Mozilla/Firefox/Profiles")
        ff_profile = get_firefox_profile_dir(ff_base)
        if ff_profile:
            paths["firefox_history"] = os.path.join(ff_profile, "places.sqlite")
            paths["firefox_cookies"] = os.path.join(ff_profile, "cookies.sqlite")

        _scan_chromium_profiles(
            os.path.join(local_app, "Google/Chrome/User Data"),
            "chrome", BOT_HOSTS_WIN, paths,
        )
        _scan_chromium_profiles(
            os.path.join(local_app, "Microsoft/Edge/User Data"),
            "edge", BOT_HOSTS_WIN, paths,
        )

        paths["indexeddb"]["chatgpt_desktop"] = os.path.join(
            app_data, "com.openai.chat/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb"
        )
        paths["indexeddb"]["claude_desktop"] = os.path.join(
            app_data, "Claude/IndexedDB/https_claude.ai_0.indexeddb.leveldb"
        )

    elif sys.platform.startswith("linux"):
        config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))

        chrome_base = os.path.join(config_dir, "google-chrome/Default")
        paths["chrome_history"] = os.path.join(chrome_base, "History")
        cookie_path = os.path.join(chrome_base, "Network", "Cookies")
        if not os.path.exists(cookie_path):
            cookie_path = os.path.join(chrome_base, "Cookies")
        paths["chrome_cookies"] = cookie_path

        edge_base = os.path.join(config_dir, "microsoft-edge/Default")
        paths["edge_history"] = os.path.join(edge_base, "History")
        edge_cookie = os.path.join(edge_base, "Network", "Cookies")
        if not os.path.exists(edge_cookie):
            edge_cookie = os.path.join(edge_base, "Cookies")
        paths["edge_cookies"] = edge_cookie

        ff_base = os.path.join(home, ".mozilla/firefox")
        ff_profile = get_firefox_profile_dir(ff_base)
        if ff_profile:
            paths["firefox_history"] = os.path.join(ff_profile, "places.sqlite")
            paths["firefox_cookies"] = os.path.join(ff_profile, "cookies.sqlite")

        # Chrome, Chromium, Edge, Brave — all Chromium-based
        _scan_chromium_profiles(
            os.path.join(config_dir, "google-chrome"),
            "chrome", BOT_HOSTS_WIN, paths,
        )
        _scan_chromium_profiles(
            os.path.join(config_dir, "chromium"),
            "chromium", BOT_HOSTS_WIN, paths,
        )
        _scan_chromium_profiles(
            os.path.join(config_dir, "microsoft-edge"),
            "edge", BOT_HOSTS_WIN, paths,
        )
        _scan_chromium_profiles(
            os.path.join(config_dir, "BraveSoftware/Brave-Browser"),
            "brave", BOT_HOSTS_WIN, paths,
        )

        # Snap-installed Chrome/Chromium
        snap_chrome = os.path.join(home, "snap/chromium/common/chromium")
        _scan_chromium_profiles(snap_chrome, "chromium_snap", BOT_HOSTS_WIN, paths)

    return paths
