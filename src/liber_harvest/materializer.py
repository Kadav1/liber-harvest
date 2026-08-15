"""Turn validated model drafts into deterministic Lore Fragment records."""

from __future__ import annotations

from .constants import CONTRACT_VERSION, EXTRACTOR_VERSION, FRAGMENT_SCHEMA_VERSION
from .identity import fragment_id
from .models import (
    HarvestMeta, LoreFragmentDraft, LoreFragmentRecord, Review, ReviewReason,
)
from .provenance import materialize_provenance_anchor


def materialize_fragment(
    draft: LoreFragmentDraft,
    *,
    source_document: dict,
    run_id: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> LoreFragmentRecord:
    materialized = [
        materialize_provenance_anchor(anchor, source_document)
        for anchor in draft.provenance
    ]
    anchors = [item.anchor for item in materialized]

    added_reasons: list[ReviewReason] = []
    for item in materialized:
        for reason in item.review_reasons:
            if reason not in added_reasons:
                added_reasons.append(reason)

    reasons = list(draft.review.reasons)
    for reason in added_reasons:
        if reason not in reasons:
            reasons.append(reason)
    review = Review(required=bool(reasons) or draft.review.required, reasons=reasons)

    fid = fragment_id(draft, anchors)
    payload = draft.model_dump(exclude={"provenance", "review"})
    return LoreFragmentRecord(
        schema_version=FRAGMENT_SCHEMA_VERSION,
        fragment_id=fid,
        **payload,
        provenance=anchors,
        review=review,
        harvest=HarvestMeta(
            contract_version=CONTRACT_VERSION,
            extractor_version=extractor_version,
            run_id=run_id,
        ),
    )
