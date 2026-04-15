from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ingestion.discovery.human_review import (
    HumanReviewFeedback,
    build_human_review_report,
    human_review_feedback_from_dict,
    human_review_feedback_to_dict,
)


class JsonlDiscoveryHumanReviewRepository:
    def __init__(self, *, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def append_feedback_sync(
        self,
        *,
        provider: str,
        feedback: HumanReviewFeedback,
    ) -> None:
        path = self._feedback_path(provider)
        with path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    human_review_feedback_to_dict(feedback),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            file.write("\n")

    def list_feedback_sync(self, *, provider: str) -> list[HumanReviewFeedback]:
        path = self._feedback_path(provider)
        if not path.exists():
            return []
        feedback_items: list[HumanReviewFeedback] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                feedback_items.append(human_review_feedback_from_dict(payload))
        return feedback_items

    def save_report_sync(
        self,
        *,
        provider: str,
        generated_at: datetime,
        review_payload: dict[str, Any],
        feedback_items: list[HumanReviewFeedback] | None = None,
    ) -> dict[str, Any]:
        resolved_feedback = (
            feedback_items
            if feedback_items is not None
            else self.list_feedback_sync(provider=provider)
        )
        report = build_human_review_report(
            provider=provider,
            generated_at=generated_at,
            review_payload=review_payload,
            feedback_items=resolved_feedback,
        )
        dated_path = self.directory / f"{generated_at:%Y%m%d_%H%M%S}_{provider}_human_review_report.json"
        latest_path = self.directory / f"latest_{provider}_human_review_report.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, report)
        return report

    def _feedback_path(self, provider: str) -> Path:
        return self.directory / f"{provider}_human_feedback.jsonl"


def load_review_artifact(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Review artifact must be a JSON object: {path}")
    return payload


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
