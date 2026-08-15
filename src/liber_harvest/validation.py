"""Deterministic harvest-result and source-coverage validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import PRIMARY_EXEGATE_FIELDS
from .constants import PIPELINE_WRAPPER_MARKERS
from .models import (
    ClaimModality, CoverageDisposition, ExegateHarvestResult, LoreFragmentRecord,
    ProvenancePrecision,
)
from .pointers import JsonPointerError, resolve_json_pointer
from .provenance import hash_pointer_value, sha256_text



_MODALITY_MARKERS = {
    ClaimModality.PROPOSED: (
        "proposed", "possible", "suggested", "envisaged", "imagined",
        "could", "might", "may", "would",
    ),
    ClaimModality.HYPOTHETICAL: ("hypothetical", "possible", "if ", "could", "might", "may", "would"),
    ClaimModality.INTERPRETIVE: (
        "interpret", "reading", "understood as", "treated as", "associated",
        "suggest", "can be read", "may signify", "viewed as",
    ),
    ClaimModality.POETIC: ("poetic", "metaphor", "figurative", "symbolic", "imagery", "association", "motif", "evokes"),
    ClaimModality.AMBIGUOUS: (
        "ambiguous", "uncertain", "unclear", "possible", "may", "might",
        "unresolved", "cannot be determined",
    ),
}

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def validate_result_against_source(
    result: ExegateHarvestResult,
    *,
    source_path: str,
    source_sha256: str,
    source_document: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if result.source.source_path != source_path:
        issues.append(ValidationIssue("source_path_mismatch", "Result source_path does not match input envelope"))
    if result.source.source_sha256.lower() != source_sha256.lower():
        issues.append(ValidationIssue("source_sha256_mismatch", "Result source_sha256 does not match input envelope"))

    coverage_pointers = {entry.json_pointer for entry in result.coverage}
    for field in PRIMARY_EXEGATE_FIELDS:
        if _nonempty(source_document.get(field)) and f"/{field}" not in coverage_pointers:
            issues.append(ValidationIssue(
                "coverage_missing",
                f"Non-empty primary Exegate field /{field} has no top-level coverage entry",
            ))

    concept_keys = {fragment.concept_key for fragment in result.fragments}
    for entry in result.coverage:
        unknown = [key for key in entry.concept_keys if key not in concept_keys]
        if unknown:
            issues.append(ValidationIssue(
                "coverage_unknown_concept",
                f"Coverage {entry.json_pointer} references unknown concept key(s): {', '.join(unknown)}",
            ))
        try:
            target = resolve_json_pointer(source_document, entry.json_pointer)
            if entry.disposition == CoverageDisposition.EMPTY and _nonempty(target):
                issues.append(ValidationIssue(
                    "coverage_false_empty",
                    f"Coverage {entry.json_pointer} is marked empty but source content is non-empty",
                ))
        except JsonPointerError as exc:
            issues.append(ValidationIssue("coverage_pointer_unresolved", str(exc)))

    for entry in result.discarded:
        try:
            resolve_json_pointer(source_document, entry.json_pointer)
        except JsonPointerError as exc:
            issues.append(ValidationIssue("discard_pointer_unresolved", str(exc)))

    for fragment in result.fragments:
        for anchor in fragment.provenance:
            if anchor.source_path != source_path:
                issues.append(ValidationIssue(
                    "anchor_source_path_mismatch",
                    f"{fragment.concept_key}: provenance source_path differs from input source",
                ))
            if anchor.source_sha256.lower() != source_sha256.lower():
                issues.append(ValidationIssue(
                    "anchor_source_sha256_mismatch",
                    f"{fragment.concept_key}: provenance source_sha256 differs from input source",
                ))
            try:
                target = resolve_json_pointer(source_document, anchor.json_pointer)
                if not isinstance(target, str):
                    issues.append(ValidationIssue(
                        "anchor_target_not_text",
                        f"{fragment.concept_key}: provenance pointer must resolve to a textual scalar",
                    ))
            except JsonPointerError as exc:
                issues.append(ValidationIssue(
                    "anchor_pointer_unresolved",
                    f"{fragment.concept_key}: {exc}",
                ))

        normalized = fragment.content.normalized_lore.casefold()
        leaked = [marker for marker in PIPELINE_WRAPPER_MARKERS if marker in normalized]
        if leaked:
            issues.append(ValidationIssue(
                "pipeline_wrapper_leak",
                f"{fragment.concept_key}: normalized_lore retains pipeline wrapper marker(s): {', '.join(leaked)}",
            ))
        markers = _MODALITY_MARKERS.get(fragment.claim.modality)
        if markers and not any(marker in normalized for marker in markers):
            issues.append(ValidationIssue(
                "modality_wording_unsafe",
                f"{fragment.concept_key}: normalized_lore does not visibly preserve "
                f"{fragment.claim.modality.value} modality",
            ))

    return issues



def validate_materialized_record(
    record: LoreFragmentRecord,
    *,
    source_document: dict[str, Any],
) -> list[ValidationIssue]:
    """Verify LF-13 hashes/spans against the current canonical source document."""
    issues: list[ValidationIssue] = []
    for anchor in record.provenance:
        try:
            target = resolve_json_pointer(source_document, anchor.json_pointer)
        except JsonPointerError as exc:
            issues.append(ValidationIssue("provenance_stale", f"{record.fragment_id}: {exc}"))
            continue
        if not isinstance(target, str):
            issues.append(ValidationIssue(
                "anchor_target_not_text",
                f"{record.fragment_id}: {anchor.json_pointer} no longer resolves to textual evidence",
            ))
            continue
        if hash_pointer_value(target) != anchor.anchor_sha256:
            issues.append(ValidationIssue(
                "provenance_stale",
                f"{record.fragment_id}: anchor hash changed at {anchor.json_pointer}",
            ))
        if anchor.precision == ProvenancePrecision.SPAN:
            span = anchor.source_span
            if span is None or span.end > len(target):
                issues.append(ValidationIssue(
                    "provenance_stale",
                    f"{record.fragment_id}: source span is out of bounds at {anchor.json_pointer}",
                ))
                continue
            text = target[span.start:span.end]
            if sha256_text(text) != span.text_sha256:
                issues.append(ValidationIssue(
                    "provenance_stale",
                    f"{record.fragment_id}: span hash changed at {anchor.json_pointer}",
                ))
            if text != anchor.excerpt:
                issues.append(ValidationIssue(
                    "provenance_stale",
                    f"{record.fragment_id}: stored excerpt no longer matches materialized span",
                ))
        elif anchor.precision == ProvenancePrecision.ITEM and anchor.excerpt != target:
            issues.append(ValidationIssue(
                "provenance_stale",
                f"{record.fragment_id}: item excerpt no longer equals pointer target",
            ))
    return issues
