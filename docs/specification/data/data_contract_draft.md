# 데이터 계약 초안

## 문서 메타데이터

- 문서 유형: Data Contract Draft
- 상태: Draft v0.4
- 권위 범위: Core signal contract, consumer payload contract, score/entity 정의, DTO 분리 원칙
- 상위 문서: `docs/architecture/architecture_specification.md`
- 관련 문서: `docs/specification/data/data_model_spec.md`, `docs/specification/data/persistence_spec.md`, `docs/specification/api/api_spec.md`
- 최종 수정일: 2026-04-15

## 1. 계약 원칙

- Core signal model은 consumer-agnostic이어야 한다.
- QTS payload, Generic payload, Workflow payload는 Adapter 산출물이다.
- 분석 output과 consumer-specific payload를 저장소와 코드에서 분리한다.
- confidence score는 설명 가능한 breakdown을 가져야 한다.
- Signal API DTO는 neutral signal 용어만 사용한다.
- QTS payload DTO에서만 `market_bias`, `risk_overrides`, `universe_adjustments`를 사용한다.

## 1.1 계약 분류

| 분류 | 권장 위치 | 설명 |
|------|-----------|------|
| Core signal contracts | `src/contracts/core.py` | RawNewsItem, NewsEvaluation, MarketSignal, ThemeSignal, StockSignal, TrendSnapshot |
| Adapter payload contracts | `src/contracts/payloads.py` | QTSInputPayload, GenericInsightPayload, WorkflowTriggerPayload |
| API DTO contracts | MVP 기본: `src/contracts/api.py`; 확장 시 `src/contracts/api_requests.py`, `src/contracts/api_responses.py` | transport 전용 API request/response, ErrorResponse, Pagination |
| Runtime/job contracts | `src/contracts/runtime.py` | RuntimeMode, JobRequest, JobResult, CorrelationContext |
| Symbol catalog contracts | `src/contracts/symbols.py` | SymbolRecord, SymbolCatalog |
| Port contracts | `src/contracts/ports.py` | repository/source/dispatch protocol |

API DTO 주의:

- `contracts/api.py`는 transport DTO 전용이다.
- MVP에서는 단일 `contracts/api.py`를 기본으로 시작한다.
- API request/response schema는 Core signal contract나 Adapter payload contract로 역수입하지 않는다.
- API DTO가 많아지면 `api_requests.py`와 `api_responses.py`로 분리한다.

## 2. Core Signal Model

### SymbolRecord / SymbolCatalog

Symbol catalog는 뉴스 발견과 provider별 종목코드 기반 조회를 위한 upstream contract다. Core signal model은 아니지만 Core/ingestion 경계를 오염시키지 않기 위해 별도 `contracts.symbols`에 둔다.

SymbolRecord:

- `symbol`
- `name`
- `market`
- `security_type`
- `korean_name`
- `english_name`
- `normalized_name`
- `aliases`
- `query_keywords`
- `metadata`

SymbolCatalog:

- `id`
- `as_of`
- `source`
- `records`
- `generated_at`
- `metadata`

SymbolCatalogValidationReport:

- `catalog_id`
- `generated_at`
- `total_count`
- `invalid_code_count`
- `duplicate_symbol_count`
- `duplicate_name_count`
- `missing_name_count`
- `market_distribution`
- `classification_distribution`
- `suspicious_records`

SymbolSelectionReport:

- `generated_at`
- `policy`
- `catalog_id`
- `explicit_override_used`
- `catalog_missing_fallback_used`
- `selected_symbol_count`
- `selected_records`
- `catalog_total_count`
- `catalog_invalid_code_count`
- `valid_code_count`
- `selection_invalid_code_excluded_count`
- `market_filters`
- `classification_filters`
- `limit`

주의:

- QTS/Observer universe의 전일종가 4000원 미만 제외 필터를 적용하지 않는다.
- 가격, 거래정지, 관리종목 여부 같은 provider metadata는 보존할 수 있지만 catalog 포함/제외 정책으로 즉시 사용하지 않는다.

### SourceExecutionReport

Provider source 실행 후 런타임 관측성을 위해 다음 값을 기록한다.

- `provider`
- `requested_symbol_count`
- `succeeded_symbol_count`
- `failed_symbol_count`
- `item_count`
- `partial_success`
- `failed_symbols`
- `query_count`
- `failed_query_count`
- `failed_query_sample`
- `raw_discovered_item_count`
- `deduplicated_item_count`
- `kept_item_count`
- `weak_keep_item_count`
- `dropped_item_count`
- `suspicious_item_count`
- `top_query_yield_sample`
- `top_symbol_yield_sample`
- `top_classification_yield_sample`
- `noisy_query_sample`
- `noisy_alias_sample`
- `noisy_keyword_sample`
- `ambiguous_symbol_sample`

Query 기반 discovery source는 Core 진입 전에 rule-based 품질 평가를 수행할 수 있다. 평가 결과는 `RawNewsItem.metadata`에 `query_origin`, `classification`, `discovery_decision`, `discovery_score`, `discovery_reasons`, `discovery_suspicious`로 보존한다. 이 값은 Core signal contract가 아니라 source/discovery 관측성 metadata다.

### Discovery Review Artifact

Naver News 같은 query 기반 discovery source는 review/calibration artifact를 저장할 수 있다.

- `provider`
- `generated_at`
- `items`
  - `symbol`
  - `query`
  - `query_origin`
  - `title`
  - `url`
  - `published_at`
  - `discovery_decision`
  - `discovery_score`
  - `discovery_reasons`
  - `discovery_suspicious`
  - `classification`
- `calibration_summary`
  - `per_query`
  - `per_symbol`
  - `per_classification`
  - `noisy_alias_sample`
  - `noisy_keyword_sample`
  - `ambiguous_symbol_sample`

### RawNewsItem

- `id`
- `source`
- `source_id`
- `title`
- `body`
- `url`
- `published_at`
- `collected_at`
- `language`
- `symbols`
- `metadata`

### NormalizedNewsItem

- `id`
- `raw_news_id`
- `normalized_title`
- `normalized_body`
- `canonical_url`
- `published_at`
- `language`
- `dedup_key`
- `content_hash`

### NewsEvaluation

- `id`
- `normalized_news_id`
- `relevance_score`
- `sentiment_score`
- `impact_score`
- `confidence_score`
- `novelty_score`
- `source_weight`
- `actionability_score`
- `urgency_score`
- `content_value_score`
- `credibility_breakdown`
- `themes`
- `sectors`
- `symbols`
- `rules_version`
- `evaluated_at`

### MarketSignal

- `id`
- `snapshot_id`
- `market`
- `bias_hint`
- `impact_score`
- `confidence_score`
- `driver_themes`
- `driver_news_ids`
- `generated_at`

주의:

- `bias_hint`는 중립 signal의 방향성 힌트다. QTS Adapter가 이를 QTS 전용 `market_bias`로 변환할 수 있지만 Core 자체가 QTS 필드를 만들지는 않는다.

### ThemeSignal

- `id`
- `snapshot_id`
- `theme`
- `sector`
- `rank`
- `momentum_score`
- `impact_score`
- `confidence_score`
- `news_count`
- `driver_news_ids`
- `generated_at`

### StockSignal

- `id`
- `snapshot_id`
- `symbol`
- `name`
- `themes`
- `relevance_score`
- `sentiment_score`
- `impact_score`
- `confidence_score`
- `urgency_score`
- `driver_news_ids`
- `generated_at`

### TrendSnapshot

- `id`
- `as_of`
- `window_start`
- `window_end`
- `market_signals`
- `theme_signals`
- `stock_signals`
- `evaluation_count`
- `rules_version`
- `created_at`

## 3. QTS Payload Model

QTSInputPayload:

- `id`
- `snapshot_id`
- `market_bias`
- `universe_adjustments`
- `risk_overrides`
- `sector_weights`
- `strategy_activation_hints`
- `confidence_score`
- `generated_at`
- `expires_at`
- `adapter_version`

규칙:

- 실제 주문 명령을 포함하지 않는다.
- 낮은 confidence signal은 `review_required`나 `watch`로 분리한다.
- QTS 정책은 QTS Adapter에만 위치한다.

## 4. Generic Payload Model

GenericInsightPayload:

- `id`
- `snapshot_id`
- `daily_briefing`
- `theme_ranking`
- `watchlist_candidates`
- `alert_summary`
- `report_seed`
- `confidence_labels`
- `generated_at`
- `adapter_version`

규칙:

- 자동화 routing condition을 포함하지 않는다.
- 사람 또는 외부 프로젝트가 소비할 insight 중심이다.

## 5. Workflow Payload Model

WorkflowTriggerPayload:

- `id`
- `snapshot_id`
- `trigger_type`
- `priority`
- `recommended_actions`
- `routing_conditions`
- `downstream_payload`
- `dispatch_policy`
- `confidence_gate`
- `generated_at`
- `adapter_version`

규칙:

- n8n 및 workflow automation control에 특화된다.
- 낮은 confidence/high urgency 조합은 manual review action을 권장한다.
- dispatch 결과는 별도 log로 저장한다.

## 6. Score Definitions

| 점수 | 의미 |
|------|------|
| `relevance_score` | 뉴스가 시장/테마/종목 분석에 관련 있는 정도 |
| `sentiment_score` | 긍정/부정 방향 |
| `impact_score` | 시장/테마/종목 영향 가능성 |
| `confidence_score` | source와 내용 기반 신뢰도 최종값 |
| `novelty_score` | 기존 signal 대비 새로움 |
| `source_weight` | source tier 기반 기본 가중치 |
| `actionability_score` | 후속 행동으로 연결 가능한 정도 |
| `urgency_score` | 시간 민감도 |
| `content_value_score` | 브리핑/리포트 소재 가치 |

## 7. Credibility Breakdown

`confidence_score`는 다음 breakdown을 기준으로 산정한다.

- `source_tier`
- `source_weight`
- `evidence_score`
- `corroboration_score`
- `content_quality_score`
- `freshness_score`
- `conflict_penalty`
- `rumor_penalty`
- `method_version`
