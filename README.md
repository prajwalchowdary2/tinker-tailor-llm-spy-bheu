# Tinker Tailor LLM Spy: Reconstructing "Deleted" Chats & Hijacking Sessions from Chromium LevelDB Caches

[![Target Venue](https://img.shields.io/badge/Venue-Black%20Hat%20Europe%20Briefings-red.svg)](https://www.blackhat.com/eu-24/)
[![Institution](https://img.shields.io/badge/Research-PES%20University%20ISFCR-blue.svg)](https://pes.edu)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://python.org)

> **Official Research Repository for Black Hat Europe Briefings & Digital Forensics Artifacts**

---

## 📌 Executive Summary

**Tinker Tailor LLM Spy** is a specialized, zero-dependency client-side forensic carving and threat-hunting framework designed to extract, reconstruct, and inspect Large Language Model (LLM) telemetry from volatile local storage cache files.

When users click **"Delete Chat"** inside web interfaces like ChatGPT, Claude, Gemini, or Perplexity, cloud servers mark records for deletion. However, local Chromium-based browsers (Chrome, Edge, Brave) and Electron desktop apps store client telemetry inside **IndexedDB** databases backed by Google's **LevelDB** Log-Structured Merge (LSM) storage engine. Because LevelDB relies on append-only Write-Ahead Logs (`.log`) and delayed background SSTable compactions (`.ldb`), "deleted" prompts, assistant responses, and intermediate keystroke drafts persist on disk for days, weeks, or indefinitely.

---

## 👥 Authors & Affiliation

1. **Dr. Sapna V M** (Associate Professor, Dept of CSE, PES University, Bangalore) — `sapnavm@pes.edu`
2. **Prajwal Chowdary** (Student & Researcher, Dept of CSE, PES University, Bangalore) — `prajwalchowdary5@gmail.com`
3. **Prasad H B** (Professor & Director of ISFCR, Dept of CSE, PES University, Bangalore) — `prasadhb@pes.edu`

**Institution:** Information Security Forensics & Cyber Resilience (ISFCR) Lab, Department of Computer Science & Engineering, PES University, Bangalore, India  
**Target Venue:** Black Hat Europe Briefings  
**Category:** Enterprise Security / Malware Analysis & Incident Response / Applied Vulnerability Research

---

## 🔥 Key Vulnerabilities Uncovered

1. **LSM-Tree Data Remanence in LevelDB:**
   * User prompts and full conversation trees persist in uncompacted LevelDB WAL (`.log`) and SSTable (`.ldb`) records long after being deleted via the web UI.
   * On our empirical scan across 23 browser profiles, **506 text artifacts** were recovered, **70.8% (358 artifacts) of which were already deleted from the UI**.
2. **Claude TipTap Keystroke Draft Persistence:**
   * Anthropic's Claude web app caches in-flight user keystrokes in `tipTapEditorState` IndexedDB records *before* the user clicks 'Send'. Unsubmitted drafts and abandoned thoughts remain readable on disk.
3. **Plaintext Document & File Blobs (`.indexeddb.blob/`):**
   * Uploaded proprietary files (PDFs, source code, data spreadsheets) are stored as raw, unencrypted binary blobs directly on disk under user privileges, surviving conversation deletion.
4. **Cryptographic Key Exposure in Desktop Apps (`com.openai.atlas`):**
   * The ChatGPT Desktop application persists raw WebRTC ECDSA private keys (`BEGIN PRIVATE KEY`) side-by-side with user chat transcripts in unencrypted LevelDB logs.

---

## 📐 Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                            TARGET ENDPOINT ENVIRONMENT                            |
|                                                                                   |
|  +--------------------+   +-----------------------+   +------------------------+  |
|  | Chrome / Edge IDB  |   | Claude TipTap Cache   |   | Electron Desktop Apps  |  |
|  | (.log / .ldb / SST)|   | (IndexedDB Blobs)     |   | (com.openai.atlas)     |  |
|  +---------+----------+   +-----------+-----------+   +-----------+------------+  |
+------------|--------------------------|---------------------------|---------------+
             |                          |                           |
             +--------------------------+---------------------------+
                                        | (Lock-Free Read-Only Carve)
                                        v
                     +--------------------------------------+
                     |       TINKER TAILOR ENGINE           |
                     |  - Multi-Profile Auto Discovery      |
                     |  - Pure Python V8 Deserializer       |
                     |  - Snappy Decompression Engine       |
                     |  - TipTap State JSON Parser          |
                     |  - Real-Time DLP Credential Scanner  |
                     |  - HMAC-SHA256 Chain of Custody Sign |
                     +------------------+-------------------+
                                        |
               +------------------------+------------------------+
               v                                                 v
+--------------------------------------+       +------------------------------------+
| Interactive Live UI (live_monitor.py)|       | Headless CLI (tinker_tailor)       |
|  - Real-time Threat Heatmap          |       |  - Automated Incident Response     |
|  - Interactive Thread Rebuilder      |       |  - JSON/CSV Telemetry Export       |
|  - DLP Security & PII Alerts         |       |  - Sub-150ms Full Endpoint Scans   |
+--------------------------------------+       +------------------------------------+
```

---

## ⚙️ Requirements & Installation

* **Operating System:** macOS (Apple Silicon / Intel), Windows 10/11, or Linux
* **Python:** Python 3.8+
* **Dependencies:** Zero mandatory external compiled dependencies (Core engine runs in 100% pure Python standard library).

```bash
# Clone the repository
git clone https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu.git
cd tinker-tailor-llm-spy-bheu

# Optional: Install requirements for cryptographic signing and figure reproduction
pip install -r requirements.txt
```

---

## 🚀 Usage

### Mode A: Live Interactive Web Dashboard

Launch the local carving daemon and interactive forensic dashboard:

**On macOS / Linux:**
```bash
./start.sh
```

**On Windows:**
```cmd
start.bat
```

Or run directly via Python:
```bash
python3 live_monitor.py
```
Open **`http://127.0.0.1:8888`** in your browser to view live recovered conversations, keystroke drafts, and DLP security alerts.

---

### Mode B: Modular Headless CLI Engine

Use the modular CLI for forensic analysis, scripting, and threat hunting:

```bash
# Scan all local browser profiles and print a summary table
python3 -m tinker_tailor scan

# Deep scan with full conversation transcript display
python3 -m tinker_tailor scan --verbose

# Scan and export evidence to JSON with HMAC-SHA256 cryptographic seal
python3 -m tinker_tailor scan --output evidence.json --sign

# Scan a specific LevelDB directory
python3 -m tinker_tailor scan --path ~/Library/Application\ Support/Google/Chrome/Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb

# Run DLP credential scanner against all recovered artifacts
python3 -m tinker_tailor dlp
```

---

## 📊 Benchmark & Evaluation Reproduction

To reproduce all experimental tables and figures reported in the research paper:

```bash
# Verify environment and run synthetic validation tests
python3 verify_reproduction.py

# Reproduce all experimental tables (Tables 1–21)
python3 reproduce_tables.py

# Reproduce all publication figures (Figures 1–13)
python3 reproduce_figures.py
```

---

## 📄 Research Documentation & Papers

* 📑 **Full Research Paper:** [`docs/Tinker_Tailor_Research_Paper.pdf`](docs/Tinker_Tailor_Research_Paper.pdf)
* 🛡️ **Vulnerability Summary Report:** [`docs/Vulnerability_Summary_Report.pdf`](docs/Vulnerability_Summary_Report.pdf)
* 📋 **Responsible Disclosure Details:** [`DISCLOSURE.md`](DISCLOSURE.md)
* 🔬 **Artifact Reproduction Guide:** [`REPRODUCE.md`](REPRODUCE.md)

---

## 🛡️ Responsible Disclosure

We practice coordinated vulnerability disclosure. Preliminary findings regarding client-side data remanence, keystroke draft caching, and unencrypted blob persistence have been documented for notification to affected browser vendors and LLM providers. See [`DISCLOSURE.md`](DISCLOSURE.md) for full timelines and recommended mitigations.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
