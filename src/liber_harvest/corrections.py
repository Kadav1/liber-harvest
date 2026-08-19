"""Deterministic corrections for model-produced Exegate harvest candidates.

These corrections are deliberately narrow. They repair structural facts that Liber
Harvest can prove from the source document without asking a model to reinterpret
lore. They do not make canon decisions or invent missing semantics.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from .models import HarvestInputEnvelope
from .pointers import JsonPointerError, resolve_json_pointer

_FIELD_CIRCLES = {
    "prima_materia_raw": "prima_materia",
    "vectors_raw": "vectors_of_corruption",
    "vectors": "vectors_of_corruption",
    "symbols": "symbols",
    "psych_pathology_raw": "psychological_pathology",
    "rituals": "ritual_extraction",
    "atmospherics_raw": "atmospherics_texture",
    "scene_hooks": "narrative_potential",
    "seed_lines": "seed_line_distillation",
    "metadata_raw": "metadata_assessment",
    "naming_ids_raw": "naming_ids",
}

_EMPTY_VALUES = (None, "")


def _source_title(document: dict[str, Any]) -> str | None:
    value = document.get("song_title")
    return str(value) if value is not None else None


def _is_empty(value: Any) -> bool:
    return value in _EMPTY_VALUES or value == [] or value == {}


def _circle_for_pointer(pointer: str) -> str | None:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return None
    token = pointer.split("/", 2)[1].replace("~1", "/").replace("~0", "~")
    return _FIELD_CIRCLES.get(token)


def _resolve_or_none(document: dict[str, Any], pointer: str) -> Any:
    try:
        return resolve_json_pointer(document, pointer)
    except JsonPointerError:
        return None


def _canonical_scalar_pointer(
    document: dict[str, Any], pointer: str, excerpt: str | None
) -> str:
    """Collapse bogus scalar child pointers such as /field/1 to /field.

    The correction is only applied when the parent exists, is scalar text, and the
    supplied excerpt can be found exactly inside that scalar. That keeps LF-13
    provenance correction deterministic rather than heuristic.
    """
    try:
        resolve_json_pointer(document, pointer)
        return pointer
    except JsonPointerError:
        pass

    current = pointer
    while "/" in current[1:]:
        parent, token = current.rsplit("/", 1)
        if not token.isdigit():
            break
        try:
            value = resolve_json_pointer(document, parent)
        except JsonPointerError:
            current = parent
            continue
        if isinstance(value, str) and excerpt and excerpt in value:
            return parent
        break
    return pointer


def _normalize_details(content: dict[str, Any], changes: list[str]) -> None:
    details = content.get("details")
    if details is None:
        content["details"] = []
        changes.append("content.details:null->[]")
        return
    if isinstance(details, dict):
        content["details"] = [f"{key}: {value}" for key, value in details.items()]
        changes.append("content.details:object->list")
    elif isinstance(details, str):
        content["details"] = [details]
        changes.append("content.details:string->list")


def _normalize_derivation(fragment: dict[str, Any], changes: list[str]) -> None:
    derivation = fragment.get("derivation")
    if not isinstance(derivation, dict):
        return
    primary = derivation.get("primary_mode")
    operations = derivation.get("operations")
    if not isinstance(primary, str) or not isinstance(operations, list):
        return
    normalized = [str(value) for value in operations]
    if primary == "direct" and normalized != ["direct"]:
        derivation["operations"] = ["direct"]
        changes.append("derivation:direct-made-exclusive")
        return
    if primary != "direct" and "direct" in normalized:
        normalized = [value for value in normalized if value != "direct"]
        if primary not in normalized:
            normalized.insert(0, primary)
        derivation["operations"] = list(dict.fromkeys(normalized))
        changes.append("derivation:removed-conflicting-direct")
    elif primary not in normalized:
        derivation["operations"] = [primary, *normalized]
        changes.append("derivation:inserted-primary-operation")


def _canonical_source_ref(
    source_ref: dict[str, Any], envelope: HarvestInputEnvelope, changes: list[str]
) -> None:
    expected = {
        "pipeline": "exegate",
        "source_path": envelope.source_path,
        "source_sha256": envelope.source_sha256,
        "source_title": _source_title(envelope.source),
    }
    for key, value in expected.items():
        if source_ref.get(key) != value:
            source_ref[key] = value
            changes.append(f"source.{key}:canonicalized")


def _canonical_provenance(
    fragment: dict[str, Any], envelope: HarvestInputEnvelope, changes: list[str]
) -> None:
    provenance = fragment.get("provenance")
    if not isinstance(provenance, list):
        return
    for index, anchor in enumerate(provenance):
        if not isinstance(anchor, dict):
            continue
        expected = {
            "pipeline": "exegate",
            "source_path": envelope.source_path,
            "source_sha256": envelope.source_sha256,
            "source_title": _source_title(envelope.source),
        }
        for key, value in expected.items():
            if anchor.get(key) != value:
                anchor[key] = value
                changes.append(f"provenance[{index}].{key}:canonicalized")

        pointer = anchor.get("json_pointer")
        excerpt = anchor.get("excerpt")
        if isinstance(pointer, str):
            canonical = _canonical_scalar_pointer(
                envelope.source, pointer, excerpt if isinstance(excerpt, str) else None
            )
            if canonical != pointer:
                anchor["json_pointer"] = canonical
                pointer = canonical
                changes.append(f"provenance[{index}].json_pointer:scalar-parent")
            circle = _circle_for_pointer(pointer)
            if circle and anchor.get("circle") != circle:
                anchor["circle"] = circle
                changes.append(f"provenance[{index}].circle:derived-from-pointer")

        layer = anchor.get("evidence_layer")
        if layer in {"generated_hook", "generated_phrase"} and anchor.get(
            "source_modality"
        ) == "asserted":
            anchor["source_modality"] = "proposed"
            changes.append(f"provenance[{index}].source_modality:asserted->proposed")

    claim = fragment.get("claim")
    if isinstance(claim, dict) and claim.get("modality") == "asserted":
        asserted_anchor = any(
            isinstance(anchor, dict) and anchor.get("source_modality") == "asserted"
            for anchor in provenance
        )
        if not asserted_anchor:
            claim["modality"] = "proposed"
            changes.append("claim.modality:asserted->proposed")


def _fragment_is_empty_source(
    fragment: dict[str, Any], document: dict[str, Any]
) -> tuple[bool, list[str]]:
    provenance = fragment.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        return False, []
    pointers: list[str] = []
    resolved: list[Any] = []
    for anchor in provenance:
        if not isinstance(anchor, dict):
            return False, []
        pointer = anchor.get("json_pointer")
        if not isinstance(pointer, str):
            return False, []
        try:
            value = resolve_json_pointer(document, pointer)
        except JsonPointerError:
            return False, []
        pointers.append(pointer)
        resolved.append(value)
    return bool(resolved) and all(_is_empty(value) for value in resolved), pointers


def apply_deterministic_corrections(
    candidate: dict[str, Any], envelope: HarvestInputEnvelope
) -> tuple[dict[str, Any], list[str]]:
    """Return a corrected deep copy and an audit trail of structural changes."""
    result = deepcopy(candidate)
    changes: list[str] = []

    source_ref = result.get("source")
    if isinstance(source_ref, dict):
        _canonical_source_ref(source_ref, envelope, changes)

    fragments = result.get("fragments")
    removed_keys: set[str] = set()
    removed_pointers: list[str] = []
    kept: list[Any] = []
    if isinstance(fragments, list):
        for index, fragment in enumerate(fragments):
            if not isinstance(fragment, dict):
                kept.append(fragment)
                continue
            content = fragment.get("content")
            if isinstance(content, dict):
                _normalize_details(content, changes)
            _normalize_derivation(fragment, changes)
            _canonical_provenance(fragment, envelope, changes)
            is_empty, pointers = _fragment_is_empty_source(fragment, envelope.source)
            if is_empty:
                key = fragment.get("concept_key")
                if isinstance(key, str):
                    removed_keys.add(key)
                removed_pointers.extend(pointers)
                changes.append(f"fragments[{index}]:removed-empty-source")
                continue
            kept.append(fragment)
        result["fragments"] = kept

    coverage = result.get("coverage")
    if isinstance(coverage, list):
        for entry in coverage:
            if not isinstance(entry, dict):
                continue
            keys = entry.get("concept_keys")
            if isinstance(keys, list) and removed_keys:
                new_keys = [key for key in keys if key not in removed_keys]
                if new_keys != keys:
                    entry["concept_keys"] = new_keys
                    changes.append("coverage:removed-empty-fragment-reference")
            pointer = entry.get("json_pointer")
            if isinstance(pointer, str):
                value = _resolve_or_none(envelope.source, pointer)
                if _is_empty(value) and not entry.get("concept_keys"):
                    entry["disposition"] = "empty"
                    entry["evidence_layer"] = None
                    entry["source_modality"] = None
                    changes.append("coverage:empty-source-normalized")

    if removed_pointers:
        discarded = result.setdefault("discarded", [])
        if isinstance(discarded, list):
            existing = {
                (entry.get("json_pointer"), entry.get("reason"))
                for entry in discarded
                if isinstance(entry, dict)
            }
            for pointer in sorted(set(removed_pointers)):
                item = (pointer, "empty")
                if item not in existing:
                    discarded.append(
                        {
                            "json_pointer": pointer,
                            "reason": "empty",
                            "note": "Removed deterministically because the referenced source value is empty.",
                        }
                    )
                    existing.add(item)
                    changes.append("discarded:recorded-empty-source")

    return result, changes


def fragment_error_indices(exc: ValidationError) -> tuple[int, ...]:
    indices: set[int] = set()
    for error in exc.errors():
        loc = error.get("loc", ())
        if len(loc) >= 2 and loc[0] == "fragments" and isinstance(loc[1], int):
            indices.add(loc[1])
    return tuple(sorted(indices))


def all_validation_errors_fragment_local(exc: ValidationError) -> bool:
    """Return True only when every schema error belongs to one fragment item."""
    errors = exc.errors()
    if not errors:
        return False
    return all(
        len(error.get("loc", ())) >= 2
        and error["loc"][0] == "fragments"
        and isinstance(error["loc"][1], int)
        for error in errors
    )


def make_fragment_repair_subset(
    candidate: dict[str, Any], indices: tuple[int, ...]
) -> dict[str, Any] | None:
    fragments = candidate.get("fragments")
    if not indices or not isinstance(fragments, list):
        return None
    if any(index < 0 or index >= len(fragments) for index in indices):
        return None
    selected = [deepcopy(fragments[index]) for index in indices]
    keys = {
        fragment.get("concept_key")
        for fragment in selected
        if isinstance(fragment, dict) and isinstance(fragment.get("concept_key"), str)
    }
    coverage = candidate.get("coverage")
    selected_coverage: list[Any] = []
    if isinstance(coverage, list):
        for entry in coverage:
            if not isinstance(entry, dict):
                continue
            concept_keys = entry.get("concept_keys")
            if isinstance(concept_keys, list) and keys.intersection(concept_keys):
                selected_coverage.append(deepcopy(entry))
    return {
        "contract_version": candidate.get("contract_version"),
        "source": deepcopy(candidate.get("source")),
        "fragments": selected,
        "coverage": selected_coverage,
        "discarded": [],
        "warnings": [],
    }


def _remap_coverage_key(candidate: dict[str, Any], old_key: str, new_key: str) -> None:
    if old_key == new_key:
        return
    coverage = candidate.get("coverage")
    if not isinstance(coverage, list):
        return
    for entry in coverage:
        if not isinstance(entry, dict):
            continue
        keys = entry.get("concept_keys")
        if not isinstance(keys, list):
            continue
        entry["concept_keys"] = [new_key if key == old_key else key for key in keys]


def merge_fragment_repair(
    candidate: dict[str, Any], indices: tuple[int, ...], repaired_subset: dict[str, Any]
) -> dict[str, Any]:
    merged = deepcopy(candidate)
    fragments = merged.get("fragments")
    repaired = repaired_subset.get("fragments")
    if not isinstance(fragments, list) or not isinstance(repaired, list):
        raise TypeError("Fragment repair response must contain a fragments list")
    if len(repaired) != len(indices):
        raise ValueError(
            f"Fragment repair returned {len(repaired)} fragments for {len(indices)} requested fragments"
        )
    for target_index, repaired_fragment in zip(indices, repaired, strict=True):
        original = fragments[target_index]
        if isinstance(original, dict) and isinstance(repaired_fragment, dict):
            old_key = original.get("concept_key")
            new_key = repaired_fragment.get("concept_key")
            if isinstance(old_key, str) and isinstance(new_key, str):
                _remap_coverage_key(merged, old_key, new_key)
        fragments[target_index] = deepcopy(repaired_fragment)
    return merged
