"""Deterministic Lore Fragment and relation identity generation."""

from __future__ import annotations

import hashlib
import json

from .constants import FRAGMENT_SCHEMA_VERSION, RELATION_SCHEMA_VERSION, TYPE_CODES
from .models import LoreFragmentDraft, ProvenanceAnchor, RelationType


def _digest(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()


def fragment_id(fragment: LoreFragmentDraft, provenance: list[ProvenanceAnchor]) -> str:
    sources = sorted({(p.source_path, p.source_sha256) for p in provenance})
    pointers = sorted({p.json_pointer for p in provenance})
    identity = {
        "schema_version": FRAGMENT_SCHEMA_VERSION,
        "sources": sources,
        "json_pointers": pointers,
        "concept_key": fragment.concept_key,
        "type": fragment.type.value,
    }
    code = TYPE_CODES[fragment.type.value]
    return f"LFR-{code}-{_digest(identity)[:12]}"


def relation_id(relation: RelationType, source_fragment_id: str, target_fragment_id: str) -> str:
    identity = {
        "schema_version": RELATION_SCHEMA_VERSION,
        "relation": relation.value,
        "source_fragment_id": source_fragment_id,
        "target_fragment_id": target_fragment_id,
    }
    return f"LRL-{_digest(identity)[:12]}"
