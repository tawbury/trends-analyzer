from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ingestion.discovery.calibration import DiscoveryCalibrationSummary
from src.ingestion.discovery.calibration_compare import build_calibration_comparison
from src.ingestion.discovery.experiment import DiscoveryExperimentMetadata
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
        experiment_metadata: DiscoveryExperimentMetadata | None = None,
    ) -> None:
        latest_path = self.directory / f"latest_{provider}_review.json"
        previous_payload = _read_json(latest_path)
        payload = {
            "provider": provider,
            "generated_at": generated_at.isoformat(),
            "experiment_metadata": _to_jsonable(experiment_metadata)
            if experiment_metadata is not None
            else _fallback_experiment_metadata(
                provider=provider,
                generated_at=generated_at,
            ),
            "items": [_to_jsonable(item) for item in review_items],
            "calibration_summary": _to_jsonable(calibration_summary),
        }
        comparison_payload = build_calibration_comparison(
            provider=provider,
            generated_at=generated_at.isoformat(),
            current_payload=payload,
            previous_payload=previous_payload,
        )
        dated_path = self.directory / f"{generated_at:%Y%m%d_%H%M%S}_{provider}_review.json"
        dated_comparison_path = (
            self.directory / f"{generated_at:%Y%m%d_%H%M%S}_{provider}_calibration_compare.json"
        )
        latest_comparison_path = self.directory / f"latest_{provider}_calibration_compare.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, payload)
        for path in (dated_comparison_path, latest_comparison_path):
            _write_json_atomic(path, comparison_payload)


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


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _fallback_experiment_metadata(
    *,
    provider: str,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "generated_at": generated_at.isoformat(),
        "provider": provider,
        "rule_config_path": "unknown",
        "rule_config_fingerprint": "unknown",
        "active_source_symbol_policy": "unknown",
        "selected_symbol_count": 0,
        "query_count": 0,
    }
