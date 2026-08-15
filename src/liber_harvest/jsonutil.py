"""Model-response JSON extraction utilities."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


class ModelResponseError(ValueError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse one JSON object from a model response without accepting prose wrappers."""
    candidate = text.strip()
    match = _FENCE_RE.fullmatch(candidate)
    if match:
        candidate = match.group(1).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ModelResponseError(f"Model response is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ModelResponseError("Model response must be one JSON object")
    return value
