from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _kiwoom_base_url(mode: str) -> str:
    configured = os.getenv("KIWOOM_BASE_URL")
    if configured:
        return configured.rstrip("/")
    if mode.strip().upper() in {"KIWOOM_MOCK", "MOCK", "PAPER", "DEMO"}:
        return "https://mockapi.kiwoom.com"
    return "https://api.kiwoom.com"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    rules_version: str
    active_sources: list[str] | None = None
    source_symbols: list[str] | None = None
    source_symbol_policy: str = "explicit"
    source_symbol_markets: list[str] | None = None
    source_symbol_classifications: list[str] | None = None
    source_symbol_limit: int = 0
    source_symbol_valid_code_only: bool = True
    source_timeout_seconds: float = 10
    source_partial_success: bool = True
    symbol_catalog_source: str = "kis_master"
    symbol_catalog_path: str = ""
    symbol_catalog_markets: list[str] | None = None
    symbol_catalog_url: str = ""
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    kis_market_division_code: str = "J"
    kis_tr_id_quote: str = "FHKST01010100"
    kis_tr_id_invest_opinion: str = "FHKST663300C0"
    kis_invest_opinion_lookback_days: int = 180
    kis_invest_opinion_limit_per_symbol: int = 5
    kiwoom_mode: str = "KIWOOM_REAL"
    kiwoom_app_key: str = ""
    kiwoom_app_secret: str = ""
    kiwoom_account_no: str = ""
    kiwoom_account_product_code: str = ""
    kiwoom_base_url: str = "https://api.kiwoom.com"
    kiwoom_stock_info_path: str = "/api/dostk/stkinfo"
    naver_client_id: str = ""
    naver_client_secret: str = ""
    naver_news_base_url: str = "https://openapi.naver.com"
    naver_news_enabled: bool = False
    naver_query_limit_per_symbol: int = 2
    naver_result_limit_per_query: int = 5
    naver_include_aliases: bool = False
    naver_include_query_keywords: bool = True
    discovery_review_enabled: bool = True
    discovery_rule_config_path: str = ""
    n8n_webhook_secret: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("TRENDS_DATA_DIR", ".local/trends-analyzer")).resolve()
        kiwoom_mode = os.getenv("KIWOOM_MODE", "KIWOOM_REAL")
        return cls(
            data_dir=data_dir,
            rules_version=os.getenv("RULES_VERSION", "rules-mvp-0.1"),
            active_sources=_csv_env("TRENDS_ACTIVE_SOURCES", ["fixture"]),
            source_symbols=_csv_env("TRENDS_SOURCE_SYMBOLS", ["005930", "000660"]),
            source_symbol_policy=os.getenv("TRENDS_SOURCE_SYMBOL_POLICY", "explicit"),
            source_symbol_markets=_csv_env(
                "TRENDS_SOURCE_SYMBOL_MARKETS",
                ["KOSPI", "KOSDAQ"],
            ),
            source_symbol_classifications=_csv_env(
                "TRENDS_SOURCE_SYMBOL_CLASSIFICATIONS",
                ["stock"],
            ),
            source_symbol_limit=int(os.getenv("TRENDS_SOURCE_SYMBOL_LIMIT", "0")),
            source_symbol_valid_code_only=_bool_env("TRENDS_SOURCE_SYMBOL_VALID_CODE_ONLY", True),
            source_timeout_seconds=float(os.getenv("TRENDS_SOURCE_TIMEOUT_SECONDS", "10")),
            source_partial_success=_bool_env("TRENDS_SOURCE_PARTIAL_SUCCESS", True),
            symbol_catalog_source=os.getenv("TRENDS_SYMBOL_CATALOG_SOURCE", "kis_master"),
            symbol_catalog_path=os.getenv("TRENDS_SYMBOL_CATALOG_PATH", ""),
            symbol_catalog_markets=_csv_env(
                "TRENDS_SYMBOL_CATALOG_MARKETS",
                ["KOSPI", "KOSDAQ", "KONEX"],
            ),
            symbol_catalog_url=os.getenv(
                "TRENDS_SYMBOL_CATALOG_URL",
                "",
            ),
            kis_app_key=os.getenv("KIS_APP_KEY", ""),
            kis_app_secret=os.getenv("KIS_APP_SECRET", ""),
            kis_base_url=os.getenv(
                "KIS_BASE_URL",
                "https://openapi.koreainvestment.com:9443",
            ).rstrip("/"),
            kis_market_division_code=os.getenv("KIS_MARKET_DIVISION_CODE", "J"),
            kis_tr_id_quote=os.getenv("KIS_TR_ID_QUOTE", "FHKST01010100"),
            kis_tr_id_invest_opinion=os.getenv(
                "KIS_TR_ID_INVEST_OPINION",
                "FHKST663300C0",
            ),
            kis_invest_opinion_lookback_days=int(
                os.getenv("KIS_INVEST_OPINION_LOOKBACK_DAYS", "180")
            ),
            kis_invest_opinion_limit_per_symbol=int(
                os.getenv("KIS_INVEST_OPINION_LIMIT_PER_SYMBOL", "5")
            ),
            kiwoom_mode=kiwoom_mode,
            kiwoom_app_key=_env_first("KIWOOM_APP_KEY", "KIWOOM_API_KEY"),
            kiwoom_app_secret=_env_first("KIWOOM_APP_SECRET", "KIWOOM_API_SECRET"),
            kiwoom_account_no=os.getenv("KIWOOM_APP_ACCOUNT_NO", ""),
            kiwoom_account_product_code=os.getenv("KIWOOM_APP_ACNT_PRDT_CD", ""),
            kiwoom_base_url=_kiwoom_base_url(kiwoom_mode),
            kiwoom_stock_info_path=os.getenv("KIWOOM_STOCK_INFO_PATH", "/api/dostk/stkinfo"),
            naver_client_id=os.getenv("NAVER_CLIENT_ID", ""),
            naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", ""),
            naver_news_base_url=os.getenv(
                "NAVER_NEWS_BASE_URL",
                "https://openapi.naver.com",
            ).rstrip("/"),
            naver_news_enabled=_bool_env("TRENDS_NAVER_NEWS_ENABLED", False),
            naver_query_limit_per_symbol=int(
                os.getenv("TRENDS_NAVER_QUERY_LIMIT_PER_SYMBOL", "2")
            ),
            naver_result_limit_per_query=int(
                os.getenv("TRENDS_NAVER_RESULT_LIMIT_PER_QUERY", "5")
            ),
            naver_include_aliases=_bool_env("TRENDS_NAVER_INCLUDE_ALIASES", False),
            naver_include_query_keywords=_bool_env(
                "TRENDS_NAVER_INCLUDE_QUERY_KEYWORDS",
                True,
            ),
            discovery_review_enabled=_bool_env("TRENDS_DISCOVERY_REVIEW_ENABLED", True),
            discovery_rule_config_path=os.getenv("TRENDS_DISCOVERY_RULE_CONFIG_PATH", ""),
            n8n_webhook_secret=os.getenv("N8N_WEBHOOK_SECRET"),
        )
