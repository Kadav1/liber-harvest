# LV-FORGE Lore Harvester v0.1.2 Amendment

**Amendment ID:** `LV-FORGE-AMEND-LORE-HARVEST-001-A02`  
**Version:** `0.1.2`  
**Status:** **FROZEN / RATIFIED**  
**Ratification date:** `2026-08-15`  
**Amends:** `LV-FORGE-SPEC-LORE-FRAGMENT-001 v0.1.1` and `LV-FORGE-CONTRACT-EXEGATE-HARVEST-001 v0.1.1`

## Scope

This narrow calibration amendment addresses six findings only:

1. source modality preservation;
2. evidence-layer provenance;
3. deterministic LF-13 span resolution;
4. obsolete pipeline/tool-wrapper stripping;
5. stricter independent `name` extraction;
6. stricter Seed Line -> `phrase` extraction.

All LF-01 through LF-14 decisions remain authoritative except that deterministic span/hash calculation is assigned to LV-Forge rather than the extraction model.

---

## LF-15 — Source Modality Preservation

Lore Harvest MUST preserve whether historical material presents a concept as:

- `asserted`
- `proposed`
- `hypothetical`
- `interpretive`
- `poetic`
- `ambiguous`

Every Lore Fragment records `claim.modality`.
Every provenance anchor records `source_modality`.

Normalization may weaken certainty when required for fidelity, but MUST NOT strengthen source propositional force. A proposal remains proposed; an interpretation remains interpretive; poetic material does not silently become literal cosmology; ambiguity does not become certainty.

`asserted` means asserted within the historical source's own frame. It does not mean current canon.

---

## LF-16 — Evidence-Layer Provenance

Every provenance anchor MUST identify exactly one semantic evidence layer:

- `source_semantics`
- `exegate_interpretation`
- `lv_application`
- `generated_hook`
- `generated_phrase`
- `metadata`

`circle` and `evidence_layer` are separate dimensions.

This distinction prevents source-song semantics, Exegate interpretation, old LV application, generated hooks, generated phrases, and metadata from becoming indistinguishable after normalization.

Typical mappings:

- Prima Materia source reconstruction -> `source_semantics`
- theological/psychological vectors -> `exegate_interpretation`
- “For the Order…”, “In LV terms…”, symbol `lv_hook` -> `lv_application`
- `scene_hooks` -> `generated_hook`
- `seed_lines` -> `generated_phrase`
- phase/texture/intensity metadata -> `metadata`

---

## LF-13 responsibility refinement

LF-13 remains authoritative.

The extraction model supplies:

- exact `json_pointer`;
- narrowest exact supporting `excerpt`.

LV-Forge deterministically resolves:

- exact occurrence within the JSON-pointer target;
- zero-based, end-exclusive `start` and `end`;
- `source_span.text_sha256`;
- `anchor_sha256`.

The model MUST NOT invent numeric offsets or cryptographic hashes.

If an excerpt has multiple exact matches, the materializer does not guess and flags `provenance_span_ambiguous`.
If an excerpt has no exact match, it flags `provenance_excerpt_unresolved`.

---

## Contract correction C01 — Pipeline wrappers

Obsolete production instructions such as:

- `Lore Architect could...`
- `Codex Mapper might...`
- `Page Drafter can...`
- `The Exegete could...`

are not world lore.

The embedded worldbuilding concept may be harvested. The production wrapper itself is discarded as `pipeline_wrapper`.

---

## Contract correction C02 — `name` restraint

A coined historical Exegate term is not automatically an independent `name` Lore Fragment.

Emit a `name` fragment only when terminology itself has independent linguistic, cultural, historical, social, ritual, legal, geographic, or naming-system value. Otherwise retain the historical term with its underlying concept as title, terminology binding, or provenance.

---

## Contract correction C03 — Seed Line / `phrase` restraint

A Seed Line does not automatically produce a `phrase` Lore Fragment.

First mine or merge the underlying lore. Emit an independent phrase only when the wording itself has reusable in-world function, such as an oath, ritual formula, liturgical response, proverb, maxim, motto, inscription, epitaph, taboo phrase, greeting, curse, blessing, prophetic formula, legal formula, title, or distinctive saying.

---

## Contract correction C04 — Modality-safe normalization

The no-invention rule explicitly includes:

- do not strengthen source modality;
- a possible ritual remains possible;
- a proposed place remains proposed;
- an interpretation remains an interpretation;
- poetic association does not become literal cosmology;
- ambiguity does not become certainty.

---

## Review/discard additions

New review reasons:

- `provenance_span_ambiguous`
- `provenance_excerpt_unresolved`

Existing `provenance_precision_reduced` remains valid.

New discard reason:

- `pipeline_wrapper`

---

## Regression gate

The v0.1.2 amendment was regression-tested against:

- T02 — `tests/fixtures/EXE-BUNDLE-V-N-01/exegate_run.json`
- T03 — `data/parsed/song_001.json`
- T04 — `data/parsed/song_008.json`
- T10 — `data/parsed/song_012.json`

All four tests passed. No new blocking schema defect was found.

---

## Frozen baseline after amendment

`LF-01` through `LF-16` are authoritative.

Future changes require an explicit versioned amendment and appropriate regression tests.
