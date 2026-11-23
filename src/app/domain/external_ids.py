"""Канонические идентификаторы публичных документов."""

import re


def canonical_external_id(source: str, external_id: str) -> str:
    """Вернуть стабильный внешний ключ для поддерживаемых источников."""
    value = external_id.strip()
    if source == "epo_ops":
        value = re.sub(r"[\s.]", "", value).upper()
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]+[A-Z][0-9]?", value):
            raise ValueError("invalid EPO publication ID")
        return value
    if source == "openalex":
        value = value.rsplit("/", 1)[-1].upper()
        if not re.fullmatch(r"W[0-9]+", value):
            raise ValueError("invalid OpenAlex work ID")
        return value
    raise ValueError("unsupported source")
