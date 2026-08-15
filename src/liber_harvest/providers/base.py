"""Provider abstraction for semantic extraction."""
from __future__ import annotations
from typing import Any, Protocol
from ..models import HarvestInputEnvelope

class ExtractionProvider(Protocol):
    def extract(self, envelope: HarvestInputEnvelope) -> dict[str, Any]: ...
    def repair(self, candidate: dict[str, Any], validation_errors: str, envelope: HarvestInputEnvelope) -> dict[str, Any]: ...
