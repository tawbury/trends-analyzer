from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.symbols import SymbolCatalog, SymbolRecord


class JsonSymbolCatalogRepository:
    def __init__(self, *, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    async def save(self, catalog: SymbolCatalog) -> None:
        payload = _to_jsonable(catalog)
        dated_path = self.directory / f"{catalog.as_of:%Y%m%d}_symbol_catalog.json"
        latest_path = self.directory / "latest_symbol_catalog.json"
        for path in (dated_path, latest_path):
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    async def get_latest(self) -> SymbolCatalog | None:
        path = self.directory / "latest_symbol_catalog.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _catalog_from_dict(payload)


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


def _catalog_from_dict(payload: dict[str, Any]) -> SymbolCatalog:
    return SymbolCatalog(
        id=payload["id"],
        as_of=datetime.fromisoformat(payload["as_of"]),
        source=payload["source"],
        records=[SymbolRecord(**record) for record in payload["records"]],
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        metadata=payload.get("metadata", {}),
    )
