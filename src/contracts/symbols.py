from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SymbolRecord:
    symbol: str
    name: str
    market: str
    security_type: str = "stock"
    korean_name: str = ""
    english_name: str = ""
    normalized_name: str = ""
    aliases: list[str] = field(default_factory=list)
    query_keywords: list[str] = field(default_factory=list)
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


@dataclass(frozen=True)
class SymbolValidationIssue:
    severity: str
    code: str
    symbol: str
    message: str


@dataclass(frozen=True)
class SymbolCatalogValidationReport:
    catalog_id: str
    generated_at: datetime
    total_count: int
    invalid_code_count: int
    duplicate_symbol_count: int
    duplicate_name_count: int
    missing_name_count: int
    market_distribution: dict[str, int]
    classification_distribution: dict[str, int]
    suspicious_records: list[SymbolValidationIssue] = field(default_factory=list)
