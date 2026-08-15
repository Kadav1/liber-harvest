"""Deterministic provider for offline materialization and regression tests."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..models import HarvestInputEnvelope

class StaticProvider:
    def __init__(self, result: dict[str, Any]):
        self.result = result

    @classmethod
    def from_file(cls, path: Path) -> "StaticProvider":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Static harvest response must be one JSON object")
        return cls(data)

    def extract(self, envelope: HarvestInputEnvelope) -> dict[str, Any]:
        del envelope
        return self.result

    def repair(self, candidate: dict[str, Any], validation_errors: str, envelope: HarvestInputEnvelope) -> dict[str, Any]:
        del validation_errors, envelope
        return candidate
