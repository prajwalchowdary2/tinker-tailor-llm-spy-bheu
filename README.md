# Tinker Tailor LLM Spy: Reconstructing "Deleted" Chats & Hijacking Sessions from Chromium LevelDB Caches

<div align="center">

[![Target Venue](https://img.shields.io/badge/Venue-Black%20Hat%20Europe%20Briefings-red.svg?style=for-the-badge&logo=target)](https://www.blackhat.com/eu-24/)
[![Institution](https://img.shields.io/badge/Research-PES%20University%20ISFCR-blue.svg?style=for-the-badge&logo=google-scholar)](https://pes.edu)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge&logo=open-source-initiative)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-3776AB.svg?style=for-the-badge&logo=python)](https://python.org)
[![Sub-150ms Scan](https://img.shields.io/badge/Scan%20Speed-%3C150ms-orange.svg?style=for-the-badge&logo=speedtest)](https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu)

**Official Research Repository for Black Hat Europe Briefings & Digital Forensics Artifacts**

[Overview](#-executive-summary) • [Architecture](#-system-architecture) • [Vulnerabilities](#-key-vulnerabilities-uncovered) • [Quick Start](#-quick-start) • [Evaluation](#-empirical-evaluation--reproduction) • [Documentation](#-research-documentation)

</div>

---

## 📌 Executive Summary

**Tinker Tailor LLM Spy** is a specialized, zero-dependency client-side forensic carving and threat-hunting framework designed to extract, reconstruct, and inspect Large Language Model (LLM) telemetry from volatile local storage cache files.

When users click **"Delete Chat"** inside web interfaces like ChatGPT, Claude, Gemini, or Perplexity, cloud servers mark records for deletion. However, local Chromium-based browsers (Chrome, Edge, Brave) and Electron desktop clients store client telemetry inside **IndexedDB** databases backed by Google's **LevelDB** Log-Structured Merge (LSM) storage engine. Because LevelDB relies on append-only Write-Ahead Logs (`.log`) and delayed background SSTable compactions (`.ldb`), "deleted" prompts, assistant responses, and intermediate keystroke drafts persist on disk for days, weeks, or indefinitely.

---

## 👥 Authors & Affiliation

* **Dr. Sapna V M** (Associate Professor, Dept of CSE, PES University, Bangalore) — `sapnavm@pes.edu`
* **Prajwal Chowdary** (Student & Researcher, Dept of CSE, PES University, Bangalore) — `prajwalchowdary5@gmail.com`
* **Prasad H B** (Professor & Director of ISFCR, Dept of CSE, PES University, Bangalore) — `prasadhb@pes.edu`

**Research Lab:** Information Security Forensics & Cyber Resilience (ISFCR) Lab  
**Institution:** Department of Computer Science & Engineering, PES University, Bangalore, India  
**Target Venue:** Black Hat Europe Briefings  
**Category:** Enterprise Security / Malware Analysis & Incident Response / Applied Vulnerability Research

---

## 📐 System Architecture

```mermaid
flowchart TD
    subgraph SOURCES[" 🌐 Target Endpoint Data Sources (Unencrypted Local Cache) "]
        direction TB
        S1["<b>Chromium IndexedDB LevelDB</b><br/><code>.log</code> WAL & <code>.ldb</code> SSTables<br/><i>ChatGPT / Claude / Gemini / DeepSeek</i>"]
        S2["<b>IndexedDB Binary Blob Store</b><br/><code>.indexeddb.blob/</code><br/><i>10MB Raw PDF & Code Attachments</i>"]
        S3["<b>Claude TipTap Cache</b><br/><code>tipTapEditorState</code><br/><i>Pre-Send Keystroke Drafts</i>"]
        S4["<b>Electron Desktop Apps</b><br/><code>com.openai.atlas</code><br/><i>WebRTC ECDSA Keys & Transcripts</i>"]
        S5["<b>Chrome Gemini Extension</b><br/><code>glic</code> Local Storage<br/><i>Conversation State & Keys</i>"]
        S6["<b>AI IDE Agent Logs</b><br/>Cursor <code>.jsonl</code> & Copilot <code>.vscdb</code><br/><i>Agent Steps & Tool Invocations</i>"]
    end

    subgraph ENGINE[" ⚙️ TINKER TAILOR FORENSIC CARVING ENGINE "]
        direction TB
        E1["<b>Dynamic Discovery & Lock Bypass</b><br/>Multi-profile traversal across Chrome, Edge, Brave & Desktop<br/><i>Lock-Free Read-Only Binary Stream Extraction</i>"]
        E2["<b>Snappy Decompression</b><br/>Pure Python LZ77/Snappy decompressor<br/><i>Uncompacted SSTable Block Decoding</i>"]
        E3["<b>V8 Structured Clone Deserializer</b><br/>Varint parsing, Smi-shift role resolution, <code>0x63</code> UTF-16LE<br/><i>Nesting Depth Tracker & Binary Anchor Detection</i>"]
        E4["<b>TipTap Fragment Assembler</b><br/>Recursive JSON extraction & deduplication<br/><i>Keystroke Timeline Rebuilder</i>"]
        
        E1 --> E2
        E1 --> E3
        E1 --> E4
    end

    subgraph SECURITY[" 🛡️ Forensic Security & DLP Pipeline "]
        direction TB
        P1["<b>Conversation Threading Engine</b><br/>Smi-parity role assignment & timeline reconstruction"]
        P2["<b>Real-Time Shadow AI DLP Scanner</b><br/>AWS keys, OpenAI tokens, Slack bearer secrets & PII regex"]
        P3["<b>HMAC-SHA256 Chain of Custody</b><br/>Cryptographic evidence sealing & integrity validation"]
        
        P1 --> P2 --> P3
    end

    subgraph INTERFACES[" 🚀 Dual Operational Interfaces "]
        direction LR
        UI["<b>Interactive Web Dashboard</b><br/><code>live_monitor.py</code> (Port 8000)<br/>• Real-time threat heatmap<br/>• Interactive conversation tree<br/>• Live DLP credential alerts<br/>• WebCrypto HMAC verification"]
        CLI["<b>Headless Incident Response CLI</b><br/><code>python3 -m tinker_tailor scan</code><br/>• Sub-150ms endpoint scan<br/>• JSON/CSV forensic telemetry<br/>• Scriptable EDR / SIEM integration<br/>• Zero compiled dependencies"]
    end

    SOURCES ==>|Lock-Free Binary Carve| E1
    E2 --> P1
    E3 --> P1
    E4 --> P1
    P3 ==> UI
    P3 ==> CLI

    classDef src fill:#1e293b,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;
    classDef eng fill:#0f172a,stroke:#818cf8,stroke-width:1.5px,color:#f8fafc;
    classDef sec fill:#1e1b4b,stroke:#c084fc,stroke-width:1.5px,color:#f8fafc;
    classDef out fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#f8fafc;

    class S1,S2,S3,S4,S5,S6 src;
    class E1,E2,E3,E4 eng;
    class P1,P2,P3 sec;
    class UI,CLI out;
```

---

## 🔥 Key Vulnerabilities Uncovered (13 Classes)

| # | Vulnerability Class | Severity | Affected Platform | Root Cause & Real-World Impact |
|:---:|:---|:---:|:---|:---|
| **1** | **LevelDB LSM Data Remanence** | 🔴 CRITICAL | ChatGPT, Claude, Gemini | Deleted conversations persist in uncompacted WAL (`.log`) and SSTable (`.ldb`) records. **506 text artifacts recovered (70.8% UI-deleted); 83-day persistence.** |
| **2** | **Plaintext Document Blob Survival** | 🔴 CRITICAL | Claude, Chromium | Uploaded attachments (PDFs, source code, data sheets) saved as raw unencrypted files in `.indexeddb.blob/`. **10MB confidential PDF recovered intact.** |
| **3** | **Pre-Send Keystroke Draft Caching** | 🟠 HIGH | Claude (Anthropic) | In-flight prompts written to `tipTapEditorState` in IndexedDB *before* clicking 'Send'. **148 unsubmitted draft fragments recovered.** |
| **4** | **Cursor AI IDE Composer Leakage** | 🟠 HIGH | Cursor IDE | `state.vscdb` SQLite stores full Composer AI chat sessions, model configs, and terminal command history. |
| **5** | **Service Worker CacheStorage Persistence** | 🟠 HIGH | Gemini, Perplexity | Cached AI API responses and authentication handshakes persist in CacheStorage after deletion. |
| **6** | **SNSS Session Restore Tab Remanence** | 🟡 MEDIUM | All Chromium | Binary SNSS session files retain AI conversation tab URLs with exact UUIDs even after tab close. |
| **7** | **Omnibox Typed Query Leakage** | 🟡 MEDIUM | All Chromium | `Shortcuts` SQLite database stores raw user-typed search text with destination URLs and timestamps. |
| **8** | **Mass Session Cookie Exposure** | 🔴 CRITICAL | ChatGPT, Claude, Gemini | **631 active AI session cookies** across 23 profiles. Encrypted with Keychain-derived key, but decryptable by any same-user process. |
| **9** | **Conversation URL + Title Persistence** | 🟠 HIGH | All Chromium | **38 conversation URLs with descriptive titles** (e.g., "Android encryption forensics methodology") persist in History DB, revealing user intent without chat content. |
| **10** | **AI Download Record Trail** | 🟠 HIGH | Claude, ChatGPT | **65 download records** from AI portals (exam papers, reports, honeypot tools) with full source URLs and file metadata. |
| **11** | **Extension API Key & JWT Leakage** | 🔴 CRITICAL | Chrome Extensions | **OpenAI `sk-` API keys and RS256 JWT tokens** stored in plaintext in extension LevelDB storage. Includes decoded email and auth claims. |
| **12** | **Desktop App Private Key Exposure** | 🔴 CRITICAL | ChatGPT Desktop (`com.openai.atlas`) | **3 ECDSA private cryptographic keys** (`-----BEGIN PRIVATE KEY-----`) stored in plaintext IndexedDB WAL alongside user IDs and conversation titles. |
| **13** | **Cross-Profile Isolation Failure** | 🟠 HIGH | All Chromium | **All 24+ profile IndexedDB directories owned by same UID (501)**. Zero OS-level isolation — a single user-level process reads every profile's data without privilege escalation. |

> ⚠️ **Keychain Encryption Gap:** macOS Keychain only encrypts cookie values and saved passwords (2 SQLite columns). **95%+ of sensitive artifacts** — conversations, private keys, API keys, documents, history, autofill — are stored in completely unprotected plaintext files.

---

## ⚡ Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu.git
cd tinker-tailor-llm-spy-bheu

# Optional: Install requirements for cryptographic signing & figure generation
pip install -r requirements.txt
```

### 2. Launching the Interactive Web Dashboard
Run the background daemon and open the interactive dashboard:

```bash
# On macOS / Linux:
./start.sh

# On Windows:
start.bat
```
Navigate to **`http://127.0.0.1:8000`** in your browser to view live recovered conversations, draft fragments, and DLP security alerts.

### 3. Running the Headless CLI Engine

```bash
# Full 13-Layer forensic audit (all vulnerability classes)
python3 -m tinker_tailor.cli --all

# Generate HTML forensic triage report (counts only, no raw data)
python3 -m tinker_tailor.cli --all --report

# Original 7 layers only (LevelDB, blobs, sessions, shortcuts, cache, cursor)
python3 -m tinker_tailor.cli --scan

# Deep Chrome analysis only (Layers 8-13: cookies, history, downloads, extensions, desktop apps, isolation)
python3 -m tinker_tailor.cli --deep

# Individual layer scanning
python3 -m tinker_tailor.cli --cookies        # Layer 8: AI session cookies
python3 -m tinker_tailor.cli --extensions     # Layer 11: Extension API key & JWT leakage
python3 -m tinker_tailor.cli --desktop        # Layer 12: Desktop app private keys
python3 -m tinker_tailor.cli --isolation      # Layer 13: Cross-profile isolation check

# Export signed evidence to JSON
python3 -m tinker_tailor.cli --all --output evidence.json --sign
```


---

## 📊 Empirical Evaluation & Reproduction

To reproduce all experimental results, tables, and figures:

```bash
# Run 1-command verification across all synthetic validation suites
python3 verify_reproduction.py

# Reproduce all experimental tables (Tables 1–21)
python3 reproduce_tables.py

# Reproduce all publication figures (Figures 1–13)
python3 reproduce_figures.py
```

### Measured Performance Summary
* **Execution Speed:** 147–163 ms across 23 profiles (506 text artifacts).
* **ChatGPT V8 Recovery:** 100% (Grep & JSON scan recover 0%).
* **Claude TipTap Recovery:** 100% (Grep recovers 21%, JSON scan recovers 0%).
* **Corruption Tolerance:** 0% crashes across 72 corrupted test cases.
* **Multilingual Unicode Support:** 100% (Devanagari, CJK, Japanese, Math symbols, Emoji).

---

## 📄 Research Documentation

* 📑 **Black Hat Europe Briefings Paper:** [`docs/Tinker_Tailor_LLM_Spy_Paper.pdf`](docs/Tinker_Tailor_LLM_Spy_Paper.pdf)
* 🛡️ **Executive Vulnerability Report:** [`docs/Vulnerability_Summary_Report.pdf`](docs/Vulnerability_Summary_Report.pdf)
* 🖥️ **Presentation Slides Deck:** [`docs/presentation_slides.pdf`](docs/presentation_slides.pdf)
* 🎨 **Research Conference Poster:** [`docs/research_poster.pdf`](docs/research_poster.pdf)
* 🛠️ **Black Hat Arsenal Proposal:** [`docs/BlackHat_Europe_Arsenal_Proposal.pdf`](docs/BlackHat_Europe_Arsenal_Proposal.pdf)
* 📖 **In-Depth Technical Whitepaper:** [`docs/whitepaper.md`](docs/whitepaper.md)
* 📋 **Responsible Disclosure Details:** [`DISCLOSURE.md`](DISCLOSURE.md)

---

## 🛡️ Responsible Disclosure

We practice coordinated vulnerability disclosure. Preliminary findings regarding client-side data remanence, keystroke draft caching, and unencrypted blob persistence have been documented for notification to affected browser vendors and LLM providers. See [`DISCLOSURE.md`](DISCLOSURE.md) for full timelines and recommended mitigations.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
