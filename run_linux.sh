#!/bin/bash
# ============================================
#   Tinker Tailor LLM Spy — Ubuntu/Linux Scanner
# ============================================
set -e

echo "============================================"
echo "  Tinker Tailor LLM Spy - Linux Scanner"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install with: sudo apt install python3"
    exit 1
fi

echo "[*] OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release 2>/dev/null | head -1 || uname -a)"
echo "[*] Chrome: $(google-chrome --version 2>/dev/null || chromium-browser --version 2>/dev/null || echo 'not found')"
echo ""

# Create results folder
mkdir -p results_linux

echo "[1/3] Running full scan across all browser profiles..."
echo ""
python3 -m tinker_tailor.cli --scan --dlp --sign --output results_linux/evidence.json
echo ""

echo "[2/3] Capturing timing benchmarks..."
echo ""
python3 << 'PYEOF'
import time, json, os, platform
from tinker_tailor.carver.browser_paths import get_forensic_paths
from tinker_tailor.carver.engine import carve_leveldb_directory

paths = get_forensic_paths()
idb = {k: v for k, v in paths.get("indexeddb", {}).items() if os.path.exists(v)}
print(f"Found {len(idb)} active LevelDB directories")

total_prompts = 0
total_convos = 0
start = time.perf_counter()
for label, p in idb.items():
    prompts, convs = carve_leveldb_directory(p, label.split("_")[0], [])
    total_prompts += len(prompts)
    total_convos += len(convs)
    print(f"  {label}: {len(prompts)} prompts, {len(convs)} convs")
elapsed = (time.perf_counter() - start) * 1000

print(f"\nTotal: {total_prompts} prompts, {total_convos} conversations in {elapsed:.1f}ms")
print(f"Directories: {len(idb)}")

with open("results_linux/timing.txt", "w") as f:
    f.write(f"os={platform.platform()}\n")
    f.write(f"prompts={total_prompts}\n")
    f.write(f"conversations={total_convos}\n")
    f.write(f"directories={len(idb)}\n")
    f.write(f"time_ms={elapsed:.1f}\n")

print(f"\nTiming saved to results_linux/timing.txt")
PYEOF

echo ""
echo "[3/3] Generating summary..."
echo ""
python3 << 'PYEOF'
import json, os, platform

e = json.load(open("results_linux/evidence.json"))
s = e.get("stats", {})
d = e.get("dlp", {})

print(f"OS:        {platform.platform()}")
print(f"Prompts:   {s.get('total_prompts', 0)}")
print(f"Convos:    {s.get('total_conversations', 0)}")
print(f"DLP creds: {d.get('credentials', 'N/A')}")
print(f"DLP PII:   {d.get('pii', 'N/A')}")

bots = {}
for p in e.get("prompts", []):
    bot = p.get("bot", "?")
    bots[bot] = bots.get(bot, 0) + 1
print(f"By bot:    {bots}")

if os.path.exists("results_linux/timing.txt"):
    print(f"Timing:    {open('results_linux/timing.txt').read().strip()}")
PYEOF

echo ""
echo "============================================"
echo "  Done! Results saved to results_linux/"
echo "    - evidence.json   (full recovery data)"
echo "    - timing.txt      (benchmark numbers)"
echo "============================================"
echo ""
echo "Zip it and copy back to your Mac:"
echo "  zip -r results_linux.zip results_linux/"
echo ""
