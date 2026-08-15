"""Legacy Infernal Exegate input schema, retained as a standalone adapter contract."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class LegacyModel(BaseModel):
    model_config=ConfigDict(extra="ignore")

class SymbolItem(LegacyModel):
    source_analysis_id: str | None=None; bundle_id: str | None=None; name: str
    literal: str | None=None; occult: str | None=None; psychological: str | None=None
    lv_hook: str | None=None; metadata_raw: str | None=None; intensity: int | None=None
    texture: str | None=None; phase: str | None=None

class RitualItem(LegacyModel):
    source_analysis_id: str | None=None; bundle_id: str | None=None; name: str
    type: str | None=None; description: str | None=None; intensity: int | None=None
    phase: str | None=None; texture: str | None=None; placement: str | None=None
    alexius_resonance: str | None=None

class SeedLineItem(LegacyModel):
    source_analysis_id: str | None=None; bundle_id: str | None=None; seed_line: str
    intensity: int | None=None; texture: str | None=None; phase: str | None=None
    voice: str | None=None; use: str | None=None; lexicon: list[str]=Field(default_factory=list)

class SceneHookItem(LegacyModel):
    source_analysis_id: str | None=None; bundle_id: str | None=None; hook_text_raw: str
    hook_title: str | None=None; hook_type: str | None=None; phase: str | None=None; texture: str | None=None

class VectorItem(LegacyModel):
    source_analysis_id: str | None=None; bundle_id: str | None=None; name: str; description: str | None=None

class ExegateRun(LegacyModel):
    song_title: str | None=None; analysis_mode: str | None=None; prima_materia_raw: str | None=None
    vectors_raw: str | None=None; vectors: list[VectorItem]=Field(default_factory=list)
    symbols: list[SymbolItem]=Field(default_factory=list); psych_pathology_raw: str | None=None
    rituals: list[RitualItem]=Field(default_factory=list); atmospherics_raw: str | None=None
    scene_hooks: list[SceneHookItem]=Field(default_factory=list); seed_lines: list[SeedLineItem]=Field(default_factory=list)
    metadata_raw: str | None=None; naming_ids_raw: str | None=None
