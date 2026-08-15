# Liber Harvest

**Liber Harvest** is the standalone, provenance-preserving historical lore recovery tool for **Liber Vacuitatis**.

Its responsibility is intentionally narrow:

> ingest historical material, recover independently reusable lore, preserve exact provenance and epistemic status, and emit a normalized file-first library without deciding canon.

Liber Harvest **does not depend on LV-Forge**. LV-Forge or any future authoring system may consume the immutable file contract emitted by Liber Harvest.

## Frozen baseline

Version `0.1.2` implements the ratified Lore Fragment / Exegate Harvest contract `LF-01` through `LF-16`. The original v0.1.2 contract identifiers are retained for compatibility even though the implementation is now standalone.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Harvest

```bash
liber-harvest harvest exegate /path/to/exegate_run.json   --model <lm-studio-model>   --out harvest
```

Offline/calibrated result:

```bash
liber-harvest harvest exegate source.json   --response-file result.json   --out harvest
```

## Output

```text
harvest/
├── exegate/
│   ├── runs/
│   └── sources/
└── library/
    ├── fragments.jsonl
    └── relations.jsonl
```

Databases and vector indexes are deliberately out of scope. They are downstream projections, never Harvest truth.

See `ARCHITECTURE-FREEZE-v0.1.2.md` and `FOLDER-STRUCTURE-FREEZE-v0.1.2.md`.
