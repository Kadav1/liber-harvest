# Liber Harvest Standalone Architecture Freeze v0.1.2

**Status:** FROZEN  
**Date:** 2026-08-15  
**Product:** Liber Harvest  
**Package:** `liber-harvest` / `liber_harvest`

## Governing boundary

Liber Harvest owns:

- historical source ingestion adapters;
- semantic extraction contracts;
- Lore Fragment draft validation;
- LF-13 provenance materialization;
- deterministic hashes and fragment identity;
- source coverage/discard auditing;
- file-first JSON/JSONL export;
- harvest manifests;
- regression/calibration evidence.

Liber Harvest does **not** own:

- canon decisions;
- current-world adaptation;
- cross-source reconciliation beyond emitted relation hints;
- active authoring/world development;
- vector search;
- RAG;
- SQL databases;
- UI/API application state;
- Obsidian publishing.

## Dependency law

> Liber Harvest MUST NOT import or depend on LV-Forge runtime code.
>
> LV-Forge MAY consume Liber Harvest's versioned file contract.

Legacy LV-Forge formats are understood only through self-contained adapters under `liber_harvest.adapters`.

## Architecture

```text
Historical corpus
      │
      ▼
Source Adapter
      │
      ▼
Harvest Input Envelope
      │
      ▼
Extraction Provider
      │
      ▼
Lore Fragment Drafts
      │
      ▼
Deterministic Validation
      │
      ▼
Provenance Materializer
      │
      ▼
Stable Identity
      │
      ▼
File-first Export
      │
      ├── run JSON
      ├── manifest JSON
      ├── fragments JSONL
      └── relation JSONL
```

## Provider boundary

The deterministic core is provider-independent. Providers implement `ExtractionProvider` and may be LM Studio, an OpenAI-compatible provider added later, or a static calibrated response. Provider output never supplies final IDs, offsets, or hashes.

## Source-adapter boundary

Exegate is the v0.1.2 pilot adapter. Future adapters may target Archivum Secretum, research bundles, old Canon Lore, Obsidian Markdown, or other historical corpora without changing the Lore Fragment destination contract.

## Authority

Files and manifests are authoritative. SQL/vector stores are downstream rebuildable indexes and are prohibited from becoming a required dependency of the Harvester core.

## Compatibility note

The ratified v0.1.2 semantic contract retains historical `LV-FORGE-*` document IDs and `exegate-harvest/0.1.2` schema/version strings. Moving the implementation into Liber Harvest does not alter LF-01 through LF-16 and therefore does not trigger semantic schema version churn.

Future architectural changes require an explicit versioned architecture amendment.
