from __future__ import annotations

from collections import Counter
from datetime import datetime
import re

from src.contracts.symbols import (
    SymbolCatalog,
    SymbolCatalogValidationReport,
    SymbolRecord,
    SymbolValidationIssue,
)


_SYMBOL_RE = re.compile(r"^\d{6}$")


def validate_symbol_catalog(
    catalog: SymbolCatalog,
    *,
    generated_at: datetime,
) -> SymbolCatalogValidationReport:
    symbol_counts = Counter(record.symbol for record in catalog.records)
    name_counts = Counter(record.normalized_name or record.name for record in catalog.records)
    market_distribution = Counter(record.market or "UNKNOWN" for record in catalog.records)
    classification_distribution = Counter(
        record.metadata.get("classification", "unknown") for record in catalog.records
    )
    issues: list[SymbolValidationIssue] = []

    for record in catalog.records:
        issues.extend(_record_issues(record=record, symbol_counts=symbol_counts, name_counts=name_counts))

    return SymbolCatalogValidationReport(
        catalog_id=catalog.id,
        generated_at=generated_at,
        total_count=len(catalog.records),
        invalid_code_count=sum(1 for record in catalog.records if not _SYMBOL_RE.match(record.symbol)),
        duplicate_symbol_count=sum(count - 1 for count in symbol_counts.values() if count > 1),
        duplicate_name_count=sum(count - 1 for count in name_counts.values() if count > 1),
        missing_name_count=sum(1 for record in catalog.records if not record.name.strip()),
        market_distribution=dict(sorted(market_distribution.items())),
        classification_distribution=dict(sorted(classification_distribution.items())),
        suspicious_records=issues[:100],
    )


def _record_issues(
    *,
    record: SymbolRecord,
    symbol_counts: Counter[str],
    name_counts: Counter[str],
) -> list[SymbolValidationIssue]:
    issues: list[SymbolValidationIssue] = []
    normalized_name = record.normalized_name or record.name
    checks = [
        (not _SYMBOL_RE.match(record.symbol), "invalid_symbol_code", "symbol code is not 6 digits"),
        (not record.name.strip(), "missing_name", "symbol name is empty"),
        (len(record.name.strip()) < 2, "suspicious_name", "symbol name is too short"),
        (symbol_counts[record.symbol] > 1, "duplicate_symbol", "symbol code appears more than once"),
        (bool(normalized_name) and name_counts[normalized_name] > 1, "duplicate_name", "normalized name appears more than once"),
        (record.market == "UNKNOWN", "unknown_market", "market is unknown"),
        (not record.sector and not record.metadata.get("sector"), "missing_sector", "sector information is missing"),
    ]
    
    # Simple market-code prefix check (example for KOSPI/KOSDAQ)
    if record.market == "KOSPI" and record.symbol.startswith("0") and len(record.name) > 5:
         # Some KOSPI codes start with 0, but this is a placeholder for more complex logic
         pass
    for failed, code, message in checks:
        if failed:
            issues.append(
                SymbolValidationIssue(
                    severity="warning",
                    code=code,
                    symbol=record.symbol,
                    message=message,
                )
            )
    return issues
