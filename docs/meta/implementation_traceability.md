# 구현 추적성 문서

## 문서 메타데이터

- 문서 유형: Implementation Traceability
- 상태: Draft v0.4
- 권위 범위: 문서 개념에서 권장 source directory/file로의 매핑, MVP 구현 slice, doc-to-code update rule
- 상위 문서: `docs/meta/docs_index.md`
- 관련 문서: `docs/architecture/architecture_specification.md`, `docs/architecture/module_design.md`, `docs/specification/source/source_module_spec.md`, `docs/specification/api/api_spec.md`, `docs/architecture/environment_config.md`
- 최종 수정일: 2026-04-15

## 1. 목적

이 문서는 구현 에이전트가 문서 개념을 실제 코드 위치로 안전하게 옮길 수 있도록 traceability 기준을 제공한다.

이 문서는 새로운 아키텍처를 정의하지 않는다. 이미 확정된 독립 Trend Intelligence Platform 방향, UseCase orchestration boundary, contracts layer, adapter/gateway/dispatch 분리, OCI 초기 배포, KST 장중 보호 정책을 코드 작업으로 연결하기 위한 handoff 문서다.

## 2. 문서 섹션에서 Source Directory로의 매핑

| 문서/섹션 | 구현 위치 | 구현 시 확인할 권위 문서 |
|-----------|-----------|--------------------------|
| `docs/architecture/architecture_specification.md`의 Application / UseCase Layer | `src/application/use_cases/` | `docs/architecture/module_design.md`, `docs/specification/source/source_module_spec.md` |
| `docs/architecture/architecture_specification.md`의 Trend Core | `src/core/` | `docs/specification/data/data_contract_draft.md`, `docs/specification/data/data_model_spec.md` |
| `docs/architecture/architecture_specification.md`의 Adapter Layer | `src/adapters/qts/`, `src/adapters/generic/`, `src/adapters/workflow/` | `docs/architecture/module_design.md`, `docs/specification/data/data_contract_draft.md` |
| `docs/architecture/architecture_specification.md`의 Integration / n8n Layer | `src/integration/n8n/` | `docs/architecture/module_design.md`, `docs/specification/api/api_spec.md` |
| `docs/architecture/architecture_specification.md`의 Runtime / Dispatch Layer | `src/runtime/dispatch/` | `docs/architecture/runtime_scheduling_policy.md`, `docs/architecture/observability_ops.md` |
| `docs/specification/api/api_draft.md`의 Endpoint Groups | `src/api/routes/` | `docs/specification/api/api_spec.md` |
| `docs/specification/data/data_contract_draft.md`의 Core Signal Model | `src/contracts/core.py` | `docs/specification/data/data_model_spec.md` |
| `docs/specification/data/data_contract_draft.md`의 Consumer Payload Model | `src/contracts/payloads.py` | `docs/architecture/module_design.md` |
| Symbol Catalog / Universe source | `src/contracts/symbols.py`, `src/ingestion/catalog/`, `src/application/use_cases/refresh_symbol_catalog.py` | `docs/specification/source/source_module_spec.md`, `docs/architecture/environment_config.md` |
| Symbol quality / lookup / selection | `src/ingestion/catalog/validation.py`, `src/ingestion/catalog/normalization.py`, `src/ingestion/catalog/lookup.py`, `src/ingestion/catalog/selection.py` | `docs/specification/data/data_contract_draft.md`, `docs/architecture/environment_config.md` |
| Query news discovery | `src/ingestion/clients/naver_news_client.py`, `src/ingestion/loaders/naver_news_loader.py`, `src/ingestion/loaders/query_strategy.py` | `docs/specification/source/source_module_spec.md`, `docs/architecture/environment_config.md` |
| Discovery quality evaluation | `src/ingestion/discovery/` | `docs/specification/source/source_module_spec.md`, `docs/architecture/observability_ops.md` |
| Source execution reporting | `src/contracts/runtime.py`, `src/ingestion/loaders/`, `src/ingestion/loaders/composite.py` | `docs/specification/source/source_module_spec.md`, `docs/architecture/observability_ops.md` |
| `docs/architecture/runtime_scheduling_policy.md`의 market-hours guard | `src/shared/market_hours.py`, `src/api/dependencies.py`, `src/batch/runner.py` | `docs/architecture/runtime_scheduling_policy.md` |
| `docs/architecture/environment_config.md`의 env var groups | `src/shared/config.py` 또는 equivalent | `docs/architecture/environment_config.md` |
| `docs/architecture/observability_ops.md`의 job/correlation tracking | `src/contracts/runtime.py`, `src/shared/logging.py`, `src/db/repositories/` | `docs/architecture/observability_ops.md` |

## 3. Core UseCase에서 권장 파일로의 매핑

| UseCase | 권장 파일 | 주요 의존성 | 비고 |
|---------|-----------|-------------|------|
| `IngestNewsUseCase` | `src/application/use_cases/ingest_news.py` | `NewsSourcePort`, `NewsRepository`, `CorrelationContext` | source client를 직접 route/batch에서 호출하지 않게 하는 경계 |
| `AnalyzeDailyTrendsUseCase` | `src/application/use_cases/analyze_daily_trends.py` | ingestion port, `src/core/*`, `SnapshotRepository`, `JobRepository` | MVP 첫 분석 흐름의 중심 |
| `RefreshSymbolCatalogUseCase` | `src/application/use_cases/refresh_symbol_catalog.py` | `SymbolCatalogSourcePort`, `SymbolCatalogRepository` | QTS 가격 필터 없이 독립 symbol catalog artifact 생성 |
| `GenerateQtsPayloadUseCase` | `src/application/use_cases/generate_qts_payload.py` | `SnapshotRepository`, `QtsAdapter`, `PayloadRepository` | neutral signal을 QTS payload로 변환 |
| `GenerateGenericInsightUseCase` | `src/application/use_cases/generate_generic_insight.py` | `SnapshotRepository`, `GenericAdapter`, `PayloadRepository` | MVP 이후 확장 가능 |
| `GenerateWorkflowPayloadUseCase` | `src/application/use_cases/generate_workflow_payload.py` | `SnapshotRepository`, `WorkflowAdapter`, `PayloadRepository` | dispatch 실행과 payload mapping을 분리 |
| `DispatchWorkflowPayloadUseCase` | `src/application/use_cases/dispatch_workflow_payload.py` | `WorkflowPayloadRepository`, `RuntimeDispatchService`, `CorrelationContext` | dispatch 요청과 context 전달 담당 |

UseCase는 Core 알고리즘, Adapter mapping, HTTP validation을 직접 구현하지 않는다.

## 4. Contract Type에서 권장 파일로의 매핑

| 계약 유형 | 권장 파일 | 포함 대상 |
|-----------|-----------|-----------|
| Core signal contracts | `src/contracts/core.py` | `RawNewsItem`, `NormalizedNewsItem`, `NewsEvaluation`, `MarketSignal`, `ThemeSignal`, `StockSignal`, `TrendSnapshot` |
| Adapter payload contracts | `src/contracts/payloads.py` | `QTSInputPayload`, `GenericInsightPayload`, `WorkflowTriggerPayload` |
| API transport DTO contracts | MVP: `src/contracts/api.py` | API request/response, `ErrorResponse`, pagination DTO |
| API transport DTO 확장 | `src/contracts/api_requests.py`, `src/contracts/api_responses.py` | API DTO가 커질 때만 분리 |
| Runtime/job contracts | `src/contracts/runtime.py` | `RuntimeMode`, `JobRequest`, `JobResult`, `CorrelationContext`, `DispatchResult` |
| Symbol catalog contracts | `src/contracts/symbols.py` | `SymbolRecord`, `SymbolCatalog`, `SymbolCatalogValidationReport`, `SymbolSelectionReport` |
| Port contracts | `src/contracts/ports.py` | repository/source/dispatch protocol |

주의:

- Core와 Adapter는 API transport DTO를 import하지 않는다.
- Adapter는 payload contract에 의존하고, FastAPI/Pydantic request schema에 의존하지 않는다.
- DB repository는 `contracts.ports`를 구현한다.

## 5. API Group에서 Route File로의 매핑

| API Group | 권장 route file | 구현 기준 |
|-----------|-----------------|-----------|
| Ingestion API | `src/api/routes/ingest.py` | `IngestNewsUseCase` 호출, webhook verification은 n8n integration과 분리 |
| Analysis API | `src/api/routes/analyze.py` | `AnalyzeDailyTrendsUseCase` 호출, market-hours guard 적용 |
| Signal API | `src/api/routes/signals.py` | neutral signal DTO만 반환 |
| QTS API | `src/api/routes/qts.py` | QTS Adapter payload 조회. `market_bias`는 여기서만 노출 |
| Generic API | `src/api/routes/generic.py` | generic insight payload 조회 |
| Workflow API | `src/api/routes/workflow.py` | workflow payload 조회 및 dispatch UseCase 호출 |
| Ops API | `src/api/routes/ops.py` | health, readiness, job status, config version |

구현 계약의 세부 필드는 `docs/specification/api/api_spec.md`를 우선한다. `docs/specification/api/api_draft.md`는 endpoint group과 사용 의도 확인용으로 사용한다.

## 6. Runtime Concern에서 권장 파일로의 매핑

| Runtime Concern | 권장 위치 | 구현 기준 |
|-----------------|-----------|-----------|
| API app bootstrap | `src/api/app.py` | route 등록, settings 주입, dependency 구성 |
| API dependencies | `src/api/dependencies.py` | auth, correlation id, market-hours guard |
| Batch runner | `src/batch/runner.py` | UseCase 호출, 장중 heavy job 차단 |
| Symbol catalog refresh | `src/batch/refresh_symbol_catalog.py` | `RefreshSymbolCatalogUseCase` 호출, KIS master/JSON artifact source 선택 |
| Scheduler | `src/scheduler/main.py` | batch window trigger, job overlap 방지 |
| Runtime dispatch | `src/runtime/dispatch/service.py` | idempotency, retryability, dispatch execution policy |
| n8n gateway | `src/integration/n8n/gateway.py` | outbound HTTP/webhook 호출 |
| n8n webhook verification | `src/integration/n8n/security.py` | shared secret/HMAC signature 검증 |
| Market-hours guard | `src/shared/market_hours.py` | KST 09:00~15:30 heavy job 차단 |
| Config loading | `src/shared/config.py` | `docs/architecture/environment_config.md` 기준 env var 로딩 |
| Logging/correlation | `src/shared/logging.py` | `correlation_id`, `job_id`, `dispatch_id` 포함 |

## 7. 권장 MVP 구현 Slice

로컬 Windows 11 + WSL2에서 먼저 검증할 slice는 다음으로 제한한다.

1. one ingest path
   - 예: local fixture 또는 단일 RSS/mock loader
   - 권장 파일: `src/ingestion/loaders/local_fixture_loader.py`, `src/application/use_cases/ingest_news.py`

2. one `analyze_daily` use case
   - normalize, deduplicate, score, aggregate의 최소 흐름
   - 권장 파일: `src/application/use_cases/analyze_daily_trends.py`

3. one `TrendSnapshot` persistence flow
   - PostgreSQL이 준비되지 않았으면 JSONL 보조 저장소로 먼저 검증 가능
   - 권장 파일: `src/db/repositories/snapshot_repository.py`

4. one QTS payload generation flow
   - neutral `bias_hint`를 QTS `market_bias`로 변환
   - 권장 파일: `src/adapters/qts/adapter.py`, `src/application/use_cases/generate_qts_payload.py`

5. one read-only API endpoint
   - 예: `GET /api/v1/qts/daily-input` 또는 `GET /api/v1/signals/market`
   - 권장 파일: `src/api/routes/qts.py` 또는 `src/api/routes/signals.py`

6. one market-hours guard
   - API dependency와 batch runner 양쪽에서 재사용
   - 권장 파일: `src/shared/market_hours.py`, `src/api/dependencies.py`

7. one job/correlation id propagation path
   - API request 또는 batch command에서 UseCase, repository 저장, log event까지 전달
   - 권장 파일: `src/contracts/runtime.py`, `src/shared/logging.py`, `src/application/use_cases/analyze_daily_trends.py`

이 slice가 통과하기 전에는 Generic Adapter, Workflow Adapter, n8n outbound dispatch, rebuild, scheduler 자동화 범위를 넓히지 않는다.

## 8. Doc-to-Code Update Rule

구현 중 의미 있는 변경이 생기면 다음 문서를 함께 갱신한다.

| 코드 변경 | 함께 갱신할 문서 |
|-----------|------------------|
| 새 contract file 추가 | `docs/specification/data/data_contract_draft.md`, `docs/specification/source/source_module_spec.md`, 이 문서 |
| 새 UseCase 추가 | `docs/architecture/module_design.md`, `docs/specification/source/source_module_spec.md`, 이 문서 |
| 새 API endpoint 추가 | `docs/specification/api/api_draft.md`, `docs/specification/api/api_spec.md`, 이 문서 |
| 새 runtime mode 추가 | `docs/architecture/runtime_scheduling_policy.md`, `docs/architecture/environment_config.md`, `docs/specification/source/source_module_spec.md` |
| 새 env var 추가 | `docs/architecture/environment_config.md`, 필요 시 `docs/architecture/deployment_topology.md` |
| 새 repository/port 추가 | `docs/specification/data/persistence_spec.md`, `docs/specification/data/data_contract_draft.md`, `docs/specification/source/source_module_spec.md` |
| 새 symbol catalog source 추가 | `docs/specification/source/source_module_spec.md`, `docs/architecture/environment_config.md`, 이 문서 |
| 새 adapter payload 추가 | `docs/architecture/module_design.md`, `docs/specification/data/data_contract_draft.md`, `docs/specification/api/api_spec.md` |
| n8n dispatch 정책 변경 | `docs/architecture/module_design.md`, `docs/architecture/runtime_scheduling_policy.md`, `docs/architecture/observability_ops.md` |

규칙:

- 코드를 먼저 바꾸고 문서를 나중에 추측해서 맞추지 않는다.
- 계약 변경은 contract 문서와 source module spec을 먼저 맞춘다.
- API 동작 변경은 `docs/specification/api/api_spec.md`를 우선 갱신한다.
- 새 환경 변수는 `docs/architecture/environment_config.md`에 먼저 등록한다.
- 문서와 코드가 충돌하면 `docs/meta/docs_index.md`의 source-of-truth 규칙을 따른다.
