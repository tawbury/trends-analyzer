from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def metadata_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def provider_metadata(provider: str, response: dict[str, Any]) -> dict[str, str]:
    return {
        "provider": provider,
        "provider_payload": metadata_value(response),
    }


def compact_text(*parts: object) -> str:
    return " ".join(str(part).strip() for part in parts if str(part).strip())


def parse_provider_datetime(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return fallback
    cleaned = value.strip()
    for pattern in ("%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(cleaned, pattern).replace(tzinfo=fallback.tzinfo)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return fallback


def normalize_numeric_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"^[+-]+", "", text)
