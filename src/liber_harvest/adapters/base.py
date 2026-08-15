"""Source-adapter protocol."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from ..models import HarvestInputEnvelope

@dataclass(frozen=True)
class LoadedSource:
    actual_path: Path
    envelope: HarvestInputEnvelope
    document: dict[str, Any]
    bundle_id: str | None = None

class SourceAdapter(Protocol):
    pipeline: str
    def load(self, path: Path) -> LoadedSource: ...
