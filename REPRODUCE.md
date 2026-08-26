# Reproducing TINKER TAILOR Results

## One-Command Verified Reproduction (recommended)

The fastest way to confirm the pipeline reproduces the paper's synthetic
results is the checksum-verified harness. It runs every deterministic,
synthetic experiment (recovery, ablation, Unicode, corruption,
schema-drift, role-assignment), collects their numeric outputs into a
canonical object, and checks it against a committed manifest
(`results/expected_manifest.json`). Exit code is 0 iff every metric
matches bit-for-bit (SHA-256 identical).

### With Docker (no local Python needed)

```bash
docker build -t tinker-tailor .
docker run --rm tinker-tailor        # runs verify_reproduction.py by default
```

Expected tail of output:

```
  recovery           PASS     7 metrics match
  ablation           PASS     7 metrics match
  unicode            PASS     28 metrics match
  corruption         PASS     48 metrics match
  schema_drift       PASS     8 metrics match
  role_assignment    PASS     6 metrics match
  manifest SHA-256 match: YES
  RESULT: PASS — all synthetic metrics reproduce exactly.
```

The same SHA-256 is produced under Python 3.11 (container) and 3.14
(host), i.e. the synthetic results are environment-independent.

### Without Docker

```bash
python verify_reproduction.py            # run + verify against manifest
python verify_reproduction.py --figures  # also regenerate paper figures
python verify_reproduction.py --update   # regenerate the manifest (maintainers)
```

Non-deterministic experiments (speed) and those requiring real browser
data (tool comparison, persistence) are intentionally excluded from the
checksum; they cannot be reproduced from the public artifact.

## Requirements


- Python 3.9+ (tested on 3.11)
- macOS, Windows 10/11, or Linux
- No external dependencies for core carving
- Optional: `matplotlib` for figures, `cryptography` for chain of custody

```bash
pip install -r requirements.txt   # optional, for figures
```

## Quick Start

### Run against synthetic test corpus

```bash
# ChatGPT (V8 binary carving)
python -m tinker_tailor --target test_corpus/chatgpt_profile/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb --bot chatgpt

# Claude (TipTap draft recovery)
python -m tinker_tailor --target test_corpus/claude_profile/IndexedDB/https_claude.ai_0.indexeddb.leveldb --bot claude

# DeepSeek (generic regex carving)
python -m tinker_tailor --target test_corpus/generic_profile/IndexedDB/https_chat.deepseek.com_0.indexeddb.leveldb --bot deepseek
```

### Run against live browser data (macOS/Windows/Linux)

```bash
python -m tinker_tailor --scan
```

### Run with DLP scanning and chain of custody

```bash
python -m tinker_tailor --scan --dlp --sign --output evidence.json
```

## Reproducing Paper Results

### Tables 4-9 (experiments)

```bash
python reproduce_tables.py
```

Runs: synthetic recovery (Table 4), speed benchmark (Table 5), ablation
(Table 11), Unicode recovery (Table 14), corruption tolerance (Table 15).

### Figures 1-12

```bash
python reproduce_figures.py
```

Generates all 11 PDF figures in `paper/figures/`.

### Individual experiments

```bash
# Experiment 1: Recovery accuracy (Table 4)
python -m evaluation.experiment_recovery

# Experiment 2: Speed benchmark (Table 5)
python -m evaluation.experiment_speed --trials 1000

# Experiment 3: Tool comparison (Table 6, requires real LevelDB data)
python -m evaluation.experiment_comparison --target <path> --bot chatgpt

# Experiment 4: Ablation study (Table 11)
python -m evaluation.experiment_ablation

# Experiment 5: Unicode recovery (Table 14)
python -m evaluation.experiment_unicode

# Experiment 6: Corruption tolerance (Table 15)
python -m evaluation.experiment_corruption

# Experiment 7: Schema-drift robustness (Table 10)
python -m evaluation.experiment_schema_drift

# Experiment 8: Role-assignment robustness (Table 11)
python -m evaluation.experiment_role_assignment

# Experiment 9: Persistence snapshot (requires real data)
python -m evaluation.experiment_persistence --target <path> --bot chatgpt --single
```

### Generate synthetic test corpus

```bash
python -m evaluation.generate_synthetic_corpus
```

Creates `test_corpus/` with synthetic V8 blobs, TipTap states, and a
manifest of expected recoverable content.

## Test Environment

Paper results were collected on:
- MacBook Pro (Apple M1, 16GB RAM, macOS Sonoma 14.x)
- Chrome 126, 23 active profiles
- Supplementary validation: Windows 11 Build 10.0.26200

## Docker

```bash
docker build -t tinker-tailor .
docker run --rm tinker-tailor                          # verified reproduction
docker run --rm tinker-tailor python -m tinker_tailor --help   # use the CLI
```
