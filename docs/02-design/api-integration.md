# PDCA Design: API & Logic Integration (api-integration)

## 1. 개요 (Abstract)
본 설계 문서는 `api-integration` 계획에 따른 Port 확장, Repository 구현, UseCase 고도화 및 Container 연동에 대한 상세 기술 명세를 정의합니다.

## 2. 모듈 설계 (Module Design)

### 2.1 Port 확장 (`src/contracts/ports.py`)
신규 어댑터와 저장소를 위한 인터페이스를 추가합니다.

*   `GenericAdapterPort`: `TrendSnapshot` -> `GenericInsightPayload`
*   `WorkflowAdapterPort`: `TrendSnapshot` -> `WorkflowTriggerPayload`
*   `GenericPayloadRepository`: `GenericInsightPayload` 저장 및 조회
*   `WorkflowPayloadRepository`: `WorkflowTriggerPayload` 저장 및 조회

### 2.2 Repository 구현 (`src/db/repositories/jsonl.py`)
기존 `JsonlSnapshotRepository` 패턴을 따라 신규 Repository들을 구현합니다.

*   `JsonlGenericPayloadRepository`
*   `JsonlWorkflowPayloadRepository`

### 2.3 UseCase 고도화 (`src/application/use_cases/`)
*   **`AnalyzeDailyTrendsUseCase`**:
    *   `__init__`에 `GenericAdapterPort`, `WorkflowAdapterPort`, `GenericPayloadRepository`, `WorkflowPayloadRepository` 추가.
    *   `execute()` 내부에서 Snapshot 생성 후 모든 Adapter를 호출하여 Payload를 생성하고 각각 저장.
*   **`GetSignalsUseCase`**: (신규) `SnapshotRepository`를 사용하여 특정 ID 또는 최신 스냅샷의 시그널을 반환.

### 2.4 Container 연동 (`src/bootstrap/container.py`)
`build_container()` 함수에서 신규 컴포넌트들을 생성하고 `AnalyzeDailyTrendsUseCase`에 주입합니다.

## 3. 구현 계획 (Implementation Plan)

1.  **Contracts**: `ports.py`에 인터페이스 추가.
2.  **Repositories**: `jsonl.py`에 신규 클래스 추가.
3.  **UseCase**: `analyze_daily_trends.py` 수정 및 `get_signals.py` 생성.
4.  **Bootstrap**: `container.py`에서 의존성 주입 설정 업데이트.
5.  **API Routes**: `analyze.py`, `signals.py`, `qts.py`, `generic.py`, `workflow.py`에서 UseCase 및 Repository 호출로 교체.

## 4. 테스트 전략 (Test Strategy)
*   **Integration Test**: `tests/test_api_integration.py` 생성.
    *   `TestClient`를 사용하여 `/api/v1/analyze/daily` 호출.
    *   결과로 반환된 `snapshot_id`를 사용하여 각 시그널 및 페이로드 조회 API 호출 결과 검증.
    *   실제 JSONL 파일에 데이터가 기록되는지 확인.
