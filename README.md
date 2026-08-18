# Liber Harvest

**Liber Harvest** is the standalone, provenance-preserving historical lore recovery tool for **Liber Vacuitatis**.

Its responsibility is narrow:

> ingest historical material, recover independently reusable lore, preserve exact provenance and epistemic status, and emit a normalized file-first library without deciding canon.

Liber Harvest does **not** depend on LV-Forge. LV-Forge, Obsidian tooling, or another downstream system may consume its file contract.

## Current release

- Application: **0.1.6**
- Frozen semantic contract: **`exegate-harvest/0.1.2`**
- Lore Fragment schema: **`lore-fragment/0.1.2`**
- Frozen clauses: **LF-01 through LF-16**
- Model-selection benchmark: **`model-selection/0.1`**

Application v0.1.6 adds the T01-T11 model-selection benchmark. It does not revise the frozen v0.1.2 lore semantics.

---

## 1. Execution model

Liber Harvest has a deterministic core and a replaceable semantic-extraction provider.

```text
Historical Exegate source
        │
        ▼
Exegate adapter
        │
        ▼
Semantic extraction provider
   ├── OpenAI       hosted
   ├── LM Studio    local
   └── Static       saved response, no live inference
        │
        ▼
Lore Fragment drafts
        │
        ▼
Deterministic Liber Harvest core
   ├── contract validation
   ├── exact provenance resolution
   ├── source spans + hashes
   ├── deterministic LFR IDs
   └── JSONL + manifests
```

The model/provider is an **untrusted semantic extractor**. It does not control final IDs, source hashes, provenance spans, or manifests.

**No live provider is selected implicitly.** A bare harvest command will not try to contact LM Studio or OpenAI.

See available modes:

```bash
liber-harvest providers
```

---

## 2. Install

Liber Harvest requires Python 3.12+.

```bash
git clone https://github.com/Kadav1/liber-harvest.git
cd liber-harvest

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Verify:

```bash
liber-harvest version
```

For development:

```bash
pip install -e ".[dev]"
pytest -q
```

Installed executable names:

```text
liber-harvest
lh
liber-harvest-benchmark
lh-benchmark
```

---

## 3. Create the local workspace

Run once from the repository root:

```bash
liber-harvest init
```

Runtime layout:

```text
liber-harvest/
├── data/                         # local source corpus; gitignored
│   ├── parsed/
│   │   ├── song_001.json
│   │   ├── song_002.json
│   │   └── ...
│   └── bundles/
│       └── EXE-BUNDLE-.../
│           └── exegate_run.json
│
├── harvest/                      # generated harvest output; gitignored
└── benchmark-results/            # generated benchmark evidence; gitignored
```

Parsed historical files belong under:

```text
data/parsed/song_001.json
data/parsed/song_002.json
...
```

An intact bundle may instead be placed under:

```text
data/bundles/EXE-BUNDLE-V-N-01/
└── exegate_run.json
```

---

## 4. Choose a provider

### OpenAI: no LM Studio required

```bash
export OPENAI_API_KEY="your-api-key"

liber-harvest doctor \
  --provider openai \
  --source data/parsed/song_001.json

liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider openai
```

Default hosted model:

```text
gpt-5.6
```

The frozen Harvest system instructions are sent automatically. Nothing should be pasted manually into a chat UI.

**Privacy boundary:** OpenAI provider mode sends the Exegate source to the hosted API. Use LM Studio when inference must remain local.

### LM Studio: optional local inference

```bash
liber-harvest doctor --provider lmstudio

liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider lmstudio \
  --model <lm-studio-model-key>
```

The generic default profile is:

```text
endpoint:       http://127.0.0.1:1234
context:        65536
reasoning:      off
temperature:    0.1
output tokens:  32768
timeout:        600 s
```

For constrained GPUs, lower `--context-length` explicitly. Model quantization and context length should be treated as part of the operational model profile.

If LM Studio token authentication is enabled:

```bash
export LIBER_HARVEST_LM_STUDIO_TOKEN="..."
```

### Static: no live model call

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --response-file extraction-response.json
```

Static mode materializes a previously generated extraction response. It cannot generate a new semantic extraction by itself.

---

## 5. No silent provider default

This command intentionally does **not** pick a backend unless `LIBER_HARVEST_PROVIDER` is configured:

```bash
liber-harvest harvest exegate data/parsed/song_001.json
```

Optional shell defaults:

```bash
export LIBER_HARVEST_PROVIDER=lmstudio
export LIBER_HARVEST_MODEL=<model-key>
```

or:

```bash
export LIBER_HARVEST_PROVIDER=openai
```

---

## 6. `doctor`

Provider-neutral source/runtime check:

```bash
liber-harvest doctor --source data/parsed/song_001.json
```

OpenAI:

```bash
liber-harvest doctor --provider openai --source data/parsed/song_001.json
```

LM Studio:

```bash
liber-harvest doctor --provider lmstudio --source data/parsed/song_001.json
```

---

## 7. Batch harvest with `--all`

`--all` belongs to the nested `harvest exegate` command:

```bash
liber-harvest harvest exegate --help
```

LM Studio batch example:

```bash
liber-harvest harvest exegate \
  --all \
  --source-root data/parsed \
  --provider lmstudio \
  --model <model-key> \
  --out harvest
```

It discovers `song_*.json` directly under the selected source root. Static `--response-file` is single-source only.

---

## 8. Validate output

```bash
liber-harvest validate harvest/library/fragments.jsonl
```

Full provenance validation:

```bash
liber-harvest validate \
  harvest/library/fragments.jsonl \
  --provenance
```

---

## 9. T01-T11 model-selection benchmark

Application v0.1.6 turns the frozen semantic calibration suite into a repeatable model-selection benchmark without changing the cases themselves.

The benchmark covers:

```text
T01  distributed lore / empty structured arrays
T02  structured objects / legacy bindings
T03  generated hooks / modality / wrappers
T04  legacy normalization / evidence layers / spans
T05  decomposition / taxonomy
T06  external mythic material / naming restraint
T07  repeated doctrine / dedupe
T08  imported terminology / evidence separation
T09  sensory material / intra-source merges
T10  competing interpretations / contradiction
T11  malformed and null legacy metadata
```

List the cases:

```bash
lh-benchmark cases
```

Show the score profile:

```bash
lh-benchmark profile
```

### Run one model through all T01-T11

For LM Studio:

```bash
lh-benchmark run \
  --provider lmstudio \
  --model <lm-studio-model-key> \
  --label qwen3.5-9b-q6k-16k \
  --context-length 16384 \
  --reasoning off \
  --corpus-root data \
  --hardware-note "11 GB VRAM; DDR3 system RAM"
```

`--label` should identify the exact model configuration being tested. Quantization matters. Do not label Q4 and Q6 runs identically.

Run only selected stress cases:

```bash
lh-benchmark run \
  --provider lmstudio \
  --model <model-key> \
  --cases T01,T03,T04,T07,T10
```

### Compare models

Each run writes a `summary.json`. Compare two or more:

```bash
lh-benchmark compare \
  benchmark-results/<qwen-run>/summary.json \
  benchmark-results/<granite-run>/summary.json \
  benchmark-results/<bonsai-run>/summary.json
```

The automatic compliance score is weighted as follows:

| Component | Weight |
|---|---:|
| contract validity | 25 |
| coverage | 20 |
| provenance | 15 |
| modality/evidence safety | 15 |
| legacy isolation | 10 |
| exact dedupe | 5 |
| review burden | 5 |
| wrapper isolation | 5 |

The aggregate selection score uses:

```text
80% mean deterministic compliance
+
20% machine-scoreable target-check pass percentage
```

**The score is a shortlist, not a semantic oracle.** Targets that cannot be judged safely without gold semantic annotations are marked informational. Final selection should inspect the top models' actual T01-T11 fragments, especially T01, T03, T04, T07, and T10.

Full benchmark specification:

- `calibration/MODEL-SELECTION-BENCHMARK-v0.1.md`
- `calibration/model-selection-profile-v0.1.json`

---

## 10. Harvest output structure

```text
harvest/
├── exegate/
│   ├── runs/
│   └── sources/
└── library/
    ├── fragments.jsonl
    └── relations.jsonl
```

Files are Harvest truth. Databases, vector indexes, search systems and LV-Forge imports are downstream projections.

Benchmark output is separate:

```text
benchmark-results/
└── BMS-<timestamp>-<provider>-<model>/
    ├── T01/result.json
    ├── ...
    ├── T11/result.json
    └── summary.json
```

---

## 11. Common failures

### `No extraction provider selected`

```bash
liber-harvest providers
```

Then select `--provider openai`, `--provider lmstudio`, or supply `--response-file`.

### LM Studio connection refused

LM Studio is optional. Start/check its server and run:

```bash
liber-harvest doctor --provider lmstudio
```

### A benchmark case cannot find its source

The benchmark resolves the historical calibration keys against the runtime corpus convention:

```text
data/parsed/song_*.json
data/bundles/EXE-BUNDLE-*/exegate_run.json
```

Use `--corpus-root` if your runtime corpus is elsewhere.

### Invalid model response

Liber Harvest performs syntax repair and the configured contract-repair cycle. If the response still violates the frozen contract, that benchmark case fails and receives compliance score `0`.

---

## 12. Frozen design boundary

The following remain authoritative and unchanged by v0.1.6:

- `ARCHITECTURE-FREEZE-v0.1.2.md`
- `FOLDER-STRUCTURE-FREEZE-v0.1.2.md`
- `contracts/exegate-harvest/v0.1.2/`
- `schemas/v0.1.2/`

The model-selection benchmark is an application-level calibration overlay. It does not alter the semantic contract or deterministic ownership boundary.
