# Liber Harvest Folder Structure Freeze v0.1.2

**Status:** FROZEN  
**Date:** 2026-08-15

The following is the complete v0.1.2 standalone source/release structure. Transient build outputs, virtual environments, caches, and generated `harvest/` output are explicitly excluded from the frozen repository structure.

```text
liber-harvest/
├── calibration/
│   ├── T01/
│   │   ├── case.json
│   │   └── README.md
│   ├── T02/
│   │   ├── case.json
│   │   └── README.md
│   ├── T03/
│   │   ├── case.json
│   │   └── README.md
│   ├── T04/
│   │   ├── case.json
│   │   └── README.md
│   ├── T05/
│   │   ├── case.json
│   │   └── README.md
│   ├── T06/
│   │   ├── case.json
│   │   └── README.md
│   ├── T07/
│   │   ├── case.json
│   │   └── README.md
│   ├── T08/
│   │   ├── case.json
│   │   └── README.md
│   ├── T09/
│   │   ├── case.json
│   │   └── README.md
│   ├── T10/
│   │   ├── case.json
│   │   └── README.md
│   ├── T11/
│   │   ├── case.json
│   │   └── README.md
│   └── README.md
├── contracts/
│   └── exegate-harvest/
│       └── v0.1.2/
│           ├── LV-FORGE-AMEND-LORE-FRAGMENT-001-A01-v0.1.1.md
│           ├── LV-FORGE-AMEND-LORE-HARVEST-001-A02-v0.1.2.md
│           ├── LV-FORGE-CALIBRATION-CLOSEOUT-v0.1.2.md
│           ├── LV-FORGE-CONTRACT-EXEGATE-HARVEST-001-v0.1.2.md
│           ├── LV-FORGE-SPEC-LORE-FRAGMENT-001-v0.1.2.md
│           ├── RATIFICATION-MANIFEST-v0.1.2.md
│           └── STANDALONE-ADOPTION-NOTE-v0.1.2.md
├── schemas/
│   └── v0.1.2/
│       ├── examples/
│       │   ├── fragments.example.jsonl
│       │   └── relations.example.jsonl
│       ├── exegate-harvest-result.schema.json
│       ├── harvest-manifest.schema.json
│       ├── lore-fragment-draft.schema.json
│       ├── lore-fragment-record.schema.json
│       ├── lore-relation-record.schema.json
│       ├── PROCEDURAL-INVARIANTS.md
│       ├── SCHEMA-CATALOG-v0.1.2.json
│       └── VALIDATION-REPORT.txt
├── src/
│   └── liber_harvest/
│       ├── adapters/
│       │   ├── exegate/
│       │   │   ├── __init__.py
│       │   │   ├── contract.py
│       │   │   ├── loader.py
│       │   │   ├── models.py
│       │   │   └── parser.py
│       │   ├── __init__.py
│       │   └── base.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── lmstudio.py
│       │   └── static.py
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── jsonl.py
│       │   └── manifest.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── constants.py
│       ├── exporter.py
│       ├── identity.py
│       ├── jsonutil.py
│       ├── materializer.py
│       ├── models.py
│       ├── pipeline.py
│       ├── pointers.py
│       ├── provenance.py
│       ├── py.typed
│       └── validation.py
├── tests/
│   ├── fixtures/
│   │   ├── T02/
│   │   │   ├── expectations.json
│   │   │   └── source.json
│   │   ├── T03/
│   │   │   ├── expectations.json
│   │   │   └── source.json
│   │   ├── T04/
│   │   │   ├── expectations.json
│   │   │   └── source.json
│   │   └── T10/
│   │       ├── expectations.json
│   │       └── source.json
│   ├── regression/
│   │   └── test_frozen_regressions.py
│   ├── unit/
│   │   ├── test_exegate_adapter.py
│   │   ├── test_export_and_schemas.py
│   │   ├── test_models_and_materialization.py
│   │   ├── test_pointers_and_provider.py
│   │   └── test_validation.py
│   └── conftest.py
├── .gitignore
├── ARCHITECTURE-FREEZE-v0.1.2.md
├── AUDIT-REPORT-v0.1.2.md
├── FOLDER-STRUCTURE-FREEZE-v0.1.2.md
├── LICENSE
├── pyproject.toml
├── README.md
├── RELEASE-MANIFEST.json
└── SHA256SUMS.txt
```

`pipeline.py`, package entrypoints, and deterministic pointer utilities are explicit frozen additions to the earlier sketch because orchestration must not live inside the CLI.

Top-level subsystem additions require a versioned structure amendment. New implementation files inside an existing subsystem are allowed only when they preserve the frozen ownership boundaries in `ARCHITECTURE-FREEZE-v0.1.2.md`.
