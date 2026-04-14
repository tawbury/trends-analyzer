from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import count
from uuid import uuid4

from src.adapters.qts.adapter import QtsAdapter
from src.application.use_cases.refresh_symbol_catalog import RefreshSymbolCatalogUseCase
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.ports import (
    IdempotencyRepository,
    NewsSourcePort,
    QtsPayloadRepository,
    SnapshotRepository,
)
from src.contracts.runtime import CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import MockNewsScorer
from src.db.repositories.jsonl import (
    JsonlIdempotencyRepository,
    JsonlQtsPayloadRepository,
    JsonlSnapshotRepository,
)
from src.db.repositories.symbol_catalog_repository import JsonSymbolCatalogRepository
from src.ingestion.catalog.json_artifact_loader import JsonArtifactSymbolCatalogSource
from src.ingestion.catalog.kis_stock_code_source import KisStockCodeCatalogSource
from src.ingestion.catalog.selection import SymbolSelectionPolicy, select_source_symbols
from src.ingestion.clients.http import JsonHttpClient
from src.ingestion.clients.kis_client import KisClient
from src.ingestion.clients.kiwoom_client import KiwoomClient
from src.ingestion.loaders.composite import CompositeNewsSource
from src.ingestion.loaders.kis_loader import KisMarketDataSource
from src.ingestion.loaders.kiwoom_loader import KiwoomStockInfoSource
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource
from src.shared.config import Settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    snapshot_repository: SnapshotRepository
    qts_payload_repository: QtsPayloadRepository
    idempotency_repository: IdempotencyRepository
    news_source: NewsSourcePort
    analyze_daily_use_case: AnalyzeDailyTrendsUseCase
    refresh_symbol_catalog_use_case: RefreshSymbolCatalogUseCase


_job_sequence = count(start=1)


def build_container(settings: Settings | None = None) -> Container:
    resolved_settings = settings or Settings.from_env()
    data_dir = resolved_settings.data_dir
    snapshot_repository = JsonlSnapshotRepository(data_dir / "snapshots.jsonl")
    qts_payload_repository = JsonlQtsPayloadRepository(data_dir / "qts_payloads.jsonl")
    idempotency_repository = JsonlIdempotencyRepository(data_dir / "idempotency.jsonl")
    symbol_catalog_repository = JsonSymbolCatalogRepository(
        directory=data_dir / "symbol_catalog",
    )
    news_source = build_news_source(
        resolved_settings,
        symbol_catalog_repository=symbol_catalog_repository,
    )
    symbol_catalog_source = build_symbol_catalog_source(resolved_settings)

    use_case = AnalyzeDailyTrendsUseCase(
        news_source=news_source,
        normalizer=NewsNormalizer(),
        scorer=MockNewsScorer(),
        aggregator=TrendAggregator(),
        qts_adapter=QtsAdapter(),
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        rules_version=resolved_settings.rules_version,
    )
    refresh_symbol_catalog_use_case = RefreshSymbolCatalogUseCase(
        source=symbol_catalog_source,
        repository=symbol_catalog_repository,
    )
    return Container(
        settings=resolved_settings,
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        idempotency_repository=idempotency_repository,
        news_source=news_source,
        analyze_daily_use_case=use_case,
        refresh_symbol_catalog_use_case=refresh_symbol_catalog_use_case,
    )


def build_news_source(
    settings: Settings,
    *,
    symbol_catalog_repository: JsonSymbolCatalogRepository | None = None,
) -> NewsSourcePort:
    active_sources = settings.active_sources or ["fixture"]
    symbols = resolve_source_symbols(
        settings,
        symbol_catalog_repository=symbol_catalog_repository,
    )
    http = JsonHttpClient(timeout_seconds=settings.source_timeout_seconds)
    sources = []

    for source_name in active_sources:
        normalized = source_name.strip().lower()
        if normalized == "fixture":
            sources.append(LocalFixtureNewsSource())
        elif normalized == "kis":
            sources.append(
                KisMarketDataSource(
                    client=KisClient(
                        base_url=settings.kis_base_url,
                        app_key=settings.kis_app_key,
                        app_secret=settings.kis_app_secret,
                        market_division_code=settings.kis_market_division_code,
                        quote_tr_id=settings.kis_tr_id_quote,
                        invest_opinion_tr_id=settings.kis_tr_id_invest_opinion,
                        http=http,
                        token_cache_path=settings.data_dir / "kis_token.json",
                    ),
                    symbols=symbols,
                    invest_opinion_lookback_days=settings.kis_invest_opinion_lookback_days,
                    invest_opinion_limit_per_symbol=settings.kis_invest_opinion_limit_per_symbol,
                )
            )
        elif normalized == "kiwoom":
            sources.append(
                KiwoomStockInfoSource(
                    client=KiwoomClient(
                        mode=settings.kiwoom_mode,
                        base_url=settings.kiwoom_base_url,
                        app_key=settings.kiwoom_app_key,
                        app_secret=settings.kiwoom_app_secret,
                        account_no=settings.kiwoom_account_no,
                        account_product_code=settings.kiwoom_account_product_code,
                        stock_info_path=settings.kiwoom_stock_info_path,
                        http=http,
                        token_cache_path=settings.data_dir / "kiwoom_token.json",
                    ),
                    symbols=symbols,
                )
            )
        else:
            raise ValueError(f"Unsupported source configured: {source_name}")

    return CompositeNewsSource(
        sources=sources,
        partial_success=settings.source_partial_success,
    )


def resolve_source_symbols(
    settings: Settings,
    *,
    symbol_catalog_repository: JsonSymbolCatalogRepository | None = None,
) -> list[str]:
    catalog = None
    if symbol_catalog_repository is not None:
        catalog = symbol_catalog_repository.get_latest_sync()
    return select_source_symbols(
        policy=SymbolSelectionPolicy(
            mode=settings.source_symbol_policy,
            explicit_symbols=settings.source_symbols or ["005930", "000660"],
            markets=settings.source_symbol_markets or [],
            classifications=settings.source_symbol_classifications or [],
            limit=settings.source_symbol_limit,
            valid_code_only=settings.source_symbol_valid_code_only,
        ),
        catalog=catalog,
    )


def build_symbol_catalog_source(settings: Settings):
    source_name = settings.symbol_catalog_source.strip().lower()
    if source_name == "json_artifact":
        if not settings.symbol_catalog_path:
            raise ValueError("TRENDS_SYMBOL_CATALOG_PATH is required for json_artifact source")
        from pathlib import Path

        return JsonArtifactSymbolCatalogSource(path=Path(settings.symbol_catalog_path))
    if source_name in {"kis_master", "kis_csv"}:
        return KisStockCodeCatalogSource(
            url=settings.symbol_catalog_url,
            allowed_markets=settings.symbol_catalog_markets or ["KOSPI", "KOSDAQ", "KONEX"],
            timeout_seconds=settings.source_timeout_seconds,
        )
    raise ValueError(f"Unsupported symbol catalog source: {settings.symbol_catalog_source}")


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container()


def build_correlation_context(
    *,
    requested_by: str,
    correlation_id: str | None = None,
    job_prefix: str = "job_mvp_daily",
) -> CorrelationContext:
    sequence = next(_job_sequence)
    return CorrelationContext(
        correlation_id=correlation_id or f"corr_{uuid4().hex[:12]}",
        job_id=f"{job_prefix}_{sequence:04d}",
        requested_by=requested_by,
    )
