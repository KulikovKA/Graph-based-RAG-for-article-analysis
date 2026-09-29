"""Простые детерминированные функции скрытия данных в структурированных логах."""

import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE_KEY = re.compile(r"password|secret|token|cookie|authorization|api[_-]?key|prompt", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")


def redact(value: Any) -> Any:
    """Скрыть секретные поля и токены, не записывая тело запроса в лог."""
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
