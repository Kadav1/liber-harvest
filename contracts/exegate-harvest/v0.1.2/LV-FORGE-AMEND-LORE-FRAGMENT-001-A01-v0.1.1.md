# LV-FORGE Lore Fragment v0.1.1 Provenance/Derivation Amendment

**Amendment ID:** `LV-FORGE-AMEND-LORE-FRAGMENT-001-A01`  
**Version:** `0.1.1`  
**Amends:** `LV-FORGE-SPEC-LORE-FRAGMENT-001 v0.1`  
**Also applies to:** `LV-FORGE-CONTRACT-EXEGATE-HARVEST-001 v0.1`  
**Status:** Frozen / Ratified narrow amendment  
**Scope:** Provenance precision and derivation trace only

This amendment adds exactly two requirements:

- `LF-13` — scalar source-span provenance
- `LF-14` — ordered derivation operations

All other requirements `LF-01` through `LF-12` remain unchanged.

---

## 1. Purpose

Calibration against historical Exegate material exposed two cases that v0.1 represented inadequately.

First, exact JSON Pointer provenance is insufficient when one scalar JSON value, such as `/vectors_raw`, contains several paragraphs and many independent ideas.

Second, a Lore Fragment often undergoes more than one derivation operation. A concept extracted from a scene hook might first be decomposed from the larger scene and then generalized away from obsolete characters, terminology, chronology, or institutional bindings.

This amendment resolves those two issues without expanding the purpose or editorial scope of Lore Harvest.

---

# LF-13 — Scalar Source-Span Provenance

## Normative rule

> **LF-13:** When a provenance anchor points to a scalar source value containing more material than the specific evidence supporting the Lore Fragment, the anchor SHOULD include an exact character span within that value. Where reliable span determination is unavailable, the JSON Pointer remains valid but the anchor MUST be flagged for reduced provenance precision.

JSON Pointer remains mandatory.

`source_span` supplements it.

It does not replace it.

---

## 2. Updated provenance structure

### Existing v0.1

```yaml
provenance:
  - pipeline: exegate
    source_path: data/parsed/song_006.json
    source_sha256: "..."
    source_title: Blood-Sweat in the Dust of Judgment
    bundle_id: null
    source_item_id: null
    circle: vectors_of_corruption
    json_pointer: /vectors_raw
    anchor_sha256: "..."
    role: primary
    excerpt: "..."
```

### v0.1.1

```yaml
provenance:
  - pipeline: exegate
    source_path: data/parsed/song_006.json
    source_sha256: "..."
    source_title: Blood-Sweat in the Dust of Judgment
    bundle_id: null
    source_item_id: null
    circle: vectors_of_corruption
    json_pointer: /vectors_raw

    source_span:
      unit: char
      start: 842
      end: 1174
      text_sha256: "..."

    anchor_sha256: "..."
    role: primary
    excerpt: "..."
```

---

## 3. `source_span` schema

```yaml
source_span:
  unit: char
  start: 842
  end: 1174
  text_sha256: "..."
```

### `unit`

v0.1.1 permits only:

```text
char
```

Character offsets are defined against the decoded Unicode string located at `json_pointer`.

Byte offsets are excluded from v0.1.1.

### `start`

Zero-based inclusive character offset.

```text
0 <= start < end
```

### `end`

Zero-based exclusive character offset.

Equivalent Python semantics:

```python
source_value[start:end]
```

### `text_sha256`

SHA-256 of the exact substring:

```python
source_value[start:end]
```

after retrieval from the parsed JSON value.

No whitespace normalization occurs before hashing.

No case conversion occurs.

No Markdown cleanup occurs.

---

## 4. Relationship to `anchor_sha256`

`anchor_sha256` and `source_span.text_sha256` serve different purposes.

### `anchor_sha256`

Hashes the complete value addressed by the JSON Pointer.

Example:

```text
/vectors_raw
```

This detects alteration anywhere within that field.

### `source_span.text_sha256`

Hashes only the exact supporting substring.

This detects alteration of the evidence used for the specific fragment.

Both should be retained.

---

## 5. Provenance precision levels

v0.1.1 adds optional:

```yaml
precision: span
```

Allowed values:

```text
field
span
item
```

### `item`

The JSON Pointer itself resolves to one discrete structured object or atomic field which adequately supports the fragment.

Example:

```text
/scene_hooks/4/hook_text_raw
```

### `span`

A smaller substring inside the pointer target supplies the actual evidence.

Example:

```text
/vectors_raw
characters 842–1174
```

### `field`

Only the larger field could be reliably identified.

This remains valid but is less precise.

---

## 6. When `source_span` is required

`source_span` is required when all three are true:

1. the pointer target is scalar text;
2. that text contains multiple independent semantic units;
3. the fragment relies on only part of that text.

Example:

```text
/vectors_raw
```

typically requires a span.

By contrast:

```text
/scene_hooks/3/hook_text_raw
```

often does not, because that field already represents one relatively discrete source unit.

A span may still be supplied there if only a small portion supports the fragment.

---

## 7. Span failure behaviour

The extractor or materializer must not invent offsets.

If exact offsets cannot be resolved reliably:

```yaml
precision: field
source_span: null

review:
  required: true
  reasons:
    - provenance_precision_reduced
```

This amendment adds:

```text
provenance_precision_reduced
```

to the permitted `review.reasons` vocabulary.

Failure to derive a span is not grounds to discard a fragment.

---

## 8. Multi-span provenance

One concept may be supported by several discontinuous passages inside the same source field.

Do not represent discontinuous evidence as one artificial contiguous span.

Use separate provenance anchors:

```yaml
provenance:
  - json_pointer: /vectors_raw
    source_span:
      unit: char
      start: 842
      end: 1012
      text_sha256: "..."
    role: primary

  - json_pointer: /vectors_raw
    source_span:
      unit: char
      start: 1460
      end: 1644
      text_sha256: "..."
    role: supporting
```

---

# LF-14 — Ordered Derivation Operations

## Normative rule

> **LF-14:** Lore Fragment derivation MUST support an ordered sequence of semantic operations. `primary_mode` records the operation most responsible for the final normalized representation, while `operations` records every substantive transformation applied during extraction.

The original v0.1 single-mode model is superseded.

---

## 9. Previous structure

v0.1:

```yaml
derivation:
  mode: generalized
  fidelity: high
  inference_note: null
```

This cannot accurately represent a fragment that was:

1. decomposed from a scene;
2. generalized away from Alexius;
3. merged with a duplicate formulation elsewhere.

---

## 10. v0.1.1 structure

```yaml
derivation:
  primary_mode: generalized

  operations:
    - decomposed
    - generalized
    - merged_intra_source

  fidelity: high
  inference_note: null
```

---

## 11. Permitted derivation operations

v0.1.1 defines:

```text
direct
decomposed
generalized
implied
merged_intra_source
```

### `direct`

No substantive semantic transformation was required beyond concise normalization.

### `decomposed`

One component was separated from a compound source passage.

### `generalized`

Historical implementation-specific bindings were removed while the underlying concept was preserved.

### `implied`

The concept was strongly encoded but not explicitly presented as a standalone lore statement.

### `merged_intra_source`

Equivalent manifestations of the same concept from multiple locations in the same Exegate source were consolidated into one Lore Fragment.

---

## 12. Ordering semantics

Operations must appear in conceptual execution order.

Example:

```yaml
operations:
  - decomposed
  - generalized
  - merged_intra_source
```

means:

1. the idea was separated from a larger source object;
2. obsolete implementation bindings were removed;
3. equivalent support elsewhere in the same source was consolidated.

Order must not be alphabetized.

---

## 13. `primary_mode`

Allowed values are the same as the operation vocabulary except that `merged_intra_source` should not normally be the primary mode.

Recommended precedence:

```text
generalized
implied
decomposed
direct
```

The primary mode answers:

> What operation most materially distinguishes the normalized Lore Fragment from its source expression?

Example:

A scene hook proposes an Alexius-specific named rite.

The extractor:

1. decomposes the ritual from the scene;
2. removes Alexius and old Abbey placement.

Correct:

```yaml
primary_mode: generalized
operations:
  - decomposed
  - generalized
```

---

## 14. `direct` exclusivity

If `direct` is the only operation:

```yaml
primary_mode: direct
operations:
  - direct
```

If a substantive additional operation occurs, `direct` should normally be omitted.

Invalid:

```yaml
operations:
  - direct
  - generalized
```

The fragment is no longer direct if it required generalization.

---

## 15. `implied` combinations

`implied` may combine with generalization.

Example:

```yaml
primary_mode: implied
operations:
  - implied
  - generalized
```

If inference changes the fragment significantly, `fidelity` should generally be `medium` rather than `high`.

---

## 16. Fidelity remains unchanged

Allowed:

```text
high
medium
low
```

Fidelity measures faithfulness to historical source material, not usefulness, quality, current-canon compatibility, or desirability.

`LF-14` does not modify this principle.

---

## 17. `inference_note`

Still mandatory when:

```text
fidelity: low
```

It is also recommended whenever `implied` appears in `operations`.

Example:

```yaml
derivation:
  primary_mode: implied
  operations:
    - implied
    - generalized
  fidelity: medium
  inference_note: >
    The source presents crop failure through a chronicler's explanation
    rather than as an independently established property of the soil.
```

---

## 18. Updated fragment example

```yaml
schema_version: lore-fragment/0.1.1

fragment_id: LFR-RIT-92AC731F04DD
concept_key: barefoot_processional_way_of_dust

type: ritual
title: Barefoot Processional Way of Dust

content:
  source_meaning: >
    Members of the historical Order descend barefoot through dust
    while chanting on their way to the old Sunken Tomb.

  normalized_lore: >
    A ritual procession requires participants to walk barefoot through
    dust along a designated descending path while repetitive chanting
    accompanies the movement.

  details:
    - Bare feet create deliberate contact with dust and ground.
    - Downward movement forms part of the rite.
    - Chant and physical procession operate as one ceremonial sequence.

domains:
  - ritual
  - religion
  - infrastructure

tags:
  - barefoot
  - procession
  - dust
  - descent
  - chant

legacy_bindings:
  - kind: character
    value: Alexius
    handling: removed_from_normalized
    note: The procession does not depend upon the historical protagonist.

  - kind: location
    value: Sunken Tomb
    handling: generalized
    note: The reusable concept requires a ritual destination, not this specific old location.

  - kind: terminology
    value: Via Pulveris Mortis
    handling: removed_from_normalized
    note: Historical proposed name remains preserved through provenance.

derivation:
  primary_mode: generalized
  operations:
    - decomposed
    - generalized
  fidelity: high
  inference_note: null

provenance:
  - pipeline: exegate
    source_path: data/parsed/song_006.json
    source_sha256: "..."
    source_title: Blood-Sweat in the Dust of Judgment
    bundle_id: null
    source_item_id: null
    circle: narrative_potential
    json_pointer: /scene_hooks/1/hook_text_raw
    precision: item
    source_span: null
    anchor_sha256: "..."
    role: primary
    excerpt: "..."

relation_hints: []

review:
  required: false
  reasons: []

harvest:
  contract_version: exegate-harvest/0.1.1
  extractor_version: "0.1.1"
  run_id: "..."
```

---

## 19. Updated raw-field example

```yaml
provenance:
  - pipeline: exegate
    source_path: data/parsed/song_006.json
    source_sha256: "..."
    source_title: Blood-Sweat in the Dust of Judgment
    circle: vectors_of_corruption
    json_pointer: /vectors_raw

    precision: span

    source_span:
      unit: char
      start: 842
      end: 1174
      text_sha256: "..."

    anchor_sha256: "..."
    role: primary
    excerpt: "..."
```

---

## 20. Harvest Result compatibility

Harvest Result changes only in version labeling:

```yaml
contract_version: exegate-harvest/0.1.1
```

Fragments use:

```yaml
schema_version: lore-fragment/0.1.1
```

Coverage, discarded records, warnings, taxonomy, legacy bindings, and no-invention requirements remain unchanged.

---

## 21. Backward compatibility

Existing v0.1 fragment drafts remain interpretable.

Migration is deterministic.

### Old

```yaml
derivation:
  mode: generalized
  fidelity: high
```

### Migrated

```yaml
derivation:
  primary_mode: generalized
  operations:
    - generalized
  fidelity: high
```

Existing provenance lacking `source_span` remains valid:

```yaml
precision: field
source_span: null
```

unless the source pointer itself identifies an atomic item, in which case migration tooling may assign:

```yaml
precision: item
```

without semantic reinterpretation.

---

## 22. Validation additions

```text
LF13-V1
source_span.start >= 0

LF13-V2
source_span.end > source_span.start

LF13-V3
source_span.unit == "char"

LF13-V4
text_sha256 == SHA256(pointer_value[start:end])

LF13-V5
precision == "span" requires source_span

LF13-V6
source_span requires a scalar textual pointer target

LF14-V1
operations contains at least one operation

LF14-V2
primary_mode appears in operations

LF14-V3
operations contains no duplicates

LF14-V4
direct must be the sole operation if present

LF14-V5
merged_intra_source requires two or more provenance anchors

LF14-V6
low fidelity requires inference_note

LF14-V7
operations preserve declared order during serialization
```

---

## 23. Contract insertion

Add the following normative section to the Exegate extraction contract:

```text
PROVENANCE SPANS

A JSON Pointer identifies the source field or structured item.

When the pointer resolves to a long scalar text containing multiple
independent semantic units, identify the exact supporting character
span whenever reliable offsets are available.

Use zero-based, end-exclusive character offsets.

Never guess character offsets.

If exact offsets cannot be established, preserve field-level provenance
and flag provenance_precision_reduced for later review.

DERIVATION OPERATIONS

Do not collapse derivation into one mode.

Record every substantive extraction operation in execution order.

Allowed operations:

direct
decomposed
generalized
implied
merged_intra_source

Also assign primary_mode to the operation most responsible for the final
normalized representation.

If direct is used, it must be the sole operation.

If equivalent evidence from multiple locations in the same source is
consolidated into one fragment, include merged_intra_source and preserve
all supporting provenance anchors.
```

---

## 24. Explicit non-changes

This amendment does **not** alter:

- the definition of Lore Fragment
- Exegate as the pilot corpus
- source precedence rules
- destination taxonomy
- domain vocabulary
- tags
- legacy-binding handling
- no-invention rule
- current-canon neutrality
- source/normalized dual representation
- intra-source deduplication policy
- cross-source deduplication boundary
- coverage audit requirements
- discard rules
- deterministic fragment identity principle
- JSONL storage recommendation

No `LF-01` through `LF-12` language is superseded except where the original single `derivation.mode` representation is structurally replaced by `primary_mode + operations`.

---

## 25. Ratified amendment clauses

**LF-13:** For scalar source fields containing multiple semantic units, provenance supports exact zero-based, end-exclusive character spans within the JSON-pointer target, together with a hash of the exact supporting substring. Exact spans must never be guessed.

**LF-14:** Derivation records an ordered sequence of substantive extraction operations, with a separate `primary_mode` identifying the operation most responsible for the final normalized representation. Supported operations are `direct`, `decomposed`, `generalized`, `implied`, and `merged_intra_source`.

These two clauses constitute the complete scope of v0.1.1.
