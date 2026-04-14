from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SymbolRecord:
    symbol: str
    name: str
    market: str
    security_type: str = "stock"
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SymbolCatalog:
    id: str
    as_of: datetime
    source: str
    records: list[SymbolRecord]
    generated_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return [record.symbol for record in self.records]
