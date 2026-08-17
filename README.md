# Liber Harvest

**Liber Harvest** is the standalone, provenance-preserving historical lore recovery tool for **Liber Vacuitatis**.

Its job is deliberately narrow:

> ingest historical material, recover independently reusable lore, preserve exact provenance and epistemic status, and emit a normalized file-first library without deciding canon.

Liber Harvest does **not** depend on LV-Forge. LV-Forge, Obsidian tooling, or any future authoring system may consume the immutable file contract emitted by Liber Harvest.

## Current release

- Application version: **0.1.4**
- Frozen semantic contract: **`exegate-harvest/0.1.2`**
- Lore Fragment schema: **`lore-fragment/0.1.2`**
- Frozen clauses: **LF-01 through LF-16**

Version 0.1.4 is an **operator/usability release**. It does not revise the frozen v0.1.2 Lore Fragment or Exegate Harvest semantics.

---

# 1. What runs where

```text
Historical Exegate JSON
        │
        ▼
Liber Harvest source adapter
        │
        ▼
LM Studio local model
  semantic extraction only
        │
        ▼
Lore Fragment drafts
        │
        ▼
Liber Harvest deterministic core
  validation
  exact provenance resolution
  source spans + SHA-256
  deterministic LFR IDs
  JSONL + manifests
        │
        ▼
harvest/
```

The language model is an **untrusted semantic extractor**. It never creates final fragment IDs, provenance hashes, or source spans. Liber Harvest materializes those deterministically after validating the model response.

---

# 2. Install locally

Liber Harvest requires **Python 3.12+**.

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

For development/testing:

```bash
pip install -e ".[dev]"
pytest -q
```

Both commands are installed:

```text
liber-harvest
lh
```

---

# 3. Initialize the local runtime workspace

Run once from the repository root:

```bash
liber-harvest init
```

This creates:

```text
liber-harvest/
├── data/                       # local historical inputs; gitignored
│   ├── parsed/
│   │   └── song_*.json
│   └── bundles/
│       └── <bundle-id>/
│           └── exegate_run.json
│
├── harvest/                    # generated output; gitignored
│
└── [application source]
```

`data/` and `harvest/` are runtime directories, not application source.

## Where to put Exegate JSON files

### Parsed historical corpus

Put canonical `ExegateRun` JSON files here:

```text
data/parsed/song_001.json
data/parsed/song_002.json
data/parsed/song_003.json
...
```

The batch command `--all` currently discovers `song_*.json` files in `data/parsed/`.

### Existing Exegate bundle

You may keep a bundle intact:

```text
data/bundles/EXE-BUNDLE-V-N-01/
└── exegate_run.json
```

Liber Harvest accepts either the directory:

```bash
liber-harvest harvest exegate data/bundles/EXE-BUNDLE-V-N-01
```

or the JSON directly:

```bash
liber-harvest harvest exegate data/bundles/EXE-BUNDLE-V-N-01/exegate_run.json
```

Keeping inputs below the project root also gives stable provenance paths such as `data/parsed/song_006.json` instead of machine-specific absolute paths.

---

# 4. LM Studio setup

Liber Harvest uses LM Studio's **native v1 REST API** and sends requests to:

```text
POST http://127.0.0.1:1234/api/v1/chat
```

The Harvest system instructions are embedded in Liber Harvest and sent through the API automatically.

**Do not paste a second Liber Harvest system prompt into the LM Studio UI.** Leave any manually configured system prompt blank/default for this workflow.

## 4.1 Recommended model profile

The v0.1.4 operational default is:

```text
qwen/qwen3.6-35b-a3b
```

Recommended Harvest profile:

```text
reasoning:          off
context length:     65,536
Harvest temperature: 0.1
max output tokens:  32,768
request timeout:    600 seconds
```

This model choice is an **operational default, not part of the frozen lore contract**. It may be changed after comparative calibration without changing LF-01 through LF-16.

The 35B-A3B model requires a comparatively capable machine. For lower-memory testing, use a smaller current Qwen model such as `qwen/qwen3.5-9b`, but treat smaller-model runs as exploratory until they have passed the Harvest calibration suite.

## 4.2 Download the model

In LM Studio's UI, search for the model above and download an appropriate quantization for your hardware.

Or with the LM Studio CLI:

```bash
lms get qwen/qwen3.6-35b-a3b
```

List downloaded models:

```bash
lms ls --llm
```

Estimate memory before loading:

```bash
lms load --estimate-only qwen/qwen3.6-35b-a3b --context-length 65536
```

## 4.3 Start the local server

```bash
lms server start --port 1234 --bind 127.0.0.1
```

Check it:

```bash
lms server status
```

For this workflow, keep the server on `127.0.0.1`. CORS is not required.

## 4.4 Load the model

```bash
lms load qwen/qwen3.6-35b-a3b \
  --context-length 65536 \
  --gpu max
```

If `--gpu max` is unsuitable for your hardware, omit it and let LM Studio choose automatically, or use a lower offload setting.

Check loaded models:

```bash
lms ps
```

## 4.5 Authentication

For a localhost-only server, authentication is optional.

If you enable LM Studio API-token authentication, set the token for Liber Harvest without placing it on the command line:

```bash
export LIBER_HARVEST_LM_STUDIO_TOKEN='your-token'
```

Liber Harvest sends it as a Bearer token.

---

# 5. Check the complete setup before harvesting

Run:

```bash
liber-harvest doctor
```

It checks:

- runtime input directories
- output write access
- LM Studio connectivity
- default/requested model visibility
- whether the model is loaded
- requested context length
- requested reasoning mode

To include a real source parse check:

```bash
liber-harvest doctor --source data/parsed/song_006.json
```

The built-in defaults are:

```text
LM Studio:     http://127.0.0.1:1234
model:         qwen/qwen3.6-35b-a3b
context:       65536
reasoning:     off
```

---

# 6. Run the first real harvest

Start with one source, not the whole corpus:

```bash
liber-harvest harvest exegate data/parsed/song_006.json
```

That is equivalent to the explicit command:

```bash
liber-harvest harvest exegate data/parsed/song_006.json \
  --model qwen/qwen3.6-35b-a3b \
  --lm-studio-url http://127.0.0.1:1234 \
  --context-length 65536 \
  --reasoning off \
  --temperature 0.1 \
  --max-output-tokens 32768 \
  --timeout 600 \
  --out harvest
```

The provider injects the frozen Exegate Harvest system contract automatically.

---

# 7. Environment variables

Optional shell defaults:

```bash
export LIBER_HARVEST_LM_STUDIO_URL=http://127.0.0.1:1234
export LIBER_HARVEST_MODEL=qwen/qwen3.6-35b-a3b
```

If LM Studio authentication is enabled:

```bash
export LIBER_HARVEST_LM_STUDIO_TOKEN='...'
```

Command-line `--model` and `--lm-studio-url` override the corresponding defaults.

---

# 8. Validate the result

Basic materialized-record validation:

```bash
liber-harvest validate harvest/library/fragments.jsonl
```

Full provenance validation reopens the historical source and verifies that the stored evidence still resolves correctly:

```bash
liber-harvest validate harvest/library/fragments.jsonl --provenance
```

Do this before treating a harvest run as accepted output.

---

# 9. Batch harvest

After several single-source runs are satisfactory:

```bash
liber-harvest harvest exegate \
  --all \
  --source-root data/parsed \
  --out harvest
```

Current `--all` behavior is intentionally simple: it discovers `song_*.json` files directly under the selected source root. Bundle-directory recursion is not part of v0.1.4.

---

# 10. Output structure

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

The database/vector layer is deliberately downstream. JSON/JSONL and manifests are Harvest truth.

---

# 11. Offline/static-provider mode

You can materialize a previously generated extraction response without contacting LM Studio:

```bash
liber-harvest harvest exegate data/parsed/song_006.json \
  --response-file extraction-response.json \
  --out harvest
```

This is useful for regression testing, reproducibility, and comparing model outputs.

---

# 12. Troubleshooting

## `LM Studio check failed`

Check:

```bash
lms server status
curl http://127.0.0.1:1234/api/v1/models
```

Then run:

```bash
liber-harvest doctor
```

## `model not installed/visible`

```bash
lms get qwen/qwen3.6-35b-a3b
lms ls --llm
```

Or override the model:

```bash
liber-harvest doctor --model <your-model-key>
```

## Model is installed but not loaded

```bash
lms load qwen/qwen3.6-35b-a3b --context-length 65536
```

LM Studio may also auto-load an installed model on first API use, but explicit loading makes memory/context configuration easier to audit.

## Out of memory

Try, in order:

1. reduce `--context-length` to `32768`;
2. use a more compressed quantization;
3. reduce GPU offload;
4. use a smaller model for exploratory runs.

Keep the Liber Harvest `--context-length` at or below the context with which the model is loaded.

## Model emits invalid JSON

Liber Harvest automatically performs one syntax-repair attempt and contract repair. If the result still fails, the run is rejected rather than silently writing malformed fragments.

## Debug the exact prompt sent to LM Studio

LM Studio can stream inference logs:

```bash
lms log stream
```

Remember that the Harvest system instructions come from:

```text
src/liber_harvest/adapters/exegate/contract.py
```

Do not maintain a second manual copy inside LM Studio.

---

# 13. Frozen design documents

The standalone architecture and source-tree baseline remain governed by:

- `ARCHITECTURE-FREEZE-v0.1.2.md`
- `FOLDER-STRUCTURE-FREEZE-v0.1.2.md`
- `contracts/exegate-harvest/v0.1.2/`
- `schemas/v0.1.2/`

Application v0.1.4 improves operation and provider control while preserving that frozen semantic and architectural boundary.
