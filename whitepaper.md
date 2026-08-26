# Tinker Tailor LLM Spy: Reconstructing "Deleted" Chats & Hijacking Sessions from Chromium LevelDB Caches

**Authors:**
1. **Dr. Sapna V M** (Associate Professor, Dept of CSE, PES University, Bangalore) — `sapnavm@pes.edu`
2. **Prajwal Chowdary** (Student & Researcher, Dept of CSE, PES University, Bangalore) — `prajwalchowdary5@gmail.com`
3. **Prasad H B** (Professor & Director of ISFCR, Dept of CSE, PES University, Bangalore) — `prasadhb@pes.edu`

**Organization:** Information Security Forensics & Cyber Resilience (ISFCR) Lab, Department of Computer Science & Engineering, PES University, Bangalore, India  
**Target Venue:** Black Hat Europe Briefings  
**Category:** Enterprise Security / Malware Analysis & Incident Response / Applied Vulnerability Research  
**Official Repository:** `https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu`

---

## Abstract

As Large Language Model (LLM) web portals and native desktop applications become standard corporate utilities, proprietary source code, internal spreadsheets, and API credentials are routinely processed by users. When a user clicks **"Delete Chat"** inside interfaces like ChatGPT, Claude, or Gemini, they expect their local footprint to be permanently erased. However, because Chromium-based browsers (Chrome, Edge, Brave) and Electron desktop clients store this telemetry inside IndexedDB databases backed by Google's LevelDB engine and file blob stores, these deleted records persist on disk in Write-Ahead Logs (`.log`), uncompacted Sorted String Tables (`.sst`/`.ldb`), and unencrypted blob trees (`.indexeddb.blob/`).

This paper details our reverse engineering of client-side LLM storage schemas, V8 structured clone deserialization, and parallel binary blob stores. We uncover four critical endpoint vulnerability classes:
1. **LSM-Tree Data Remanence:** 70.8% of recovered chat artifacts across 23 real-world profiles had already been deleted from the cloud UI.
2. **Pre-Submission Keystroke Caching:** Claude's TipTap editor persists unsubmitted keystroke drafts to disk *before* the user clicks 'Send'.
3. **Unencrypted Document Blobs:** Uploaded proprietary files (10MB PDFs, code files) are stored as raw, plaintext binary blobs on disk, persisting indefinitely past chat deletion.
4. **Cryptographic Key Exposure:** Electron desktop apps (ChatGPT `com.openai.atlas`) persist raw WebRTC ECDSA private keys (`BEGIN PRIVATE KEY`) in unencrypted LevelDB logs alongside user chat transcripts.

Finally, we introduce **Tinker Tailor LLM Spy**, a zero-dependency, sub-150ms client-side forensic and threat-hunting framework to extract, reconstruct, and inspect deleted LLM telemetry with cryptographic chain-of-custody verification.

---

## 1. Introduction: The Ephemeral AI Fallacy

The security industry has focused heavily on Generative AI security at the perimeter: prompt injection defenses, model jailbreaks, and cloud data governance. Virtually unmapped, however, is the client-side forensic footprint left behind by web interfaces and native wrapper applications on endpoint workstations.

When a user deletes a chat thread, the cloud-side database marks the conversation as deleted. Locally on the endpoint, however, the deletion is merely written as a LevelDB tombstone or index pointer modification. Because LevelDB is an append-only Log-Structured Merge-tree (LSM tree), the serialized data blocks containing the prompts, assistant replies, and system instructions remain intact in write-ahead log records or orphaned data blocks until background compaction occurs—a process that can take hours, days, or never trigger if write volume is low. This creates an expansive forensic window: any local unprivileged process running as the current user can recover sensitive, supposedly "deleted" intellectual property.

---

## 2. Deep Vulnerability Analysis

### 2.1. Vulnerability 1: LevelDB LSM-Tree Chat Remanence (ChatGPT & Gemini)
Chromium browsers implement IndexedDB using LevelDB. When ChatGPT serializes conversations, it encodes them using V8's internal structured clone binary format (`ValueSerializer`). 

* **The Exposure:** Active writes are appended sequentially to Write-Ahead Log (`.log`) files. In low-write database partitions, WAL records are never flushed to disk SSTables, and SSTable Level-0 files are not compacted.
* **Empirical Validation:** Across a 23-profile scan on an active macOS workstation, we recovered **506 text artifacts** comprising **174 ChatGPT user prompts, 154 assistant replies, 148 Claude keystroke fragments, and 30 submitted Claude prompts**. Crucially, **358 of these artifacts (70.8%) were verified to have already been deleted from the user's web interface**. One deleted conversation artifact remained intact on disk **83 days after creation**.

### 2.2. Vulnerability 2: Pre-Submission Keystroke Draft Persistence (Claude TipTap)
Anthropic's Claude web application utilizes the TipTap rich-text framework. To provide auto-recovery during browser crashes, Claude continuously serializes the user's unsubmitted editor state into IndexedDB (`tipTapEditorState`).

* **The Exposure:** As the user types into the prompt box, keystrokes are written to local storage in real-time *before* the user clicks 'Send' or presses Enter. If a user types sensitive credentials or proprietary code, changes their mind, and deletes the text or closes the tab, **the abandoned draft remains fully recoverable on disk**.
* **Forensic Impact:** We recovered 148 intermediate keystroke fragments containing abandoned code snippets and half-formulated prompts from uncompacted SSTables.

### 2.3. Vulnerability 3: Plaintext Uploaded Document & File Blobs (`.indexeddb.blob/`)
When users upload attachments to web LLMs (e.g. PDFs, images, spreadsheets, Python scripts), Chromium does not embed large files into LevelDB records directly; instead, it stores them in a dedicated blob directory:
```
~/Library/Application Support/Google/Chrome/Profile */IndexedDB/https_claude.ai_0.indexeddb.blob/
```

* **The Exposure:** Files are stored as **completely unencrypted, raw binary files** with standard user permissions (`-rw-------`). We recovered a **10MB PDF document** from Claude's blob store (`PDF document, version 1.5`) that remained fully intact on disk long after the corresponding conversation was deleted.
* **Bounty/Disclosure Significance:** Any same-user background script or infostealer can harvest complete enterprise documents, NDAs, and source files without needing root privileges or database decryption keys.

### 2.4. Vulnerability 4: Plaintext WebRTC ECDSA Private Keys in Desktop Apps
The official ChatGPT Desktop application (`com.openai.atlas`) runs as an Electron-based application utilizing Chromium storage mechanics.

* **The Exposure:** In `com.openai.atlas/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb/`, we recovered **raw ECDSA private cryptographic keys** (`-----BEGIN PRIVATE KEY-----`) stored in plaintext alongside conversation titles, user IDs, and chat text in `webrtc-cert-db` entries.
* **Threat Model:** Storing private cryptographic keys in plaintext alongside chat transcripts in an unencrypted user-space database allows an adversary to exfiltrate cryptographic identities and chat telemetry in a single read operation.

### 2.5. Vulnerability 5: Google Gemini Assistant (`glic`) Local Storage Persistence
Chrome's built-in Gemini extension (`glic`) persists conversation keys (`BARD_EMBED_CHAT_STORAGE_KEY`, `BARD_EMBED_CHAT_STORAGE_KEY_V2`) and session state in Local Storage LevelDB files, confirming that Google's own integrated browser assistant shares the identical client-side persistence exposure.

---

## 3. Reverse Engineering V8 Binary Deserialization

Chromium serializes IndexedDB values using V8's internal binary format:

### 3.1. Varint Decoding
V8 encodes integers using Protocol Buffer style varints. Every byte's MSB (bit 7) is a continuation flag; the lower 7 bits concatenate to form the integer value:
```python
def read_varint(data, offset):
    res, shift = 0, 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        res |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return res, offset
```

### 3.2. String Tagging & Unicode (0x22 vs 0x63)
* **OneByteString (`0x22`):** ASCII string. Length denotes character and byte count.
* **TwoByteString (`0x63`):** UTF-16LE string. **The varint length represents total byte count**, not character count. The carver reads exactly `length` bytes and decodes with `utf-16le`.

### 3.3. Smi-Shifted Message Roles
V8 serializes array keys as Small Integers (Smi) shifted left by 1 bit (`encoded = actual << 1`):
$$\text{role} = \begin{cases} 
\text{"user"} & \text{if } (\text{index} \mathbin{/} 2) \bmod 2 = 1 \\
\text{"assistant"} & \text{if } (\text{index} \mathbin{/} 2) \bmod 2 = 0 
\end{cases}$$

### 3.4. Nesting Depth Tracking
Object starts (`0x6f`) and array starts (`0x61`) increment depth; object ends (`0x7b`) decrement depth. This prevents premature parser termination when encountering nested message metadata.

---

## 4. Tinker Tailor LLM Spy Architecture

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

### 4.1. Lock-Free Live Carving
Standard LevelDB drivers acquire an exclusive OS lock (`LOCK` file). Tinker Tailor bypasses database locks by opening raw `.log` and `.ldb` files in read-only binary mode (`'rb'`), enabling zero-disruption live triage during active user sessions.

### 4.2. Real-Time Shadow AI DLP Scanner
All carved strings are passed through a regex-based DLP engine detecting:
* AWS Access Keys (`AKIA[0-9A-Z]{16}`)
* OpenAI API Keys (`sk-[a-zA-Z0-9]{48}`)
* Slack Bearer Tokens (`xox[baprs]-[0-9a-zA-Z]{10,48}`)
* Generic JWTs, Bearer Auth headers, and High-Entropy Secrets.

### 4.3. Cryptographic Chain of Custody
Every carved evidence package is canonicalized and signed using HMAC-SHA256:
$$\text{signature} = \text{HMAC-SHA256}(K_{\text{session}}, \text{CanonicalJSON}(\text{evidence}))$$
The interactive dashboard verifies this signature client-side via `window.crypto.subtle.verify`.

---

## 5. Empirical Evaluation Summary

| Benchmark Metric | Measured Result |
|---|---|
| **Total Profiles Scanned** | 23 browser profiles (macOS workstation) |
| **Total Text Artifacts Recovered** | 506 artifacts |
| **UI-Deleted Chat Recovery Rate** | 70.8% (358 / 506 artifacts) |
| **Longest Observed Persistence** | 83 days (low write volume partition) |
| **End-to-End Scan Speed** | 147–163 ms across all 23 profiles |
| **Baseline Grep / JSON Scan Recovery** | 0% on ChatGPT V8 data; 21% on Claude |
| **Data Corruption Tolerance** | 0% crashes across 72 corrupted test cases |
| **Multi-Language Unicode Support** | 100% (Devanagari, CJK, Japanese, Emoji) |

---

## 6. Defensive Mitigations

1. **OS-Level Storage Encryption:** Enforce full-disk encryption (FileVault, BitLocker) and extend DPAPI protections to IndexedDB storage directories.
2. **Session Eviction GPO Policies:** Configure browser enterprise policies to purge IndexedDB cache files and `.indexeddb.blob` directories on browser termination.
3. **Endpoint Behavioral Telemetry:** Deploy EDR behavioral rules monitoring unprivileged process enumeration of `%LOCALAPPDATA%\Google\Chrome\User Data\*\IndexedDB\` and `~/Library/Application Support/Google/Chrome/*/IndexedDB/`.

---

## 7. Conclusion

This research confirms that client-side Generative AI deletion is an illusion. Due to LevelDB LSM-tree mechanics, pre-submission keystroke caching, and unencrypted blob storage, sensitive user prompts, uploaded enterprise documents, and cryptographic private keys persist on disk long after deletion. **Tinker Tailor LLM Spy** delivers a sub-150ms, zero-dependency forensic framework to empower incident responders and security teams to audit shadow AI telemetry and secure the endpoint frontier.
