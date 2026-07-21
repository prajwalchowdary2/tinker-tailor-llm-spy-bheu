# Tinker Tailor LLM Spy: Reconstructing "Deleted" Chats & Hijacking Sessions from Chromium LevelDB Caches

[![Target Venue](https://img.shields.io/badge/Venue-Black%20Hat%20Europe%20Briefings-red.svg)](https://www.blackhat.com/eu-24/)
[![Institution](https://img.shields.io/badge/Research-PES%20University-blue.svg)](https://pes.edu)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://python.org)

> **Official Repository for Black Hat Europe Briefings Research Paper**

---

## 📌 Executive Summary

**Tinker Tailor LLM Spy** is a specialized, zero-dependency, sub-50ms client-side forensic carving and threat-hunting framework designed to extract, reconstruct, and inspect Large Language Model (LLM) telemetry from volatile local storage cache files.

When users click "Delete Chat" inside interfaces like ChatGPT, Claude, Gemini, or Perplexity, cloud servers mark records for deletion, but local Chromium-based browsers (Chrome, Edge) and Electron desktop apps store telemetry inside **IndexedDB** databases backed by Google's **LevelDB** LSM-tree storage engine. Because LevelDB uses an append-only write-ahead log (`.log`) and uncompacted Sorted String Tables (`.sst`/`.ldb`), "deleted" prompts and assistant responses persist on disk for hours, days, or indefinitely.

---

## 👥 Authors & Affiliation

1. **Dr. Sapna V M** (Associate Professor, Dept of CSE, PES University, Bangalore) - `sapnavm@pes.edu`
2. **Prajwal Chowdary** (Student & Researcher, Dept of CSE, PES University, Bangalore) - `prajwalchowdary5@gmail.com`
3. **Prasad H B** (Professor & Director of ISFCR, Dept of CSE, PES University, Bangalore) - `prasadhb@pes.edu`

**Institution:** Department of Computer Science & Engineering, PES University, Bangalore, India  
**Target Venue:** Black Hat Europe Briefings  
**Category:** Enterprise Security / Malware Analysis & Incident Response / Applied Research

---

## 🔥 Key Features

* 🚀 **V8 LevelDB SSTable & Log Carver:** Parses uncompacted Chrome/Edge LevelDB storage files (`.sst`, `.ldb`, `.log`) to recover deleted ChatGPT, Gemini, DeepSeek, and Perplexity message trees without triggering database locks.
* ✍️ **Claude TipTap Keystroke Draft Recovery:** Extracts unsubmitted draft inputs stored in Claude's `tipTapEditorState` JSON cache *before* the user clicks 'Send'.
* 💻 **IDE Agent Telemetry Carving:** Automates extraction across Cursor IDE (`agent-transcripts` JSONL logs) and VS Code Copilot SQLite databases (`state.vscdb`).
* 🛡️ **Real-Time Shadow AI DLP Engine:** Scans carved prompts on-the-fly for leaked credentials (AWS keys, OpenAI API tokens, Slack bearer tokens) and PII with severity scoring.
* ⚡ **41ms Threat Vector Benchmark (`verity_stealer.py`):** Headless Python proof-of-concept demonstrating how rapid adversary execution can harvest local LLM telemetry before standard EDR solutions generate alerts.
* 📜 **Cryptographic Chain of Custody:** HMAC-SHA256 integrity signatures on evidence packages verified client-side using Web Cryptography API (`window.crypto.subtle.verify`).

---

## 📐 Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                            TARGET ENDPOINT ENVIRONMENT                            |
|                                                                                   |
|  +--------------------+   +-----------------------+   +------------------------+  |
|  | Chrome / Edge IDB  |   | Cursor IDE JSONL Logs |   | VS Code Copilot DB     |  |
|  | (.log / .ldb / .sst|   | (agent-transcripts)   |   | (state.vscdb)          |  |
|  +---------+----------+   +-----------+-----------+   +-----------+------------+  |
+------------|--------------------------|---------------------------|---------------+
             |                          |                           |
             +--------------------------+---------------------------+
                                        | (Read-Only Copy & Byte Scan)
                                        v
                     +--------------------------------------+
                     | live_monitor.py (Carving Daemon)     |
                     |  - Dynamic Profile Discovery         |
                     |  - Varint & V8 Deserialization       |
                     |  - HMAC-SHA256 Evidence Seal         |
                     +------------------+-------------------+
                                        |
                                        v
                     +--------------------------------------+
                     | Web Dashboard UI (index.html/app.js) |
                     |  - Real-time Threat Heatmap          |
                     |  - Interactive Conversation Trees    |
                     |  - DLP Credential Alerts             |
                     +--------------------------------------+
```

---

## ⚙️ Requirements & Installation

* **Operating System:** macOS, Windows 10/11, or Linux
* **Python:** Python 3.8+ (Zero third-party C++ compiled bindings required)

```bash
# Clone the repository
git clone https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu.git
cd tinker-tailor-llm-spy-bheu

# Install lightweight requirements
pip install -r requirements.txt
```

---

## 🚀 Usage

### 1. Launching the Live Monitoring Dashboard

**On macOS / Linux:**
```bash
./start.sh
```

**On Windows:**
```cmd
start.bat
```

Once running, navigate to `http://localhost:8000/index.html` in your browser to access the forensic dashboard.

To stop the services:
```bash
./stop.sh
```

### 2. Headless Infostealer PoC Benchmark

To execute the 50ms headless benchmarking PoC script:

```bash
python3 verity_stealer.py
```

---

## 🛡️ Mitigations & Countermeasures

To mitigate client-side LLM telemetry leakage on enterprise endpoints:

1. **Browser Cleanup Policies:** Configure GPO / MDM policies to clear IndexedDB and web cache files upon browser exit.
2. **Full Disk Encryption:** Mandate BitLocker (Windows) or FileVault (macOS) to prevent offline extraction of LevelDB directories.
3. **EDR Path Monitoring:** Configure Endpoint Detection and Response rules to flag unprivileged access to Chromium profile paths (`IndexedDB/*.leveldb`).

---

## 📄 Citation & Whitepaper

For detailed technical analysis of V8 deserialization bitwise operations, varint decoding, Smi-shifted index keys, and LevelDB LSM compaction dynamics, please refer to [whitepaper.md](whitepaper.md).

```bibtex
@inproceedings{tinkertailorllmspy2024,
  title={Tinker Tailor LLM Spy: Reconstructing "Deleted" Chats & Hijacking Sessions from Chromium LevelDB Caches},
  author={Sapna V M and Prajwal Chowdary and Prasad H B},
  booktitle={Black Hat Europe Briefings},
  year={2024},
  institution={PES University}
}
```

---

## ⚖️ License & Disclaimer

This software is released under the **MIT License**. The codebase is created strictly for educational, defensive, forensic research, and authorized incident response purposes presented at Black Hat Europe.
