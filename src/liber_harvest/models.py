"""Strict Pydantic models implementing Lore Harvest v0.1.2."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import (
    CONTRACT_VERSION,
    DOMAINS,
    EXTRACTOR_VERSION,
    FRAGMENT_SCHEMA_VERSION,
    MANIFEST_VERSION,
    RELATION_SCHEMA_VERSION,
    TYPE_CODES,
)
from .pointers import is_valid_json_pointer

_SHA256_RE = re.compile(r"^[A-Fa-f0-9]{64}$")
_CONCEPT_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+){2,9}$")
_TAG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_FRAGMENT_ID_RE = re.compile(r"^LFR-([A-Z]{3})-([A-F0-9]{12})$")
_RELATION_ID_RE = re.compile(r"^LRL-[A-F0-9]{12}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoreType(StrEnum):
    PERSON = "person"
    GROUP = "group"
    INSTITUTION = "institution"
    OFFICE = "office"
    PLACE = "place"
    STRUCTURE = "structure"
    ARCHITECTURE = "architecture"
    OBJECT = "object"
    RELIC = "relic"
    MATERIAL = "material"
    FLORA = "flora"
    CREATURE = "creature"
    RITUAL = "ritual"
    CUSTOM = "custom"
    PRACTICE = "practice"
    LAW = "law"
    SOCIAL_STRUCTURE = "social_structure"
    ECONOMY = "economy"
    TRADE = "trade"
    WARFARE = "warfare"
    DOCTRINE = "doctrine"
    BELIEF = "belief"
    COSMOLOGY = "cosmology"
    MYTH = "myth"
    LEGEND = "legend"
    SYMBOL = "symbol"
    EVENT = "event"
    HISTORICAL_CLAIM = "historical_claim"
    SOMATIC = "somatic"
    PATHOLOGY = "pathology"
    MEDICINE = "medicine"
    ENVIRONMENT = "environment"
    LANGUAGE = "language"
    NAME = "name"
    PHRASE = "phrase"
    MOTIF = "motif"
    SENSORY_PALETTE = "sensory_palette"
    NARRATIVE_HOOK = "narrative_hook"
    CHARACTER_HOOK = "character_hook"
    OTHER = "other"


class ClaimModality(StrEnum):
    ASSERTED = "asserted"
    PROPOSED = "proposed"
    HYPOTHETICAL = "hypothetical"
    INTERPRETIVE = "interpretive"
    POETIC = "poetic"
    AMBIGUOUS = "ambiguous"


class EvidenceLayer(StrEnum):
    SOURCE_SEMANTICS = "source_semantics"
    EXEGATE_INTERPRETATION = "exegate_interpretation"
    LV_APPLICATION = "lv_application"
    GENERATED_HOOK = "generated_hook"
    GENERATED_PHRASE = "generated_phrase"
    METADATA = "metadata"


class DerivationOperation(StrEnum):
    DIRECT = "direct"
    DECOMPOSED = "decomposed"
    GENERALIZED = "generalized"
    IMPLIED = "implied"
    MERGED_INTRA_SOURCE = "merged_intra_source"


class Fidelity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BindingKind(StrEnum):
    CHARACTER = "character"
    INSTITUTION = "institution"
    RELIGION = "religion"
    COSMOLOGY = "cosmology"
    LOCATION = "location"
    TIMELINE = "timeline"
    PLOT = "plot"
    TERMINOLOGY = "terminology"
    ROLE = "role"
    STRUCTURE = "structure"
    OTHER = "other"


class BindingHandling(StrEnum):
    RETAINED = "retained"
    GENERALIZED = "generalized"
    REMOVED = "removed_from_normalized"
    ESSENTIAL = "essential"


class ProvenanceRole(StrEnum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    DUPLICATE = "duplicate"


class ProvenancePrecision(StrEnum):
    FIELD = "field"
    SPAN = "span"
    ITEM = "item"


class Circle(StrEnum):
    PRIMA_MATERIA = "prima_materia"
    VECTORS = "vectors_of_corruption"
    SYMBOLS = "symbols"
    PSYCH = "psychological_pathology"
    RITUALS = "ritual_extraction"
    ATMOSPHERICS = "atmospherics_texture"
    NARRATIVE = "narrative_potential"
    SEEDS = "seed_line_distillation"
    METADATA = "metadata_assessment"
    NAMING = "naming_ids"


class RelationType(StrEnum):
    RELATED_TO = "related_to"
    COMPONENT_OF = "component_of"
    VARIANT_OF = "variant_of"
    CONTRADICTS = "contradicts"
    REQUIRES = "requires"
    PRODUCES = "produces"
    PERFORMED_AT = "performed_at"
    LOCATED_IN = "located_in"
    ASSOCIATED_WITH = "associated_with"
    DERIVED_FROM = "derived_from"


class ReviewReason(StrEnum):
    SOURCE_AMBIGUITY = "source_ambiguity"
    HEAVY_GENERALIZATION = "heavy_generalization"
    POSSIBLE_OVER_SPLIT = "possible_over_split"
    POSSIBLE_UNDER_SPLIT = "possible_under_split"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    MIXED_CONCEPTS = "mixed_concepts"
    UNCERTAIN_TYPE = "uncertain_type"
    BROKEN_SOURCE_STRUCTURE = "broken_source_structure"
    LEGACY_DEPENDENCY_HEAVY = "legacy_dependency_heavy"
    PROVENANCE_PRECISION_REDUCED = "provenance_precision_reduced"
    PROVENANCE_SPAN_AMBIGUOUS = "provenance_span_ambiguous"
    PROVENANCE_EXCERPT_UNRESOLVED = "provenance_excerpt_unresolved"
    OTHER = "other"


class CoverageDisposition(StrEnum):
    EXTRACTED = "extracted"
    MERGED = "merged"
    METADATA_ONLY = "metadata_only"
    EMPTY = "empty"
    NON_LORE = "non_lore"
    UNPARSEABLE = "unparseable"


class DiscardReason(StrEnum):
    DUPLICATE = "duplicate_within_source"
    NON_LORE_METADATA = "non_lore_metadata"
    IDENTIFIER_ONLY = "identifier_only"
    FORMATTING_ONLY = "formatting_only"
    EMPTY = "empty"
    PARSER_ARTIFACT = "parser_artifact"
    PIPELINE_WRAPPER = "pipeline_wrapper"


def _validate_sha(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("Expected a 64-character SHA-256 hexadecimal digest")
    return value.lower()


def _check_primary(anchors: list[Any]) -> None:
    count = sum(1 for anchor in anchors if anchor.role == ProvenanceRole.PRIMARY)
    if count != 1:
        raise ValueError(f"Exactly one provenance anchor must have role=primary; found {count}")


class Claim(StrictModel):
    modality: ClaimModality


class Content(StrictModel):
    source_meaning: str = Field(min_length=1)
    normalized_lore: str = Field(min_length=1)
    details: list[str] = Field(default_factory=list)


class LegacyBinding(StrictModel):
    kind: BindingKind
    value: str = Field(min_length=1)
    handling: BindingHandling
    note: str | None = None


class Derivation(StrictModel):
    primary_mode: DerivationOperation
    operations: list[DerivationOperation] = Field(min_length=1)
    fidelity: Fidelity
    inference_note: str | None = None

    @model_validator(mode="after")
    def validate_derivation(self):
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("Derivation operations must not contain duplicates")
        if self.primary_mode not in self.operations:
            raise ValueError("primary_mode must appear in operations")
        if DerivationOperation.DIRECT in self.operations and self.operations != [DerivationOperation.DIRECT]:
            raise ValueError("direct must be the sole derivation operation when present")
        if self.fidelity == Fidelity.LOW and not self.inference_note:
            raise ValueError("Low-fidelity derivation requires inference_note")
        return self


class SourceSpan(StrictModel):
    unit: str = "char"
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    text_sha256: str

    _sha = field_validator("text_sha256")(_validate_sha)

    @model_validator(mode="after")
    def validate_span(self):
        if self.unit != "char":
            raise ValueError("v0.1.2 source spans use unit=char")
        if self.end <= self.start:
            raise ValueError("source_span.end must be greater than source_span.start")
        return self


class ProvenanceDraft(StrictModel):
    pipeline: str = "exegate"
    source_path: str = Field(min_length=1)
    source_sha256: str
    source_title: str | None = None
    bundle_id: str | None = None
    source_item_id: str | None = None
    circle: Circle
    evidence_layer: EvidenceLayer
    source_modality: ClaimModality
    json_pointer: str
    role: ProvenanceRole
    excerpt: str = Field(min_length=1)

    _sha = field_validator("source_sha256")(_validate_sha)

    @field_validator("pipeline")
    @classmethod
    def pipeline_is_exegate(cls, value: str) -> str:
        if value != "exegate":
            raise ValueError("Lore Harvest v0.1.2 pilot pipeline must be exegate")
        return value

    @field_validator("json_pointer")
    @classmethod
    def valid_pointer(cls, value: str) -> str:
        if not is_valid_json_pointer(value):
            raise ValueError("json_pointer must be a valid RFC 6901 pointer")
        return value

    @model_validator(mode="after")
    def constrain_generated_layers(self):
        if self.evidence_layer == EvidenceLayer.GENERATED_HOOK and self.source_modality == ClaimModality.ASSERTED:
            raise ValueError("generated_hook evidence cannot be asserted in v0.1.2")
        if self.evidence_layer == EvidenceLayer.GENERATED_PHRASE and self.source_modality == ClaimModality.ASSERTED:
            raise ValueError("generated_phrase evidence cannot be asserted in v0.1.2")
        return self


class ProvenanceAnchor(ProvenanceDraft):
    precision: ProvenancePrecision
    source_span: SourceSpan | None
    anchor_sha256: str

    _anchor_sha = field_validator("anchor_sha256")(_validate_sha)

    @model_validator(mode="after")
    def precision_matches_span(self):
        if self.precision == ProvenancePrecision.SPAN and self.source_span is None:
            raise ValueError("precision=span requires source_span")
        if self.precision != ProvenancePrecision.SPAN and self.source_span is not None:
            raise ValueError("field/item precision requires source_span=null")
        return self


class RelationHint(StrictModel):
    relation: RelationType
    target_concept_key: str | None = None
    target_fragment_id: str | None = None
    note: str | None = None

    @field_validator("target_concept_key")
    @classmethod
    def concept_key_valid(cls, value: str | None):
        if value is not None and not _CONCEPT_RE.fullmatch(value):
            raise ValueError("target_concept_key must use 3-10 lower_snake_case tokens")
        return value

    @field_validator("target_fragment_id")
    @classmethod
    def target_fragment_valid(cls, value: str | None):
        if value is not None and not _FRAGMENT_ID_RE.fullmatch(value):
            raise ValueError("target_fragment_id must be a materialized LFR-* ID")
        return value

    @model_validator(mode="after")
    def target_present(self):
        if not self.target_concept_key and not self.target_fragment_id:
            raise ValueError("Relation hint requires target_concept_key or target_fragment_id")
        return self


class Review(StrictModel):
    required: bool = False
    reasons: list[ReviewReason] = Field(default_factory=list)

    @model_validator(mode="after")
    def reasons_match_required(self):
        if self.required and not self.reasons:
            raise ValueError("review.required=true requires at least one reason")
        if not self.required and self.reasons:
            raise ValueError("review.required=false requires an empty reasons list")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("review reasons must be unique")
        return self


class HarvestMeta(StrictModel):
    contract_version: str = CONTRACT_VERSION
    extractor_version: str = EXTRACTOR_VERSION
    run_id: str = Field(min_length=1)

    @field_validator("contract_version")
    @classmethod
    def current_contract(cls, value: str):
        if value != CONTRACT_VERSION:
            raise ValueError(f"Expected contract_version={CONTRACT_VERSION}")
        return value


class _FragmentCommon(StrictModel):
    concept_key: str
    type: LoreType
    title: str = Field(min_length=1)
    claim: Claim
    content: Content
    domains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    legacy_bindings: list[LegacyBinding] = Field(default_factory=list)
    derivation: Derivation
    relation_hints: list[RelationHint] = Field(default_factory=list)
    review: Review

    @field_validator("concept_key")
    @classmethod
    def concept_key_valid(cls, value: str):
        if not _CONCEPT_RE.fullmatch(value):
            raise ValueError("concept_key must use 3-10 lower_snake_case tokens")
        return value

    @field_validator("domains")
    @classmethod
    def domains_valid(cls, values: list[str]):
        if len(values) != len(set(values)):
            raise ValueError("domains must be unique")
        unknown = [value for value in values if value not in DOMAINS]
        if unknown:
            raise ValueError(f"Unknown domain(s): {', '.join(unknown)}")
        return values

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values: list[str]):
        if len(values) != len(set(values)):
            raise ValueError("tags must be unique")
        for value in values:
            if not _TAG_RE.fullmatch(value):
                raise ValueError(f"Invalid tag {value!r}; expected lower_snake_case")
        return values


class LoreFragmentDraft(_FragmentCommon):
    provenance: list[ProvenanceDraft] = Field(min_length=1)

    @model_validator(mode="after")
    def cross_validate(self):
        _check_primary(self.provenance)
        if self.claim.modality == ClaimModality.AMBIGUOUS and not self.review.required:
            raise ValueError("ambiguous claim modality requires review")
        if self.claim.modality == ClaimModality.ASSERTED and not any(
            anchor.source_modality == ClaimModality.ASSERTED for anchor in self.provenance
        ):
            raise ValueError("asserted claim requires at least one asserted provenance anchor")
        if DerivationOperation.MERGED_INTRA_SOURCE in self.derivation.operations and len(self.provenance) < 2:
            raise ValueError("merged_intra_source requires at least two provenance anchors")
        return self


class LoreFragmentRecord(_FragmentCommon):
    schema_version: str = FRAGMENT_SCHEMA_VERSION
    fragment_id: str
    provenance: list[ProvenanceAnchor] = Field(min_length=1)
    harvest: HarvestMeta

    @field_validator("schema_version")
    @classmethod
    def current_schema(cls, value: str):
        if value != FRAGMENT_SCHEMA_VERSION:
            raise ValueError(f"Expected schema_version={FRAGMENT_SCHEMA_VERSION}")
        return value

    @model_validator(mode="after")
    def cross_validate(self):
        _check_primary(self.provenance)
        match = _FRAGMENT_ID_RE.fullmatch(self.fragment_id)
        if not match:
            raise ValueError("fragment_id must match LFR-{TYPECODE}-{12_HEX}")
        expected = TYPE_CODES[self.type.value]
        if match.group(1) != expected:
            raise ValueError(f"fragment_id type code {match.group(1)} does not match type={self.type.value}")
        if self.claim.modality == ClaimModality.AMBIGUOUS and not self.review.required:
            raise ValueError("ambiguous claim modality requires review")
        if self.claim.modality == ClaimModality.ASSERTED and not any(
            anchor.source_modality == ClaimModality.ASSERTED for anchor in self.provenance
        ):
            raise ValueError("asserted claim requires at least one asserted provenance anchor")
        if DerivationOperation.MERGED_INTRA_SOURCE in self.derivation.operations and len(self.provenance) < 2:
            raise ValueError("merged_intra_source requires at least two provenance anchors")
        return self


class HarvestSourceRef(StrictModel):
    pipeline: str = "exegate"
    source_path: str = Field(min_length=1)
    source_sha256: str
    source_title: str | None = None
    bundle_id: str | None = None

    _sha = field_validator("source_sha256")(_validate_sha)

    @field_validator("pipeline")
    @classmethod
    def pipeline_valid(cls, value: str):
        if value != "exegate":
            raise ValueError("pipeline must be exegate")
        return value


class HarvestInputEnvelope(StrictModel):
    contract_version: str = CONTRACT_VERSION
    source_path: str
    source_sha256: str
    source_format: Literal["exegate_run_json", "exegate_markdown"]
    source: dict[str, Any]

    _sha = field_validator("source_sha256")(_validate_sha)

    @field_validator("contract_version")
    @classmethod
    def envelope_contract_valid(cls, value: str):
        if value != CONTRACT_VERSION:
            raise ValueError(f"Expected contract_version={CONTRACT_VERSION}")
        return value


class CoverageEntry(StrictModel):
    json_pointer: str
    disposition: CoverageDisposition
    evidence_layer: EvidenceLayer | None = None
    source_modality: ClaimModality | None = None
    concept_keys: list[str] = Field(default_factory=list)

    @field_validator("json_pointer")
    @classmethod
    def pointer_valid(cls, value: str):
        if not is_valid_json_pointer(value):
            raise ValueError("coverage json_pointer must be RFC 6901")
        return value

    @field_validator("concept_keys")
    @classmethod
    def keys_valid(cls, values: list[str]):
        for value in values:
            if not _CONCEPT_RE.fullmatch(value):
                raise ValueError(f"Invalid concept key in coverage: {value}")
        return values

    @model_validator(mode="after")
    def coverage_semantics(self):
        if self.disposition in {CoverageDisposition.EXTRACTED, CoverageDisposition.MERGED} and not self.concept_keys:
            raise ValueError("extracted/merged coverage requires concept_keys")
        return self


class DiscardedEntry(StrictModel):
    json_pointer: str
    reason: DiscardReason
    note: str | None = None

    @field_validator("json_pointer")
    @classmethod
    def pointer_valid(cls, value: str):
        if not is_valid_json_pointer(value):
            raise ValueError("discard json_pointer must be RFC 6901")
        return value


class ExegateHarvestResult(StrictModel):
    contract_version: str = CONTRACT_VERSION
    source: HarvestSourceRef
    fragments: list[LoreFragmentDraft] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    discarded: list[DiscardedEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("contract_version")
    @classmethod
    def current_contract(cls, value: str):
        if value != CONTRACT_VERSION:
            raise ValueError(f"Expected contract_version={CONTRACT_VERSION}")
        return value

    @model_validator(mode="after")
    def unique_result_keys(self):
        keys = [fragment.concept_key for fragment in self.fragments]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate concept_key values remain after intra-source extraction")
        coverage_pointers = [entry.json_pointer for entry in self.coverage]
        if len(coverage_pointers) != len(set(coverage_pointers)):
            raise ValueError("Duplicate coverage json_pointer entries are not allowed")
        discard_keys = [(entry.json_pointer, entry.reason) for entry in self.discarded]
        if len(discard_keys) != len(set(discard_keys)):
            raise ValueError("Duplicate discarded pointer/reason entries are not allowed")
        return self


class RelationRecord(StrictModel):
    schema_version: str = RELATION_SCHEMA_VERSION
    relation_id: str
    relation: RelationType
    source_fragment_id: str
    target_fragment_id: str
    origin: str
    evidence_fragment_ids: list[str] = Field(min_length=1)
    note: str | None = None
    harvest_run_id: str | None = None

    @field_validator("relation_id")
    @classmethod
    def relation_id_valid(cls, value: str):
        if not _RELATION_ID_RE.fullmatch(value):
            raise ValueError("relation_id must match LRL-{12_HEX}")
        return value

    @field_validator("schema_version")
    @classmethod
    def relation_schema_valid(cls, value: str):
        if value != RELATION_SCHEMA_VERSION:
            raise ValueError(f"Expected schema_version={RELATION_SCHEMA_VERSION}")
        return value

    @field_validator("source_fragment_id", "target_fragment_id")
    @classmethod
    def fragment_id_valid(cls, value: str):
        if not _FRAGMENT_ID_RE.fullmatch(value):
            raise ValueError("Relation endpoint must be a materialized LFR-* fragment ID")
        return value

    @field_validator("evidence_fragment_ids")
    @classmethod
    def evidence_ids_valid(cls, values: list[str]):
        if len(values) != len(set(values)):
            raise ValueError("evidence_fragment_ids must be unique")
        if any(not _FRAGMENT_ID_RE.fullmatch(value) for value in values):
            raise ValueError("Every evidence_fragment_id must be a materialized LFR-* ID")
        return values

    @field_validator("origin")
    @classmethod
    def origin_valid(cls, value: str):
        if value not in {"relation_hint", "library_reconciliation"}:
            raise ValueError("Invalid relation origin")
        return value


class JsonlArtifactInfo(StrictModel):
    path: str = Field(min_length=1)
    sha256: str
    records: int = Field(ge=0)
    _sha = field_validator("sha256")(_validate_sha)


class JsonArtifactInfo(StrictModel):
    path: str = Field(min_length=1)
    sha256: str
    _sha = field_validator("sha256")(_validate_sha)


class ManifestCounts(StrictModel):
    fragments: int = Field(ge=0)
    coverage_entries: int = Field(ge=0)
    discarded: int = Field(ge=0)
    warnings: int = Field(ge=0)
    review_required: int = Field(ge=0)


class HarvestArtifacts(StrictModel):
    fragments_jsonl: JsonlArtifactInfo
    run_json: JsonArtifactInfo


class HarvestManifest(StrictModel):
    manifest_version: str = MANIFEST_VERSION
    run_id: str
    contract_version: str = CONTRACT_VERSION
    fragment_schema_version: str = FRAGMENT_SCHEMA_VERSION
    source: HarvestSourceRef
    counts: ManifestCounts
    artifacts: HarvestArtifacts
    warnings: list[str]
    created_at: datetime

    @field_validator("manifest_version")
    @classmethod
    def manifest_version_valid(cls, value: str):
        if value != MANIFEST_VERSION:
            raise ValueError(f"Expected manifest_version={MANIFEST_VERSION}")
        return value

    @field_validator("contract_version")
    @classmethod
    def manifest_contract_valid(cls, value: str):
        if value != CONTRACT_VERSION:
            raise ValueError(f"Expected contract_version={CONTRACT_VERSION}")
        return value

    @field_validator("fragment_schema_version")
    @classmethod
    def manifest_fragment_schema_valid(cls, value: str):
        if value != FRAGMENT_SCHEMA_VERSION:
            raise ValueError(f"Expected fragment_schema_version={FRAGMENT_SCHEMA_VERSION}")
        return value
