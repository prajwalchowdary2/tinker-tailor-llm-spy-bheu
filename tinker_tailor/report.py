"""
Forensic HTML report generator for Tinker Tailor LLM Spy.
"""

import html
import socket
from datetime import datetime

def _get_layer_data(evidence: dict) -> list:
    """
    Returns the 13-layer severity matrix based on evidence counts.
    """
    stats = evidence.get("stats", {})
    deep_chrome = evidence.get("deep_chrome", {})
    
    return [
        {
            "layer": 1,
            "name": "LevelDB LSM-Tree Remanence",
            "severity": "CRITICAL",
            "count": len(evidence.get("prompts", [])) + len(evidence.get("conversations", [])),
            "desc": "Deleted or fragmented conversational AI prompts and responses recovered from LevelDB."
        },
        {
            "layer": 2,
            "name": "Unencrypted Document Blobs",
            "severity": "CRITICAL",
            "count": len(evidence.get("document_blobs", [])),
            "desc": "Local files and documents uploaded to AI assistants stored completely unencrypted."
        },
        {
            "layer": 3,
            "name": "TipTap Pre-Send Keystroke Drafts",
            "severity": "HIGH",
            "count": stats.get("draft_count", 0), # Simplified for this example, could be a subset of prompts
            "desc": "Unsent messages and keystrokes captured by the TipTap editor state."
        },
        {
            "layer": 4,
            "name": "Cursor AI IDE Composer Sessions",
            "severity": "CRITICAL",
            "count": len(evidence.get("cursor_ide_telemetry", [])),
            "desc": "Proprietary source code, context, and prompts leaked from the IDE composer."
        },
        {
            "layer": 5,
            "name": "Service Worker CacheStorage",
            "severity": "HIGH",
            "count": len(evidence.get("service_worker_cache", [])),
            "desc": "Cached application state, offline resources, and API responses."
        },
        {
            "layer": 6,
            "name": "SNSS Session Restore Tabs",
            "severity": "MEDIUM",
            "count": len(evidence.get("session_restore_tabs", [])),
            "desc": "Historical tabs and navigation state saved for browser crash recovery."
        },
        {
            "layer": 7,
            "name": "Omnibox Typed Queries",
            "severity": "MEDIUM",
            "count": len(evidence.get("omnibox_shortcuts", [])),
            "desc": "Search queries and URLs typed directly into the URL bar."
        },
        {
            "layer": 8,
            "name": "Active Session Cookies",
            "severity": "CRITICAL",
            "count": len(deep_chrome.get("session_cookies", [])),
            "desc": "Authentication tokens allowing complete account takeover without MFA."
        },
        {
            "layer": 9,
            "name": "Conversation URLs with Titles",
            "severity": "HIGH",
            "count": len(deep_chrome.get("ai_history", [])),
            "desc": "Titles and metadata of previous AI interactions leaking intent."
        },
        {
            "layer": 10,
            "name": "AI Download Records",
            "severity": "MEDIUM",
            "count": len(deep_chrome.get("ai_downloads", [])),
            "desc": "Records of files and generated assets downloaded from the AI service."
        },
        {
            "layer": 11,
            "name": "Extension API Key & JWT Leakage",
            "severity": "CRITICAL",
            "count": len(deep_chrome.get("extension_secrets", [])),
            "desc": "Hardcoded or cached secrets, API keys, and JWTs from browser extensions."
        },
        {
            "layer": 12,
            "name": "Desktop App Private Keys (ECDSA/PEM)",
            "severity": "CRITICAL",
            "count": len(deep_chrome.get("desktop_app_keys", [])),
            "desc": "Private cryptographic keys extracted from local application storage."
        },
        {
            "layer": 13,
            "name": "Cross-Profile Isolation Failure",
            "severity": "CRITICAL",
            "count": len(deep_chrome.get("cross_profile_isolation", {}).keys()),
            "desc": "Evidence of data bleeding across logical browser profiles."
        }
    ]

def generate_forensic_report(evidence: dict, output_path: str = "forensic_report.html") -> str:
    """
    Generates a forensic HTML report from the provided evidence.
    
    Args:
        evidence: The dictionary containing extracted data.
        output_path: The path where the HTML report should be written.
        
    Returns:
        The output path of the written report.
    """
    version = evidence.get("version", "Unknown")
    timestamp_val = evidence.get("timestamp", 0.0)
    time_str = datetime.fromtimestamp(timestamp_val).strftime("%Y-%m-%d %H:%M:%S") if timestamp_val else "Unknown"
    hostname = html.escape(socket.gethostname())
    
    layers = _get_layer_data(evidence)
    total_artifacts = sum(layer["count"] for layer in layers)
    
    # Generate Table Rows
    table_rows = ""
    for layer in layers:
        color = "#ffc107" # Default MEDIUM
        if layer["severity"] == "CRITICAL":
            color = "#e94560"
        elif layer["severity"] == "HIGH":
            color = "#ff6b35"
            
        table_rows += f'''
        <tr>
            <td>{layer["layer"]}</td>
            <td>{html.escape(layer["name"])}</td>
            <td style="color: {color}; font-weight: bold;">{html.escape(layer["severity"])}</td>
            <td>{layer["count"]}</td>
            <td class="desc">{html.escape(layer["desc"])}</td>
        </tr>
        '''
        
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tinker Tailor LLM Spy — Forensic Triage Report</title>
    <style>
        body {{
            background-color: #1a1a2e;
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #0f3460;
            text-shadow: 1px 1px 2px rgba(233, 69, 96, 0.5);
            border-bottom: 2px solid #e94560;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #e94560;
            margin-top: 30px;
        }}
        .header-info {{
            background-color: rgba(15, 52, 96, 0.3);
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #0f3460;
        }}
        .summary-box {{
            background-color: rgba(233, 69, 96, 0.1);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e94560;
            text-align: center;
            margin-bottom: 30px;
        }}
        .summary-box h3 {{
            margin: 0 0 10px 0;
            color: #e94560;
        }}
        .total-count {{
            font-size: 2.5em;
            font-weight: bold;
            color: #ffffff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            background-color: rgba(0, 0, 0, 0.2);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #0f3460;
        }}
        th {{
            background-color: #0f3460;
            color: #ffffff;
            font-weight: bold;
            text-transform: uppercase;
        }}
        tr:hover {{
            background-color: rgba(15, 52, 96, 0.4);
        }}
        td.desc {{
            font-size: 0.9em;
            color: #b0b0b0;
        }}
        .keychain-gap {{
            background-color: rgba(255, 107, 53, 0.1);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ff6b35;
            margin-bottom: 30px;
        }}
        /* Pure CSS Pie Chart */
        .pie-chart-container {{
            display: flex;
            align-items: center;
            gap: 30px;
            margin-top: 20px;
        }}
        .pie-chart {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            /* Conic gradient for 5% protected, 95% unprotected */
            background: conic-gradient(#e94560 0% 95%, #4caf50 95% 100%);
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
        }}
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .color-box {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
            font-size: 0.8em;
            color: #808080;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Tinker Tailor LLM Spy — Forensic Triage Report</h1>
        
        <div class="header-info">
            <p><strong>Timestamp:</strong> {html.escape(time_str)}</p>
            <p><strong>Tool Version:</strong> {html.escape(version)}</p>
            <p><strong>Hostname:</strong> {hostname}</p>
        </div>

        <div class="summary-box">
            <h3>Executive Summary</h3>
            <p>Total Forensic Artifacts Recovered</p>
            <div class="total-count">{total_artifacts}</div>
        </div>

        <h2>Severity Matrix</h2>
        <table>
            <thead>
                <tr>
                    <th>Layer</th>
                    <th>Name</th>
                    <th>Severity</th>
                    <th>Count</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>

        <div class="keychain-gap">
            <h2>Keychain Encryption Gap</h2>
            <p>macOS Keychain only protects specific 2 SQLite columns: cookie values and saved passwords. However, 95%+ of sensitive data (conversations, private keys, API keys, documents, browsing history, cache) is stored completely unprotected on the disk, relying solely on OS-level user file permissions, which are inherently bypassed once logical execution occurs within the user's context.</p>
            
            <div class="pie-chart-container">
                <div class="pie-chart"></div>
                <div class="legend">
                    <div class="legend-item">
                        <div class="color-box" style="background-color: #e94560;"></div>
                        <span>Unprotected Data (>95%)</span>
                    </div>
                    <div class="legend-item">
                        <div class="color-box" style="background-color: #4caf50;"></div>
                        <span>Protected Data (<5%)</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated by Tinker Tailor LLM Spy v4.0.0-bheu | PES University ISFCR Lab
        </div>
    </div>
</body>
</html>
'''
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return output_path
