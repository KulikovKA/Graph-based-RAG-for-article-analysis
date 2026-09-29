"""Small, deterministic redaction helpers for structured logs."""

import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE_KEY = re.compile(r"password|secret|token|cookie|authorization|api[_-]?key|prompt", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")


def redact(value: Any) -> Any:
    """Redact sensitive fields and bearer credentials without logging request bodies."""
    if isinstance(value, Mapping):
        return {key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _BEARER.sub("Bearer [REDACTED]", value)
    return value
