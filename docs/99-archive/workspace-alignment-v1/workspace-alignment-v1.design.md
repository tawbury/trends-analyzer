# PDCA Design: Workspace Alignment & Core Enhancement (workspace-alignment-v1)

## 1. 개요 (Abstract)
본 설계 문서는 `workspace-alignment-v1` 계획에 명시된 Data Contract 확장, Core Logic 고도화, Adapter 구현, API Route 생성, 그리고 Market Hours Guard 정책 적용에 대한 상세 기술 명세 및 모듈 인터페이스를 정의합니다.

## 2. 모듈 설계 및 데이터 모델 변경 (Module & Data Model Design)

### 2.1 Core Contracts (`src/contracts/core.py`)
`NewsEvaluation` 데이터 클래스에 신뢰도 및 평가 관련 필드를 추가합니다.

*   **변경 대상**: `NewsEvaluation`
*   **추가 필드**:
    *   `urgency_score: float`: 긴급도 점수 (0.0 ~ 1.0)
    *   `actionability_score: float`: 후속 행동 가능성 점수 (0.0 ~ 1.0)
    *   `content_value_score: float`: 콘텐츠 가치 점수 (0.0 ~ 1.0)
    *   `credibility_breakdown: dict[str, float | str]`: 신뢰도 세부 요소 및 메서드 버전

### 2.2 Payload Contracts (`src/contracts/payloads.py`)
QTSInputPayload 외에 Generic 및 Workflow 어댑터용 Payload를 정의합니다.

*   **신규 클래스**: `GenericInsightPayload`
    *   `id: str`, `snapshot_id: str`, `daily_briefing: dict`, `theme_ranking: list`, `watchlist_candidates: list`, `alert_summary: dict`, `report_seed: dict`, `generated_at: datetime`
*   **신규 클래스**: `WorkflowTriggerPayload`
    *   `id: str`, `snapshot_id: str`, `trigger_type: str`, `priority: str`, `recommended_actions: list`, `routing_conditions: dict`, `downstream_payload: dict`, `dispatch_policy: str`, `generated_at: datetime`

### 2.3 Core Logic (`src/core/score.py`, `src/core/aggregate.py`)
Mock 로직을 구체적인 평가 로직으로 변경합니다.

*   **`src/core/score.py`**:
    *   `MockNewsScorer` -> `NewsScorer` (또는 `CredibilityBasedNewsScorer`)로 변경
    *   단순 키워드 기반이 아닌, `docs/specification/data/news_credibility_spec.md`의 명세에 따라 `evidence_score`, `corroboration_score` 등을 가산하여 최종 `confidence_score` 및 `credibility_breakdown` 도출 로직 추가.
*   **`src/core/aggregate.py`**:
    *   `MarketSignal`, `ThemeSignal`, `StockSignal` 생성 시 `driver_news_ids`를 단순 전체 포함이 아닌, `impact_score`와 `confidence_score`가 특정 임계치(예: 0.6) 이상인 뉴스만 필터링하여 매핑.

### 2.4 Adapters (`src/adapters/`)
신규 Adapter를 구현합니다.

*   **`src/adapters/generic/adapter.py`**: `GenericAdapter` 클래스. `TrendSnapshot`을 받아 `GenericInsightPayload`로 변환. 상위 랭킹 테마 및 관심 종목 추출 로직 포함.
*   **`src/adapters/workflow/adapter.py`**: `WorkflowAdapter` 클래스. `TrendSnapshot`을 받아 `WorkflowTriggerPayload`로 변환. 우선순위 결정 및 dispatch 트리거 생성 로직 포함.

### 2.5 API Layer (`src/api/routes/`)
REST API 엔드포인트를 명세에 맞게 구현합니다.

*   **`src/api/routes/ingest.py`**:
    *   `POST /api/v1/ingest/news`
    *   `POST /api/v1/ingest/batch`
    *   `POST /api/v1/ingest/webhook/n8n`
*   **`src/api/routes/signals.py`**:
    *   `GET /api/v1/signals/market`
    *   `GET /api/v1/signals/themes`
    *   `GET /api/v1/signals/stocks`
    *   `GET /api/v1/news/evaluations`
*   **`src/api/routes/qts.py`**:
    *   `GET /api/v1/qts/daily-input`
    *   `GET /api/v1/qts/universe-adjustments`
    *   `GET /api/v1/qts/risk-overrides`
*   **`src/api/routes/generic.py`**: `GET /api/v1/generic/briefing` 등
*   **`src/api/routes/workflow.py`**: `GET /api/v1/workflow/payload`, `POST /api/v1/workflow/dispatch` 등
*   **`src/api/routes/ops.py`**: `GET /api/v1/health`, `GET /api/v1/jobs/status` 등

### 2.6 Dependencies & Guards (`src/api/dependencies.py`)
`is_korean_market_hours` 함수를 사용하는 Guard 의존성을 명확히 정의합니다.

*   **`verify_market_hours`**: FastAPI 의존성으로, 장중일 경우 `409 Conflict` (에러 코드 `MARKET_HOURS_GUARD`) 발생. write 및 heavy endpoint에 적용.

## 3. 테스트 전략 (Test Strategy)
*   **Unit Test**:
    *   `NewsScorer`의 `credibility_breakdown` 및 점수 계산 결과 검증.
    *   `TrendAggregator`의 `driver_news_ids` 필터링 로직 검증.
    *   각 Adapter의 Payload 변환 형식 정합성 검증.
*   **Integration Test**:
    *   FastAPI `TestClient`를 이용해 각 API 라우트의 200 OK 응답 및 스키마 검증.
    *   Mocking된 시간에 대해 장중/장외 조건에 따른 API 접근 제어 로직 검증 (409 Conflict 발생 확인).

## 4. 고려사항 및 제약사항 (Considerations & Constraints)
*   API 라우트의 경우 초기에는 실제 비즈니스 로직(UseCase) 연결보다, API Skeleton(라우터 및 Guard 연결, Dummy Data 반환) 구축을 목표로 하여 Contract 정합성을 우선 검증합니다.
*   장중 보호 정책은 API 단에서 강제되도록 모든 관련 엔드포인트에 `Depends(verify_market_hours)`를 필수적으로 주입해야 합니다.
