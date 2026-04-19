# PDCA Plan: API & Logic Integration (api-integration)

## 1. 개요 (Abstract)

`workspace-alignment-v1`에서 구축한 API Skeleton과 `news-credibility-logic` 등 고도화된 Core 로직을 UseCase와 Container를 통해 실질적으로 연결한다. Mock 데이터를 반환하던 API 엔드포인트들이 실제 분석 파이프라인(Ingestion -> Normalization -> Scoring -> Aggregation -> Adapter)을 호출하고 결과를 반환하도록 통합한다.

## 2. 가치 제안 (Value Proposition)

- **엔드투엔드 흐름 완성**: 정적 Mock에서 탈피하여 실제 데이터 소스(Fixture/KIS 등)로부터 뉴스를 가져와 분석하고 Signal을 생성하는 전체 흐름을 API로 제어할 수 있다.
- **다양한 소비자 지원**: QTS뿐만 아니라 Generic Insight(브리핑)와 Workflow(n8n)용 분석 결과도 API를 통해 즉시 소비 가능하다.
- **의존성 주입 완성**: Container에서 모든 UseCase와 Repository, Adapter를 올바르게 연결하여 시스템의 유지보수성을 확보한다.

## 3. 기능 범위 (Scope)

### 3.1 Port & Repository 확장
- [ ] `src/contracts/ports.py`: `GenericPayloadRepository`, `WorkflowPayloadRepository`, `GenericAdapterPort`, `WorkflowAdapterPort` 추가.
- [ ] `src/db/repositories/jsonl.py`: 신규 Repository 구현 (JSONL 기반).

### 3.2 UseCase 고도화
- [ ] `src/application/use_cases/analyze_daily_trends.py`:
    - [ ] `GenericAdapter` 및 `WorkflowAdapter` 호출 로직 추가.
    - [ ] 생성된 Payload들을 각각의 Repository에 저장.
- [ ] `src/application/use_cases/get_signals.py`: (신규) 스냅샷 기반 Market/Theme/Stock signal 조회 UseCase.
- [ ] `src/application/use_cases/ingest_news.py`: (신규) 단건/배치 뉴스 수집 UseCase.

### 3.3 Bootstrap & Container 연동
- [ ] `src/bootstrap/container.py`:
    - [ ] 신규 Adapter, Repository, UseCase 등록.
    - [ ] `AnalyzeDailyTrendsUseCase` 생성 시 모든 필요한 의존성 주입.

### 3.4 API Route 실구현
- [ ] `src/api/routes/analyze.py`: `AnalyzeDailyTrendsUseCase` 호출.
- [ ] `src/api/routes/signals.py`: `GetSignalsUseCase` 호출.
- [ ] `src/api/routes/ingest.py`: `IngestNewsUseCase` 호출.
- [ ] `src/api/routes/qts.py`, `src/api/routes/generic.py`, `src/api/routes/workflow.py`: 각각의 Repository에서 최신 Payload 조회.

## 4. 구현 전략 (Implementation Strategy)

1.  **Contract First**: Port와 Repository 계약을 먼저 정의하여 의존성 경계를 고정한다.
2.  **Top-down Integration**: Container에서 의존성을 먼저 연결한 후, API Route에서 하나씩 UseCase로 교체한다.
3.  **Local Fixture 우선**: 외부 API(KIS 등) 연동 전, `LocalFixtureNewsSource`를 사용하여 로컬에서 전체 분석 파이프라인이 정상 작동하는지 확인한다.
4.  **Error Handling**: API 계층에서 UseCase의 에러(예: 장중 보호 가드)를 적절한 HTTP 상태 코드로 변환하는 로직을 점검한다.

## 5. 검증 계획 (Verification Plan)

- **Integration Test**: `tests/test_api_integration.py` 생성.
    - [ ] `/api/v1/analyze/daily` 호출 후 실제 Snapshot과 Payload 파일이 생성되는지 확인.
    - [ ] 생성된 Snapshot ID를 이용해 `/api/v1/signals/market` 등의 조회 API가 정확한 데이터를 반환하는지 확인.
- **End-to-End**: Local-first 환경에서 `batch ingest` -> `analyze` -> `get payload` 과정이 에러 없이 수행되는지 확인.

## 6. 일정 및 우선순위 (Timeline & Priority)

1.  **P0 (Critical)**: `AnalyzeDailyTrendsUseCase` 고도화 및 Container 연동, Analyze API 연결.
2.  **P1 (High)**: Signals 및 Payload 조회 API(QTS/Generic/Workflow) 연결.
3.  **P2 (Normal)**: Ingest UseCase 구현 및 API 연결.
