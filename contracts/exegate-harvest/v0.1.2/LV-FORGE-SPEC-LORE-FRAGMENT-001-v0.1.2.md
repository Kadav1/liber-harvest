# LV-FORGE Lore Fragment v0.1.2

**Specification ID:** `LV-FORGE-SPEC-LORE-FRAGMENT-001`  
**Version:** `0.1.2`  
**Companion contract:** `LV-FORGE-CONTRACT-EXEGATE-HARVEST-001 v0.1.2`  
**Amendments:** `LV-FORGE-AMEND-LORE-FRAGMENT-001-A01 v0.1.1`; `LV-FORGE-AMEND-LORE-HARVEST-001-A02 v0.1.2`  
**Purpose:** Loss-minimized extraction of reusable Liber Vacuitatis lore from historical source material.  
**Pilot corpus:** Infernal Exegate outputs.  
**Status:** **Frozen / Ratified baseline.**
**Ratification date:** `2026-08-15`

> **Preserve what the old source meant, extract what remains reusable, remove obsolete implementation dependencies from the normalized layer, preserve source modality and evidence layer, and invent nothing to replace removed material.**

This system performs **salvage**, not canonization.

---

## 1. Fundamental object

A **Lore Fragment** is:

> One independently reusable concept, entity, practice, belief, condition, event, expression, environment, or narrative mechanism recovered from historical Liber Vacuitatis material.

A fragment does not imply:

- canon
- approval
- current validity
- current chronology
- current terminology
- current character assignment
- current religious framework

It records recoverable creative material.

---

## 2. Granularity rule

> **One independently reusable idea per fragment.**

Example source concept:

> A hidden garden grows poisonous herbs in ritual arrangements, and its keeper records preparations in cipher.

This should normally become at least three fragments:

1. hidden cultivation of poisonous plants
2. ritual geometry applied to cultivation
3. encoded records protecting restricted medicinal knowledge

If separating two details destroys the concept's meaning, they remain together.

The extractor must not create microscopic fragments from adjectives, incidental scenery, or generic actions.

---

## 3. Materialized Lore Fragment

```yaml
schema_version: "lore-fragment/0.1.2"

fragment_id: "LFR-CUS-7A41C0B920ED"
concept_key: "winter_snow_as_funerary_memory"

type: "custom"

title: "Snow as Funerary Memory"

claim:
  modality: proposed

content:
  source_meaning: >
    The historical source proposes a burial place where snow covers
    the dead and takes on a commemorative function.

  normalized_lore: >
    One proposed funerary custom allows winter snow to become part of
    remembrance, with accumulation over graves understood as a form
    of natural memorialization.

  details:
    - "Snowfall participates in remembrance rather than functioning only as weather."
    - "Visible grave markers may become secondary to seasonal covering."
    - "Repeated snowfall may be associated with names, memory, or continued presence."

domains:
  - "death"
  - "burial"
  - "environment"

tags:
  - "snow"
  - "winter"
  - "grave"
  - "memory"
  - "funerary_practice"

legacy_bindings:
  - kind: "location"
    value: "old Abbey burial-field placement"
    handling: "generalized"
    note: "The burial concept is portable beyond the historical Abbey implementation."

derivation:
  primary_mode: "generalized"
  operations:
    - "decomposed"
    - "generalized"
  fidelity: "high"
  inference_note: null

provenance:
  - pipeline: "exegate"
    source_path: "data/parsed/song_001.json"
    source_sha256: "..."
    source_title: "..."
    bundle_id: null
    source_item_id: null
    circle: "narrative_potential"
    evidence_layer: "generated_hook"
    source_modality: "proposed"
    json_pointer: "/scene_hooks/4/hook_text_raw"
    precision: "item"
    source_span: null
    anchor_sha256: "..."
    role: "primary"
    excerpt: "..."

relation_hints: []

review:
  required: false
  reasons: []

harvest:
  contract_version: "exegate-harvest/0.1.2"
  extractor_version: "0.1.2"
  run_id: "..."
```

---

## 4. Required fields

### 4.1 `schema_version`

Fixed:

```text
lore-fragment/0.1.2
```

### 4.2 `fragment_id`

Assigned by LV-Forge after extraction.

The language model **must not invent fragment IDs**.

Recommended form:

```text
LFR-{TYPECODE}-{12_HEX}
```

Examples:

```text
LFR-RIT-92AC731F04DD
LFR-DOC-B612007B8C1A
LFR-PLC-784DEF229191
```

### 4.3 `concept_key`

Required before ID generation.

Rules:

- `lower_snake_case`
- 3 to 10 meaningful tokens
- describes the concept, not the prose
- avoids obsolete character names unless essential to the concept

Good:

```text
ritualized_surrender_of_personal_names
```

Poor:

```text
alexius_scene_number_four
```

---

## 5. Deterministic ID generation

The application, not the extractor, generates the ID.

Recommended identity material:

```text
schema_version
+
source identity
+
sorted provenance JSON pointers
+
concept_key
+
type
```

Then:

```python
digest = sha256(identity_material).hexdigest()[:12].upper()
fragment_id = f"LFR-{type_code}-{digest}"
```

This gives reproducibility across identical harvest runs.

Changing the actual extracted concept or its evidentiary basis intentionally produces a new identity.

---

## 6. Controlled Lore Fragment types

| Type | Code |
|---|---:|
| person | PER |
| group | GRP |
| institution | INS |
| office | OFF |
| place | PLC |
| structure | STR |
| architecture | ARC |
| object | OBJ |
| relic | REL |
| material | MAT |
| flora | FLO |
| creature | CRE |
| ritual | RIT |
| custom | CUS |
| practice | PRA |
| law | LAW |
| social_structure | SOC |
| economy | ECO |
| trade | TRD |
| warfare | WAR |
| doctrine | DOC |
| belief | BEL |
| cosmology | COS |
| myth | MYT |
| legend | LEG |
| symbol | SYM |
| event | EVT |
| historical_claim | HIS |
| somatic | SOM |
| pathology | PAT |
| medicine | MED |
| environment | ENV |
| language | LAN |
| name | NAM |
| phrase | PHR |
| motif | MOT |
| sensory_palette | SEN |
| narrative_hook | NAR |
| character_hook | CHR |
| other | OTH |

This is the **destination taxonomy**.

It has no obligation to match Exegate's existing item types.

---

## 7. `content`

### 7.1 `source_meaning`

Faithful, concise reconstruction of what the old source proposed.

It may contain:

- Alexius
- old Order terminology
- old Abbey assumptions
- Christianity
- obsolete dates
- superseded cosmology
- old character assignments

because this field records historical meaning.

It should not quote large sections unnecessarily.

### 7.2 `normalized_lore`

Portable version of the same underlying idea.

This field should:

- stand alone
- make sense without the old source
- remove implementation-specific dependencies where practical
- preserve the creative substance
- avoid replacing old structures with newly invented current ones

Example:

**Source meaning**

> A Holy Week rite uses three wounds from Alexius during preparation for the Tomb.

**Normalized lore**

> A secret rite draws blood from three separate wounds, treating each sample as one stage of a transformative religious procedure.

It must **not** become:

> The Covenant of the Living Flame performs this rite during the Feast of Ashen Dawn.

That would be new worldbuilding.

### 7.3 `details`

Optional array containing important subordinate facts which belong to the same concept.

Details must not hide concepts deserving their own fragment.

---


## 7A. Claim modality — LF-15

Every fragment records:

```yaml
claim:
  modality: proposed
```

Controlled values:

- `asserted`
- `proposed`
- `hypothetical`
- `interpretive`
- `poetic`
- `ambiguous`

`asserted` means asserted by the historical source within its own frame, not current canon.

Normalization MUST NOT strengthen modality. Proposed, hypothetical, interpretive, poetic, and ambiguous source material must remain visibly non-assertive in `normalized_lore`.

Every provenance anchor also records `source_modality`, because one fragment may be supported by anchors with different propositional force.

---

## 7B. Evidence layer — LF-16

Every provenance anchor records one `evidence_layer`:

- `source_semantics`
- `exegate_interpretation`
- `lv_application`
- `generated_hook`
- `generated_phrase`
- `metadata`

`circle` and `evidence_layer` are independent. For example, different fields inside one Symbol may map to source semantics, Exegate interpretation, or old LV application.

Generated hooks remain identifiable as generated proposals even when their old prose is declarative. Generated phrases remain identifiable as downstream creative wording rather than source assertion.

---

## 8. `domains`

Domains are contextual facets rather than ontology.

Recommended vocabulary:

```text
religion
cosmology
ritual
institution
politics
law
society
family
economy
trade
warfare
architecture
material_culture
environment
agriculture
food
medicine
body
death
burial
history
myth
folklore
language
naming
magic
travel
infrastructure
art
music
literature
psychology
```

Multiple domains are expected.

---

## 9. Tags

Tags are lightweight retrieval terms.

They must use `lower_snake_case`.

Good:

```text
blood_offering
winter
burial_field
ritual_obedience
poisonous_plants
```

Poor:

```text
cool
interesting
dark
lore
story
```

Generic mood tags should be avoided unless meaningful.

---

## 10. Legacy bindings

```yaml
legacy_bindings:
  - kind: "character"
    value: "Alexius"
    handling: "generalized"
    note: "Concept works independently of the historical protagonist."
```

Allowed `kind`:

```text
character
institution
religion
cosmology
location
timeline
plot
terminology
role
structure
other
```

Allowed `handling`:

```text
retained
generalized
removed_from_normalized
essential
```

### Meanings

**retained**  
The old element itself is valuable lore.

**generalized**  
The underlying idea survives without its old implementation.

**removed_from_normalized**  
The detail added no portable lore, but provenance records its historical presence.

**essential**  
Removing the old binding destroys the concept.

An old fictional term, doctrine, or object should often remain intact and be marked `essential` or `retained`.

---

## 11. Derivation

v0.1.2 uses ordered derivation operations.

```yaml
derivation:
  primary_mode: "generalized"
  operations:
    - "decomposed"
    - "generalized"
    - "merged_intra_source"
  fidelity: "high"
  inference_note: null
```

Allowed operations:

```text
direct
decomposed
generalized
implied
merged_intra_source
```

### `direct`

No substantive semantic transformation beyond concise normalization.

### `decomposed`

One component was separated from a compound source passage.

### `generalized`

Historical implementation-specific bindings were removed while preserving the underlying concept.

### `implied`

The concept was strongly encoded but not explicitly presented as a standalone lore statement.

### `merged_intra_source`

Equivalent manifestations of the same concept from multiple locations in the same Exegate source were consolidated into one Lore Fragment.

Operations must appear in conceptual execution order.

`primary_mode` records the operation most responsible for the final normalized representation.

Recommended precedence:

```text
generalized
implied
decomposed
direct
```

`merged_intra_source` should not normally be the primary mode.

If `direct` is used, it must be the sole operation.

---

## 12. Fidelity

Allowed values:

```text
high
medium
low
```

This measures **faithfulness to the historical source**, not quality.

It does not measure whether the idea is useful or desirable.

For `low`, `inference_note` is mandatory.

It is also recommended whenever `implied` appears in `operations`.

---

## 13. Provenance

A fragment must always have at least one provenance anchor.

```yaml
provenance:
  - pipeline: "exegate"
    source_path: "data/parsed/song_006.json"
    source_sha256: "..."
    source_title: "Blood-Sweat in the Dust of Judgment"
    bundle_id: null
    source_item_id: null
    circle: "narrative_potential"
    evidence_layer: "generated_hook"
    source_modality: "proposed"
    json_pointer: "/scene_hooks/2/hook_text_raw"
    precision: "item"
    source_span: null
    anchor_sha256: "..."
    role: "primary"
    excerpt: "..."
```

Allowed `role`:

```text
primary
supporting
duplicate
```

Repeated evidence inside the same Exegate source should strengthen one fragment, not create duplicate fragments.

---

## 14. JSON Pointer

Every provenance anchor requires a JSON Pointer.

Prefer the narrowest source location which supports the concept.

Prefer:

```text
/scene_hooks/3/hook_text_raw
```

over:

```text
/scene_hooks
```

Prefer:

```text
/symbols/1/occult
```

over:

```text
/symbols/1
```

when the narrower field alone supports the concept.

---

## 15. Scalar source-span provenance

### LF-13

> **For scalar source fields containing multiple semantic units, provenance supports exact zero-based, end-exclusive character spans within the JSON-pointer target, together with a hash of the exact supporting substring. Exact spans must never be guessed.**

`source_span` supplements JSON Pointer. It does not replace it.

```yaml
source_span:
  unit: "char"
  start: 842
  end: 1174
  text_sha256: "..."
```

Rules:

- `unit` is `char`
- `start` is zero-based and inclusive
- `end` is zero-based and exclusive
- substring semantics are equivalent to `source_value[start:end]`
- no whitespace normalization before hashing
- no case conversion
- no Markdown cleanup

`anchor_sha256` hashes the complete JSON Pointer target.

`source_span.text_sha256` hashes only the exact evidence substring.

### Provenance precision

Optional `precision` values:

```text
item
span
field
```

**item**: the pointer itself resolves to an adequately discrete source object or atomic field.

**span**: only part of the pointer target supports the fragment.

**field**: only the larger field could be reliably identified.

### Span requirement

`source_span` is required when:

1. the pointer target is scalar text;
2. the text contains multiple independent semantic units;
3. the fragment relies on only part of that text.

### Span materialization and failure

The extraction model never invents offsets or cryptographic hashes. For a long scalar field it returns the narrowest exact supporting `excerpt`.

LV-Forge deterministically resolves that excerpt against the value identified by `json_pointer`:

```text
JSON Pointer target
→ exact excerpt search
→ zero-based start/end
→ source_span.text_sha256
→ anchor_sha256
```

If exactly one occurrence matches, materialize `precision: "span"`.

If multiple exact occurrences match, do not guess:

```yaml
precision: "field"
source_span: null

review:
  required: true
  reasons:
    - "provenance_span_ambiguous"
```

If no exact occurrence matches, do not guess:

```yaml
precision: "field"
source_span: null

review:
  required: true
  reasons:
    - "provenance_excerpt_unresolved"
```

`provenance_precision_reduced` remains available for other cases where provenance can only be represented at field precision.

### Multi-span evidence

Discontinuous evidence must use separate provenance anchors rather than one artificial contiguous span.

---

## 16. Relationship hints

Relationships are optional in v0.1.2.

```yaml
relation_hints:
  - relation: "component_of"
    target_concept_key: "three_stage_blood_initiation"
```

Suggested relations:

```text
related_to
component_of
variant_of
contradicts
requires
produces
performed_at
located_in
associated_with
derived_from
```

These remain hints until library-level reconciliation occurs.

---

## 17. Review flags

This is extraction quality control, not approval.

```yaml
review:
  required: true
  reasons:
    - "source_ambiguity"
```

Allowed reasons:

```text
source_ambiguity
heavy_generalization
possible_over_split
possible_under_split
possible_duplicate
mixed_concepts
uncertain_type
broken_source_structure
legacy_dependency_heavy
provenance_precision_reduced
provenance_span_ambiguous
provenance_excerpt_unresolved
other
```

---

## 18. Harvest Result schema

The model returns a coverage-aware result rather than a naked fragment array.

```yaml
contract_version: "exegate-harvest/0.1.2"

source:
  pipeline: "exegate"
  source_path: "data/parsed/song_006.json"
  source_sha256: "..."
  source_title: "..."
  bundle_id: null

fragments:
  - ...

coverage:
  - json_pointer: "/prima_materia_raw"
    disposition: "extracted"
    evidence_layer: "source_semantics"
    source_modality: "asserted"
    concept_keys:
      - "blood_sweat_as_ritual_material"
      - "descent_into_dust_as_religious_transition"

  - json_pointer: "/rituals"
    disposition: "empty"
    evidence_layer: null
    source_modality: null
    concept_keys: []

  - json_pointer: "/metadata_raw"
    disposition: "metadata_only"
    evidence_layer: "metadata"
    source_modality: null
    concept_keys: []

discarded:
  - json_pointer: "/analysis_mode"
    reason: "non_lore_metadata"
    note: "Preserved in source manifest."

warnings: []
```

---

## 19. Coverage dispositions

Allowed:

```text
extracted
merged
metadata_only
empty
non_lore
unparseable
```

Every non-empty primary Exegate section must receive a coverage entry.

---

## 20. Discard reasons

Material may only be discarded for narrow reasons:

```text
duplicate_within_source
non_lore_metadata
identifier_only
formatting_only
empty
parser_artifact
pipeline_wrapper
```

The following are not valid discard reasons:

- outdated
- conflicts with current canon
- belongs to abandoned storyline
- strange
- excessive

---

## 21. Exegate field rules

### Prima Materia

Extract:

- events
- transformations
- environmental conditions
- objects
- bodily processes
- social situations
- customs
- implied history
- physical relationships
- recurring narrative mechanisms

Do not preserve the entire summary as one fragment unless it genuinely expresses one indivisible concept.

### Vectors

Extract separately:

- doctrine
- cosmology
- theological inversion
- political/institutional logic
- obedience structures
- social power relationships
- existential propositions
- ritual principles
- narrative structural principles

Structured vectors and `vectors_raw` must both be considered.

Repeated material should merge within the same source.

### Symbols

Treat independently:

```text
literal
occult
psychological
lv_hook
```

One old Symbol may yield multiple Lore Fragments.

### Psychological Pathology

Harvest:

- behavioural patterns
- forms of conditioning
- institutional manipulation
- fear responses
- compulsive behaviours
- altered perception
- religious psychology
- social manifestations
- bodily expressions of mental states

Avoid modern clinical diagnosis unless the source itself depends on one.

### Circle V / Ritual Extraction

Respect the Exegate `type` field.

Possible source types include:

```text
ritual
pathology
relic
doctrine
architecture
somatic
```

Never blindly map every Circle V item to `ritual`.

### Atmospherics

Atmospherics may yield both:

1. coherent `sensory_palette` fragments
2. concrete environmental, architectural, material, climatic, acoustic, lighting, or spatial facts

Both may be retained.

### Narrative Potential

Preserve the overall scene as `narrative_hook` only when useful.

Also decompose every embedded:

- building
- ritual
- object
- office
- custom
- institution
- historical idea
- social mechanism
- environment
- belief

into independent fragments.

### Seed Lines

Possible outputs include:

- phrase
- doctrine
- proverb-like belief
- ritual formula
- implied custom
- symbolic association
- historical claim
- terminology

The line itself and the concept behind it are separate objects when both have independent value.

### Metadata

Metadata is primarily contextual.

Do not automatically promote:

- phase
- texture
- intensity
- voice
- use case
- darkness type
- percentage distribution
- generic keywords

into lore.

If metadata itself introduces a concrete new concept, extract it.

### Naming & IDs

Old IDs remain provenance.

Old proposed terms or names may yield `name` fragments if they have independent worldbuilding value.

Do not assume an old Exegate name is currently valid.

---


## 21A. Pipeline-wrapper stripping

Historical production instructions such as `Lore Architect could...`, `Codex Mapper might...`, `Page Drafter can...`, or `The Exegete could...` are pipeline residue, not world lore. Harvest embedded lore where useful and discard the wrapper as `pipeline_wrapper`.

## 21B. Independent-name restraint

Do not create a `name` fragment merely because Exegate coined a label. Emit an independent name only when terminology itself has standalone linguistic, cultural, ritual, legal, geographic, historical, social, or naming-system value. Otherwise preserve the term with its underlying concept.

## 21C. Seed Line phrase restraint

Do not create a `phrase` fragment for every Seed Line. First extract or merge the underlying lore. Preserve wording independently only when it has clear in-world function such as oath, formula, response, proverb, maxim, motto, inscription, epitaph, taboo phrase, greeting, curse, blessing, prophetic formula, legal formula, title, or distinctive saying.

---

## 22. Storage contract

Pilot layout:

```text
data/
└── lore_harvest/
    ├── exegate/
    │   ├── runs/
    │   │   └── <run-id>.json
    │   │
    │   └── sources/
    │       └── <source-key>/
    │           ├── harvest_manifest.json
    │           └── fragments.jsonl
    │
    └── library/
        ├── fragments.jsonl
        └── relations.jsonl
```

`fragments.jsonl` contains one fully materialized Lore Fragment per line.

The complete run response, including coverage and discarded items, belongs in the harvest manifest.

---

## 23. Validation rules

### LF13 validation

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
```

### LF14 validation

```text
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

## 24. Frozen baseline clauses

**LF-01:** Lore Fragment is the normalized unit of recovered lore.  
**LF-02:** `exegate_run.json` is the preferred Exegate extraction source.  
**LF-03:** One independently reusable idea per fragment.  
**LF-04:** Historical meaning and normalized lore remain separate.  
**LF-05:** Obsolete bindings are recorded, not erased silently.  
**LF-06:** No canon decisions occur during harvest.  
**LF-07:** No new lore is invented during normalization.  
**LF-08:** Exact JSON-pointer provenance is mandatory.  
**LF-09:** Intra-source duplicates merge; cross-source duplicates do not yet merge.  
**LF-10:** Every source receives a coverage audit.  
**LF-11:** Conflicting and abandoned material remains extractable.  
**LF-12:** The model generates fragment drafts; LV-Forge generates deterministic IDs.  
**LF-13:** Scalar source fields support exact zero-based, end-exclusive character-span provenance with exact-substring hashing; spans and hashes are resolved deterministically by LV-Forge and never guessed.  
**LF-14:** Derivation records an ordered sequence of substantive extraction operations, with a separate `primary_mode` identifying the operation most responsible for the final normalized representation. Supported operations are `direct`, `decomposed`, `generalized`, `implied`, and `merged_intra_source`.  
**LF-15:** Lore Harvest preserves source modality; normalization may never strengthen a proposal, hypothesis, interpretation, poetic formulation, or ambiguity into a more certain world claim.  
**LF-16:** Every provenance anchor records its semantic evidence layer so source semantics, Exegate interpretation, old LV application, generated hooks, generated phrases, and metadata remain distinguishable.

---

## 25. Explicit exclusions

v0.1.2 intentionally does not contain:

- canon status
- usefulness score
- quality score
- current-story placement
- automatic current-character assignment
- automatic current-religion assignment
- automatic conflict resolution
- cross-source merging
- final Obsidian path
- prose expansion

These belong to later systems, not harvesting.
