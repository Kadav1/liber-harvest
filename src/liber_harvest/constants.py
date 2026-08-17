"""Frozen Lore Harvest v0.1.2 controlled vocabularies and constants."""

from __future__ import annotations

CONTRACT_VERSION = "exegate-harvest/0.1.2"
FRAGMENT_SCHEMA_VERSION = "lore-fragment/0.1.2"
RELATION_SCHEMA_VERSION = "lore-relation/0.1.2"
MANIFEST_VERSION = "lore-harvest-manifest/0.1.2"
EXTRACTOR_VERSION = "0.1.4"

TYPE_CODES: dict[str, str] = {
    "person": "PER", "group": "GRP", "institution": "INS", "office": "OFF",
    "place": "PLC", "structure": "STR", "architecture": "ARC", "object": "OBJ",
    "relic": "REL", "material": "MAT", "flora": "FLO", "creature": "CRE",
    "ritual": "RIT", "custom": "CUS", "practice": "PRA", "law": "LAW",
    "social_structure": "SOC", "economy": "ECO", "trade": "TRD", "warfare": "WAR",
    "doctrine": "DOC", "belief": "BEL", "cosmology": "COS", "myth": "MYT",
    "legend": "LEG", "symbol": "SYM", "event": "EVT", "historical_claim": "HIS",
    "somatic": "SOM", "pathology": "PAT", "medicine": "MED", "environment": "ENV",
    "language": "LAN", "name": "NAM", "phrase": "PHR", "motif": "MOT",
    "sensory_palette": "SEN", "narrative_hook": "NAR", "character_hook": "CHR",
    "other": "OTH",
}

DOMAINS = frozenset({
    "religion", "cosmology", "ritual", "institution", "politics", "law", "society",
    "family", "economy", "trade", "warfare", "architecture", "material_culture",
    "environment", "agriculture", "food", "medicine", "body", "death", "burial",
    "history", "myth", "folklore", "language", "naming", "magic", "travel",
    "infrastructure", "art", "music", "literature", "psychology",
})

PRIMARY_EXEGATE_FIELDS = (
    "prima_materia_raw", "vectors", "vectors_raw", "symbols", "psych_pathology_raw",
    "rituals", "atmospherics_raw", "scene_hooks", "seed_lines", "metadata_raw",
    "naming_ids_raw",
)

FIELD_TO_CIRCLE = {
    "prima_materia_raw": "prima_materia",
    "vectors": "vectors_of_corruption",
    "vectors_raw": "vectors_of_corruption",
    "symbols": "symbols",
    "psych_pathology_raw": "psychological_pathology",
    "rituals": "ritual_extraction",
    "atmospherics_raw": "atmospherics_texture",
    "scene_hooks": "narrative_potential",
    "seed_lines": "seed_line_distillation",
    "metadata_raw": "metadata_assessment",
    "naming_ids_raw": "naming_ids",
}

PIPELINE_WRAPPER_MARKERS = (
    "lore architect", "codex mapper", "page drafter", "the exegete", "exegete could",
)
