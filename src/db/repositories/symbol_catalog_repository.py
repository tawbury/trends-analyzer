from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.symbols import (
    SymbolCatalog,
    SymbolCatalogValidationReport,
    SymbolRecord,
    SymbolSelectionReport,
)


class JsonSymbolCatalogRepository:
    def __init__(self, *, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    async def save(self, catalog: SymbolCatalog) -> None:
        payload = _to_jsonable(catalog)
        dated_path = self.directory / f"{catalog.as_of:%Y%m%d}_symbol_catalog.json"
        latest_path = self.directory / "latest_symbol_catalog.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, payload)

    async def get_latest(self) -> SymbolCatalog | None:
        return self.get_latest_sync()

    def get_latest_sync(self) -> SymbolCatalog | None:
        path = self.directory / "latest_symbol_catalog.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _catalog_from_dict(payload)

    async def save_validation_report(self, report: SymbolCatalogValidationReport) -> None:
        payload = _to_jsonable(report)
        dated_path = self.directory / f"{report.generated_at:%Y%m%d}_symbol_catalog_validation.json"
        latest_path = self.directory / "latest_symbol_catalog_validation.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, payload)

    async def save_selection_report(self, report: SymbolSelectionReport) -> None:
        self.save_selection_report_sync(report)

    def save_selection_report_sync(self, report: SymbolSelectionReport) -> None:
        payload = _to_jsonable(report)
        latest_path = self.directory / "latest_source_symbol_selection.json"
        dated_path = self.directory / f"{report.generated_at:%Y%m%d}_source_symbol_selection.json"
        for path in (dated_path, latest_path):
            _write_json_atomic(path, payload)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
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


def _catalog_from_dict(payload: dict[str, Any]) -> SymbolCatalog:
    return SymbolCatalog(
        id=payload["id"],
        as_of=datetime.fromisoformat(payload["as_of"]),
        source=payload["source"],
        records=[_record_from_dict(record) for record in payload["records"]],
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        metadata=payload.get("metadata", {}),
    )


def _record_from_dict(payload: dict[str, Any]) -> SymbolRecord:
    return SymbolRecord(
        symbol=payload["symbol"],
        name=payload["name"],
        market=payload["market"],
        security_type=payload.get("security_type", "stock"),
        korean_name=payload.get("korean_name", ""),
        english_name=payload.get("english_name", ""),
        normalized_name=payload.get("normalized_name", ""),
        aliases=payload.get("aliases", []),
        query_keywords=payload.get("query_keywords", []),
        metadata=payload.get("metadata", {}),
    )
