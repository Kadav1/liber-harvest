"""RFC 6901 JSON Pointer helpers."""

from __future__ import annotations

import re
from typing import Any

_POINTER_RE = re.compile(r"^(?:/(?:[^~/]|~[01])*)+$")


class JsonPointerError(ValueError):
    """Raised when a JSON Pointer is invalid or cannot be resolved."""


def is_valid_json_pointer(pointer: str) -> bool:
    return bool(pointer and _POINTER_RE.fullmatch(pointer))


def _decode_token(token: str) -> str:
    # RFC 6901 requires ~1 first, then ~0.
    return token.replace("~1", "/").replace("~0", "~")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if not is_valid_json_pointer(pointer):
        raise JsonPointerError(f"Invalid RFC 6901 JSON Pointer: {pointer!r}")
    current = document
    for raw in pointer.split("/")[1:]:
        token = _decode_token(raw)
        if isinstance(current, dict):
            if token not in current:
                raise JsonPointerError(f"Pointer segment {token!r} not found in {pointer!r}")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token.isdigit():
                raise JsonPointerError(f"Invalid list index {token!r} in {pointer!r}")
            if len(token) > 1 and token.startswith("0"):
                raise JsonPointerError(f"Array index must not contain a leading zero: {token!r}")
            index = int(token)
            if index >= len(current):
                raise JsonPointerError(f"List index {index} out of range in {pointer!r}")
            current = current[index]
        else:
            raise JsonPointerError(
                f"Cannot traverse segment {token!r}; target is {type(current).__name__}"
            )
    return current
