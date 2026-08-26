# Coordinated Disclosure — Draft Vendor Reports

Status: **prepared, not yet sent.** Per our double-blind policy we withhold
transmission until authorship is finalized, then initiate coordinated
disclosure on a 90-day timeline (Google Project Zero / CERT-CC norms)
*before* any public release of the tool or the infostealer
proof-of-concept.

Affected parties and the specific issues reported are summarized in the
paper (Responsible Disclosure section). The three draft reports follow.

---

## 1. Google (Chromium / LevelDB) — security@google.com

Subject: Coordinated disclosure — deleted IndexedDB records recoverable
due to deferred LevelDB compaction

We are academic researchers reporting a client-side data-remanence issue
in Chromium under a 90-day coordinated timeline. Chromium's IndexedDB
(LevelDB / LSM-tree) retains "deleted" records as tombstones until
activity-driven background compaction; on low-activity profiles we
observed deleted LLM-conversation records remaining recoverable for up to
83 days. IndexedDB values are also unencrypted at rest and readable by any
same-user process. We recover this data with a pure-Python V8
structured-clone + Snappy parser that takes no database lock (works on
live profiles). We would welcome a tracking number and can share our
write-up and a reproduction.

Requested fixes: optional synchronous compaction on IndexedDB delete
(per-origin); at-rest encryption of IndexedDB values and WAL entries via
an OS-keychain-derived key.

---

## 2. OpenAI — security@openai.com (or disclosure form)

Subject: Coordinated disclosure — ChatGPT conversations persist in
client-side IndexedDB after UI deletion

Under a 90-day coordinated timeline: ChatGPT conversation content stored
in browser IndexedDB (V8 structured-clone binary) remains recoverable
after users delete conversations in the UI, because deletion does not
force LevelDB compaction. Across one workstation we recovered 358
artifacts from UI-deleted conversations. Suggested mitigations: minimize
client-side caching of conversation content, or encrypt cached content
with a Web Crypto key and enforce proactive deletion / TTLs. Happy to
share details and a reproduction.

---

## 3. Anthropic — security@anthropic.com

Subject: Coordinated disclosure — Claude TipTap editor caches unsubmitted
drafts / keystrokes in IndexedDB

Under a 90-day coordinated timeline: Claude's TipTap / ProseMirror editor
persists editor state to IndexedDB on every keystroke, so unsubmitted
prompt drafts and per-keystroke fragments (including text typed then
deleted before Send) remain recoverable from disk. Suggested mitigation:
disable or session-limit per-keystroke persistence, and encrypt any
cached editor state. Happy to share our write-up and a reproduction.
