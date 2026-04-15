from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ingestion.discovery.calibration import DiscoveryCalibrationSummary
from src.ingestion.discovery.review import DiscoveryReviewItem


class JsonDiscoveryReviewRepository:
    def __init__(self, *, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save_review_sync(
        self,
        *,
        provider: str,
        generated_at: datetime,
        review_items: list[DiscoveryReviewItem],
        calibration_summary: DiscoveryCalibrationSummary,
    ) -> None:
        payload = {
            "provider": provider,
            "generated_at": generated_at.isoformat(),
            "items": [_to_jsonable(item) for item in review_items],
            "calibration_summary": _to_jsonable(calibration_summary),
        }
        dated_path = self.directory / f"{generated_at:%Y%m%d_%H%M%S}_{provider}_review.json"
        latest_path = self.directory / f"latest_{provider}_review.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, payload)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)
