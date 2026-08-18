# Liber Harvest

**Liber Harvest** is the standalone, provenance-preserving historical lore recovery tool for **Liber Vacuitatis**.

Its responsibility is narrow:

> ingest historical material, recover independently reusable lore, preserve exact provenance and epistemic status, and emit a normalized file-first library without deciding canon.

Liber Harvest does **not** depend on LV-Forge. LV-Forge, Obsidian tooling, or another downstream system may consume its file contract.

## Current release

- Application: **0.1.5**
- Frozen semantic contract: **`exegate-harvest/0.1.2`**
- Lore Fragment schema: **`lore-fragment/0.1.2`**
- Frozen clauses: **LF-01 through LF-16**

Application v0.1.5 changes provider operation only. It does not revise the frozen v0.1.2 lore semantics.

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

Both executable names are installed:

```text
liber-harvest
lh
```

---

## 3. Create the local workspace

Run once from the repository root:

```bash
liber-harvest init
```

This creates the local runtime directories:

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
└── harvest/                      # generated output; gitignored
```

### Parsed Exegate JSON

For the historical parsed corpus, place files here:

```text
data/parsed/song_001.json
data/parsed/song_002.json
...
```

### Existing bundle directories

An intact Exegate bundle may instead be placed here:

```text
data/bundles/EXE-BUNDLE-V-N-01/
└── exegate_run.json
```

Liber Harvest accepts either the bundle directory or the JSON file directly.

---

## 4. Choose a provider

### OpenAI: no LM Studio required

Use this for automatic harvesting through the hosted OpenAI API.

The default OpenAI model for v0.1.5 is:

```text
gpt-5.6
```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Check readiness:

```bash
liber-harvest doctor \
  --provider openai \
  --source data/parsed/song_001.json
```

Run one harvest:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider openai
```

Explicit profile:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider openai \
  --model gpt-5.6 \
  --openai-reasoning low \
  --max-output-tokens 32768 \
  --timeout 600 \
  --out harvest
```

Liber Harvest sends the frozen Exegate Harvest system instructions automatically. Nothing should be pasted manually into a Playground or chat UI.

**Privacy boundary:** OpenAI provider mode sends the Exegate source to the hosted OpenAI API. The request uses `store: false`, but it is still remote inference. Use LM Studio if the corpus must remain entirely local.

### LM Studio: optional local inference

Use this only when you want local model inference:

```bash
liber-harvest doctor --provider lmstudio
```

Then:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider lmstudio
```

Default LM Studio profile:

```text
endpoint:       http://127.0.0.1:1234
model:          qwen/qwen3.6-35b-a3b
context:        65536
reasoning:      off
temperature:    0.1
output tokens:  32768
timeout:        600 s
```

If LM Studio token authentication is enabled:

```bash
export LIBER_HARVEST_LM_STUDIO_TOKEN="..."
```

### Static: no live model call

Static mode materializes a previously generated extraction response:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --response-file extraction-response.json
```

`--response-file` automatically selects the static provider. Equivalent explicit form:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider static \
  --response-file extraction-response.json
```

Static mode is useful for regression testing, reproducibility, provider comparison, and manual review workflows. It cannot generate a new semantic extraction by itself.

---

## 5. No silent provider default

This command intentionally does **not** pick a backend:

```bash
liber-harvest harvest exegate data/parsed/song_001.json
```

If no provider is configured, Liber Harvest tells you to choose one instead of attempting LM Studio.

You may set a shell default:

```bash
export LIBER_HARVEST_PROVIDER=openai
```

or:

```bash
export LIBER_HARVEST_PROVIDER=lmstudio
```

Then the short command becomes valid:

```bash
liber-harvest harvest exegate data/parsed/song_001.json
```

Other provider-related environment variables:

```bash
export LIBER_HARVEST_MODEL=...
export LIBER_HARVEST_OPENAI_BASE_URL=https://api.openai.com/v1
export LIBER_HARVEST_LM_STUDIO_URL=http://127.0.0.1:1234
```

---

## 6. `doctor`

Provider-neutral check:

```bash
liber-harvest doctor --source data/parsed/song_001.json
```

This checks the runtime directories, output writeability, and source parsing. If no provider is selected it reports that provider-specific checks were skipped.

OpenAI:

```bash
liber-harvest doctor --provider openai --source data/parsed/song_001.json
```

LM Studio:

```bash
liber-harvest doctor --provider lmstudio --source data/parsed/song_001.json
```

Static:

```bash
liber-harvest doctor \
  --provider static \
  --response-file extraction-response.json \
  --source data/parsed/song_001.json
```

---

## 7. Batch harvest with `--all`

`--all` belongs to the nested **`harvest exegate`** command. To see it:

```bash
liber-harvest harvest exegate --help
```

It discovers `song_*.json` directly under the selected source root.

OpenAI batch:

```bash
liber-harvest harvest exegate \
  --all \
  --source-root data/parsed \
  --provider openai \
  --out harvest
```

LM Studio batch:

```bash
liber-harvest harvest exegate \
  --all \
  --source-root data/parsed \
  --provider lmstudio \
  --out harvest
```

Static `--response-file` is intentionally single-source only.

---

## 8. Validate output

Basic record validation:

```bash
liber-harvest validate harvest/library/fragments.jsonl
```

Full provenance validation reopens the original source:

```bash
liber-harvest validate \
  harvest/library/fragments.jsonl \
  --provenance
```

Do this before treating a harvest as accepted output.

---

## 9. Output structure

```text
harvest/
├── exegate/
│   ├── runs/
│   │   └── <run-id>.json
│   └── sources/
│       └── <source-key>/
│           ├── harvest_manifest.json
│           └── fragments.jsonl
└── library/
    ├── fragments.jsonl
    └── relations.jsonl
```

Files are Harvest truth. Databases, vector indexes, search systems and LV-Forge imports are downstream projections.

---

## 10. Common failures

### `No extraction provider selected`

List modes:

```bash
liber-harvest providers
```

Then select `--provider openai`, `--provider lmstudio`, or supply `--response-file`.

### OpenAI key missing

```bash
export OPENAI_API_KEY="..."
liber-harvest doctor --provider openai
```

### LM Studio connection refused

LM Studio is optional. Either start its server and check:

```bash
liber-harvest doctor --provider lmstudio
```

or use OpenAI instead:

```bash
liber-harvest harvest exegate \
  data/parsed/song_001.json \
  --provider openai
```

### Invalid model response

Liber Harvest performs syntax repair and one contract-repair cycle. If the response still violates the frozen contract, the run is rejected rather than writing malformed Lore Fragments.

---

## 11. Frozen design boundary

The following remain authoritative and unchanged by v0.1.5:

- `ARCHITECTURE-FREEZE-v0.1.2.md`
- `FOLDER-STRUCTURE-FREEZE-v0.1.2.md`
- `contracts/exegate-harvest/v0.1.2/`
- `schemas/v0.1.2/`

The OpenAI provider is an implementation file inside the already frozen `providers/` subsystem. It does not alter the semantic contract or deterministic ownership boundary.
