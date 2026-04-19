from __future__ import annotations

import pytest

from src.contracts.symbols import SymbolRecord
from src.ingestion.catalog.normalization import enrich_symbol_record


def test_preferred_stock_enrichment():
    record = SymbolRecord(symbol="005935", name="삼성전자우", market="KOSPI")
    enriched = enrich_symbol_record(record)
    
    assert enriched.metadata["classification"] == "preferred_stock"
    assert "삼성전자" in enriched.aliases
    assert "삼성전자 우선주" in enriched.query_keywords
    assert "삼성전자 주가" in enriched.query_keywords


def test_holding_company_enrichment():
    record = SymbolRecord(symbol="001234", name="LG홀딩스", market="KOSPI")
    enriched = enrich_symbol_record(record)
    
    assert enriched.metadata["is_holding"] == "true"
    assert "LG지주" in enriched.aliases


def test_etf_provider_removal_in_query():
    record = SymbolRecord(symbol="123456", name="KODEX 삼성그룹", market="KOSPI", security_type="etf")
    enriched = enrich_symbol_record(record)
    
    assert enriched.metadata["classification"] == "etf"
    assert "삼성그룹" in enriched.query_keywords
    assert "KODEX 삼성그룹 ETF" in enriched.query_keywords


def test_infra_and_ship_classification():
    infra = enrich_symbol_record(SymbolRecord(symbol="088980", name="맥쿼리인프라", market="KOSPI"))
    assert infra.metadata["classification"] == "infra"
    
    ship = enrich_symbol_record(SymbolRecord(symbol="001111", name="바다로선박", market="KOSPI"))
    assert ship.metadata["classification"] == "ship"


def test_name_with_english_parentheses():
    record = SymbolRecord(symbol="000000", name="삼성전자(SAMSUNG)", market="KOSPI")
    enriched = enrich_symbol_record(record)
    
    assert "삼성전자" in enriched.aliases
    assert "삼성전자(SAMSUNG)" in enriched.aliases
