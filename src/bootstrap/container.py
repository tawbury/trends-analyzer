from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from itertools import count
from uuid import uuid4

from src.adapters.qts.adapter import QtsAdapter
from src.adapters.generic.adapter import GenericAdapter
from src.adapters.workflow.adapter import WorkflowAdapter
from src.application.use_cases.refresh_symbol_catalog import RefreshSymbolCatalogUseCase
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.application.use_cases.get_signals import GetSignalsUseCase
from src.application.use_cases.ingest_news import IngestNewsUseCase
from src.contracts.ports import (
    GenericPayloadRepository,
    IdempotencyRepository,
    NewsSourcePort,
    QtsPayloadRepository,
    RawNewsRepository,
    SnapshotRepository,
    WorkflowPayloadRepository,
)
from src.contracts.runtime import CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import NewsScorer
from src.db.repositories.jsonl import (
    JsonlGenericPayloadRepository,
    JsonlIdempotencyRepository,
    JsonlQtsPayloadRepository,
    JsonlRawNewsRepository,
    JsonlSnapshotRepository,
    JsonlWorkflowPayloadRepository,
)
from src.db.repositories.discovery_review_repository import JsonDiscoveryReviewRepository
from src.db.repositories.symbol_catalog_repository import JsonSymbolCatalogRepository
from src.ingestion.catalog.json_artifact_loader import JsonArtifactSymbolCatalogSource
from src.ingestion.catalog.kis_stock_code_source import KisStockCodeCatalogSource
from src.ingestion.catalog.selection import (
    SymbolSelectionPolicy,
    build_symbol_selection_report,
)
from src.ingestion.clients.http import JsonHttpClient
from src.ingestion.clients.kis_client import KisClient
from src.ingestion.clients.kiwoom_client import KiwoomClient
from src.ingestion.clients.naver_news_client import NaverNewsClient
from src.ingestion.discovery.rules import load_discovery_rule_config
from src.ingestion.loaders.composite import CompositeNewsSource
from src.ingestion.loaders.kis_loader import KisMarketDataSource
from src.ingestion.loaders.kiwoom_loader import KiwoomStockInfoSource
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource
from src.ingestion.loaders.naver_news_loader import NaverNewsDiscoverySource
from src.shared.clock import now_kst
from src.shared.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Container:
    settings: Settings
    snapshot_repository: SnapshotRepository
    qts_payload_repository: QtsPayloadRepository
    generic_payload_repository: GenericPayloadRepository
    workflow_payload_repository: WorkflowPayloadRepository
    idempotency_repository: IdempotencyRepository
    raw_news_repository: RawNewsRepository
    news_source: NewsSourcePort
    analyze_daily_use_case: AnalyzeDailyTrendsUseCase
    refresh_symbol_catalog_use_case: RefreshSymbolCatalogUseCase
    get_signals_use_case: GetSignalsUseCase
    ingest_news_use_case: IngestNewsUseCase


_job_sequence = count(start=1)


def build_container(settings: Settings | None = None) -> Container:
    resolved_settings = settings or Settings.from_env()
    data_dir = resolved_settings.data_dir
    snapshot_repository = JsonlSnapshotRepository(data_dir / "snapshots.jsonl")
    qts_payload_repository = JsonlQtsPayloadRepository(data_dir / "qts_payloads.jsonl")
    generic_payload_repository = JsonlGenericPayloadRepository(data_dir / "generic_payloads.jsonl")
    workflow_payload_repository = JsonlWorkflowPayloadRepository(data_dir / "workflow_payloads.jsonl")
    idempotency_repository = JsonlIdempotencyRepository(data_dir / "idempotency.jsonl")
    raw_news_repository = JsonlRawNewsRepository(data_dir / "raw_news.jsonl")
    
    symbol_catalog_repository = JsonSymbolCatalogRepository(
        directory=data_dir / "symbol_catalog",
    )
    news_source = build_news_source(
        resolved_settings,
        symbol_catalog_repository=symbol_catalog_repository,
    )
    symbol_catalog_source = build_symbol_catalog_source(resolved_settings)

    analyze_daily_use_case = AnalyzeDailyTrendsUseCase(
        news_source=news_source,
        normalizer=NewsNormalizer(),
        scorer=NewsScorer(),
        aggregator=TrendAggregator(),
        qts_adapter=QtsAdapter(),
        generic_adapter=GenericAdapter(),
        workflow_adapter=WorkflowAdapter(),
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        generic_payload_repository=generic_payload_repository,
        workflow_payload_repository=workflow_payload_repository,
        rules_version=resolved_settings.rules_version,
    )
    refresh_symbol_catalog_use_case = RefreshSymbolCatalogUseCase(
        source=symbol_catalog_source,
        repository=symbol_catalog_repository,
    )
    get_signals_use_case = GetSignalsUseCase(snapshot_repository=snapshot_repository)
    ingest_news_use_case = IngestNewsUseCase(raw_news_repo=raw_news_repository)

    return Container(
        settings=resolved_settings,
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        generic_payload_repository=generic_payload_repository,
        workflow_payload_repository=workflow_payload_repository,
        idempotency_repository=idempotency_repository,
        raw_news_repository=raw_news_repository,
        news_source=news_source,
        analyze_daily_use_case=analyze_daily_use_case,
        refresh_symbol_catalog_use_case=refresh_symbol_catalog_use_case,
        get_signals_use_case=get_signals_use_case,
        ingest_news_use_case=ingest_news_use_case,
    )


def build_news_source(
    settings: Settings,
    *,
    symbol_catalog_repository: JsonSymbolCatalogRepository | None = None,
) -> NewsSourcePort:
    active_sources = settings.active_sources or ["fixture"]
    selection_report = resolve_source_symbol_selection(
        settings,
        symbol_catalog_repository=symbol_catalog_repository,
    )
    symbols = [record.symbol for record in selection_report.selected_records]
    symbol_records = selection_report.selected_records
    if symbol_catalog_repository is not None:
        symbol_catalog_repository.save_selection_report_sync(selection_report)
    _log_symbol_selection(selection_report)
    http = JsonHttpClient(timeout_seconds=settings.source_timeout_seconds)
    discovery_review_repository = (
        JsonDiscoveryReviewRepository(directory=settings.data_dir / "discovery_reviews")
        if settings.discovery_review_enabled
        else None
    )
    discovery_rules = load_discovery_rule_config(settings.discovery_rule_config_path)
    sources = []

    for source_name in active_sources:
        normalized = source_name.strip().lower()
        if normalized == "fixture":
            sources.append(LocalFixtureNewsSource())
        elif normalized == "kis":
            source = KisMarketDataSource(
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
            setattr(source, "symbol_selection_report", selection_report)
            sources.append(source)
        elif normalized == "kiwoom":
            source = KiwoomStockInfoSource(
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
            setattr(source, "symbol_selection_report", selection_report)
            sources.append(source)
        elif normalized == "naver_news":
            if not settings.naver_news_enabled:
                raise ValueError(
                    "TRENDS_NAVER_NEWS_ENABLED=true is required for naver_news source"
                )
            source = NaverNewsDiscoverySource(
                client=NaverNewsClient(
                    base_url=settings.naver_news_base_url,
                    client_id=settings.naver_client_id,
                    client_secret=settings.naver_client_secret,
                    http=http,
                ),
                symbol_records=symbol_records,
                query_limit_per_symbol=settings.naver_query_limit_per_symbol,
                result_limit_per_query=settings.naver_result_limit_per_query,
                include_aliases=settings.naver_include_aliases,
                include_query_keywords=settings.naver_include_query_keywords,
                review_repository=discovery_review_repository,
                discovery_rules=discovery_rules,
                discovery_rule_config_path=settings.discovery_rule_config_path,
            )
            setattr(source, "symbol_selection_report", selection_report)
            sources.append(source)
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
    return [
        record.symbol
        for record in resolve_source_symbol_selection(
            settings,
            symbol_catalog_repository=symbol_catalog_repository,
        ).selected_records
    ]


def resolve_source_symbol_selection(
    settings: Settings,
    *,
    symbol_catalog_repository: JsonSymbolCatalogRepository | None = None,
):
    catalog = None
    if symbol_catalog_repository is not None:
        catalog = symbol_catalog_repository.get_latest_sync()
    return build_symbol_selection_report(
        policy=SymbolSelectionPolicy(
            mode=settings.source_symbol_policy,
            explicit_symbols=settings.source_symbols or ["005930", "000660"],
            markets=settings.source_symbol_markets or [],
            classifications=settings.source_symbol_classifications or [],
            limit=settings.source_symbol_limit,
            valid_code_only=settings.source_symbol_valid_code_only,
        ),
        catalog=catalog,
        generated_at=now_kst(),
    )


def _log_symbol_selection(selection_report) -> None:
    logger.info(
        (
            "source_symbol_selection catalog_id=%s policy=%s selected_symbol_count=%s "
            "catalog_total_count=%s catalog_invalid_code_count=%s valid_code_count=%s "
            "selection_invalid_code_excluded_count=%s markets=%s classifications=%s "
            "explicit_override=%s catalog_missing_fallback=%s"
        ),
        selection_report.catalog_id or "none",
        selection_report.policy,
        selection_report.selected_symbol_count,
        selection_report.catalog_total_count,
        selection_report.catalog_invalid_code_count,
        selection_report.valid_code_count,
        selection_report.selection_invalid_code_excluded_count,
        ",".join(selection_report.market_filters),
        ",".join(selection_report.classification_filters),
        selection_report.explicit_override_used,
        selection_report.catalog_missing_fallback_used,
        extra={
            "event": "source_symbol_selection",
            "catalog_id": selection_report.catalog_id,
            "symbol_selection_policy": selection_report.policy,
            "selected_symbol_count": str(selection_report.selected_symbol_count),
            "catalog_total_count": str(selection_report.catalog_total_count),
            "catalog_invalid_code_count": str(selection_report.catalog_invalid_code_count),
            "valid_code_count": str(selection_report.valid_code_count),
            "selection_invalid_code_excluded_count": str(
                selection_report.selection_invalid_code_excluded_count
            ),
            "explicit_override_used": str(selection_report.explicit_override_used).lower(),
            "catalog_missing_fallback_used": str(
                selection_report.catalog_missing_fallback_used
            ).lower(),
        },
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
