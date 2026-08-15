"""Deterministic LF-13 provenance materialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .models import (
    ProvenanceAnchor, ProvenanceDraft, ProvenancePrecision, ReviewReason, SourceSpan,
)
from .pointers import resolve_json_pointer


@dataclass(frozen=True)
class MaterializedAnchor:
    anchor: ProvenanceAnchor
    review_reasons: tuple[ReviewReason, ...] = ()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_pointer_value(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(raw)


def _occurrences(haystack: str, needle: str) -> list[int]:
    if not needle:
        return []
    positions: list[int] = []
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return positions
        positions.append(index)
        start = index + 1


def materialize_provenance_anchor(
    draft: ProvenanceDraft,
    source_document: dict[str, Any],
) -> MaterializedAnchor:
    target = resolve_json_pointer(source_document, draft.json_pointer)
    if not isinstance(target, str):
        raise ValueError(
            f"Lore provenance pointer must resolve to textual evidence: {draft.json_pointer}"
        )
    anchor_sha = hash_pointer_value(target)
    reasons: list[ReviewReason] = []

    precision = ProvenancePrecision.ITEM
    source_span = None

    if draft.excerpt == target:
        precision = ProvenancePrecision.ITEM
    else:
        positions = _occurrences(target, draft.excerpt)
        if len(positions) == 1:
            start = positions[0]
            end = start + len(draft.excerpt)
            precision = ProvenancePrecision.SPAN
            source_span = SourceSpan(
                unit="char",
                start=start,
                end=end,
                text_sha256=sha256_text(target[start:end]),
            )
        elif len(positions) > 1:
            precision = ProvenancePrecision.FIELD
            reasons.append(ReviewReason.PROVENANCE_SPAN_AMBIGUOUS)
        else:
            precision = ProvenancePrecision.FIELD
            reasons.append(ReviewReason.PROVENANCE_EXCERPT_UNRESOLVED)

    anchor = ProvenanceAnchor(
        **draft.model_dump(),
        precision=precision,
        source_span=source_span,
        anchor_sha256=anchor_sha,
    )
    return MaterializedAnchor(anchor=anchor, review_reasons=tuple(reasons))
