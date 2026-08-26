"""
Forensic utilities: chain of custody, browser history, blob storage,
session restore, omnibox shortcuts, Cursor AI IDE, cache storage,
and deep Chrome artifact extraction.
"""

from tinker_tailor.forensics.chain_of_custody import sign_evidence, verify_evidence
from tinker_tailor.forensics.history import extract_browser_history
from tinker_tailor.forensics.blobs import scan_blob_directories
from tinker_tailor.forensics.sessions import scan_session_restore_files
from tinker_tailor.forensics.shortcuts import scan_omnibox_shortcuts
from tinker_tailor.forensics.cursor import scan_cursor_ide_storage
from tinker_tailor.forensics.cache import scan_cache_storage
from tinker_tailor.forensics.deep_chrome import (
    scan_saved_credentials,
    scan_session_cookies,
    scan_ai_history_with_titles,
    scan_ai_downloads,
    scan_extension_secrets,
    scan_desktop_app_keys,
)

__all__ = [
    "sign_evidence",
    "verify_evidence",
    "extract_browser_history",
    "scan_blob_directories",
    "scan_session_restore_files",
    "scan_omnibox_shortcuts",
    "scan_cursor_ide_storage",
    "scan_cache_storage",
    "scan_saved_credentials",
    "scan_session_cookies",
    "scan_ai_history_with_titles",
    "scan_ai_downloads",
    "scan_extension_secrets",
    "scan_desktop_app_keys",
]
