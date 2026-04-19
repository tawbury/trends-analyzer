from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.core import (
    MarketSignal,
    StockSignal,
    ThemeSignal,
    TrendSnapshot,
)
from src.contracts.payloads import (
    GenericInsightPayload,
    QTSInputPayload,
    WorkflowTriggerPayload,
)
from src.contracts.runtime import AnalyzeDailyResult


class JsonlSnapshotRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, snapshot: TrendSnapshot) -> None:
        _append_jsonl(self.path, _to_jsonable(snapshot))

    async def get(self, snapshot_id: str) -> TrendSnapshot | None:
        item = _find_latest_by_id(self.path, snapshot_id)
        if item is None:
            return None
        return _snapshot_from_dict(item)

    async def get_latest(self) -> TrendSnapshot | None:
        item = _find_latest(self.path)
        if item is None:
            return None
        return _snapshot_from_dict(item)


class JsonlQtsPayloadRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, payload: QTSInputPayload) -> None:
        _append_jsonl(self.path, _to_jsonable(payload))

    async def get(self, payload_id: str) -> QTSInputPayload | None:
        item = _find_latest_by_id(self.path, payload_id)
        if item is None:
            return None
        return _qts_payload_from_dict(item)

    async def get_latest(self, snapshot_id: str | None = None) -> QTSInputPayload | None:
        item = _find_latest(self.path, snapshot_id=snapshot_id)
        if item is None:
            return None
        return _qts_payload_from_dict(item)


class JsonlGenericPayloadRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, payload: GenericInsightPayload) -> None:
        _append_jsonl(self.path, _to_jsonable(payload))

    async def get(self, payload_id: str) -> GenericInsightPayload | None:
        item = _find_latest_by_id(self.path, payload_id)
        if item is None:
            return None
        return _generic_payload_from_dict(item)

    async def get_latest(self, snapshot_id: str | None = None) -> GenericInsightPayload | None:
        item = _find_latest(self.path, snapshot_id=snapshot_id)
        if item is None:
            return None
        return _generic_payload_from_dict(item)


class JsonlWorkflowPayloadRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, payload: WorkflowTriggerPayload) -> None:
        _append_jsonl(self.path, _to_jsonable(payload))

    async def get(self, payload_id: str) -> WorkflowTriggerPayload | None:
        item = _find_latest_by_id(self.path, payload_id)
        if item is None:
            return None
        return _workflow_payload_from_dict(item)

    async def get_latest(self, snapshot_id: str | None = None) -> WorkflowTriggerPayload | None:
        item = _find_latest(self.path, snapshot_id=snapshot_id)
        if item is None:
            return None
        return _workflow_payload_from_dict(item)


class JsonlIdempotencyRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, request_hash: str, result: AnalyzeDailyResult) -> None:
        _append_jsonl(
            self.path,
            {
                "id": key,
                "key": key,
                "request_hash": request_hash,
                "result": _to_jsonable(result),
                "created_at": datetime.now().isoformat(),
            },
        )

    async def get(self, key: str) -> tuple[str, AnalyzeDailyResult] | None:
        item = _find_latest_by_id(self.path, key)
        if item is None:
            return None
        return item["request_hash"], AnalyzeDailyResult(**item["result"])


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        file.write("\n")


def _find_latest_by_id(path: Path, item_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    found: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("id") == item_id:
                found = item
    return found


def _find_latest(path: Path, snapshot_id: str | None = None) -> dict[str, Any] | None:
    if not path.exists():
        return None
    found: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            if snapshot_id:
                if item.get("snapshot_id") == snapshot_id:
                    found = item
            else:
                found = item
    return found


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _snapshot_from_dict(item: dict[str, Any]) -> TrendSnapshot:
    return TrendSnapshot(
        id=item["id"],
        as_of=datetime.fromisoformat(item["as_of"]),
        window_start=datetime.fromisoformat(item["window_start"]),
        window_end=datetime.fromisoformat(item["window_end"]),
        market_signals=[
            MarketSignal(
                **{
                    **signal,
                    "generated_at": datetime.fromisoformat(signal["generated_at"]),
                }
            )
            for signal in item["market_signals"]
        ],
        theme_signals=[
            ThemeSignal(
                **{
                    **signal,
                    "generated_at": datetime.fromisoformat(signal["generated_at"]),
                }
            )
            for signal in item["theme_signals"]
        ],
        stock_signals=[
            StockSignal(
                **{
                    **signal,
                    "generated_at": datetime.fromisoformat(signal["generated_at"]),
                }
            )
            for signal in item["stock_signals"]
        ],
        evaluation_count=item["evaluation_count"],
        rules_version=item["rules_version"],
        created_at=datetime.fromisoformat(item["created_at"]),
    )


def _qts_payload_from_dict(item: dict[str, Any]) -> QTSInputPayload:
    return QTSInputPayload(
        id=item["id"],
        snapshot_id=item["snapshot_id"],
        market_bias=item["market_bias"],
        universe_adjustments=item["universe_adjustments"],
        risk_overrides=item["risk_overrides"],
        sector_weights=item["sector_weights"],
        strategy_activation_hints=item["strategy_activation_hints"],
        confidence_score=item["confidence_score"],
        generated_at=datetime.fromisoformat(item["generated_at"]),
        adapter_version=item["adapter_version"],
    )


def _generic_payload_from_dict(item: dict[str, Any]) -> GenericInsightPayload:
    return GenericInsightPayload(
        id=item["id"],
        snapshot_id=item["snapshot_id"],
        daily_briefing=item["daily_briefing"],
        theme_ranking=item["theme_ranking"],
        watchlist_candidates=item["watchlist_candidates"],
        alert_summary=item["alert_summary"],
        report_seed=item["report_seed"],
        generated_at=datetime.fromisoformat(item["generated_at"]),
    )


def _workflow_payload_from_dict(item: dict[str, Any]) -> WorkflowTriggerPayload:
    return WorkflowTriggerPayload(
        id=item["id"],
        snapshot_id=item["snapshot_id"],
        trigger_type=item["trigger_type"],
        priority=item["priority"],
        recommended_actions=item["recommended_actions"],
        routing_conditions=item["routing_conditions"],
        downstream_payload=item["downstream_payload"],
        dispatch_policy=item["dispatch_policy"],
        generated_at=datetime.fromisoformat(item["generated_at"]),
    )
