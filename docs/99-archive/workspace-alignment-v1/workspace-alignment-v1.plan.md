# PDCA Plan: Workspace Alignment & Core Enhancement (workspace-alignment-v1)

## 1. 개요 (Abstract)

Trend Intelligence Platform의 현재 구현 상태와 `docs/` 내 설계 문서 간의 차이를 해소하고, 마스터 기획서(Phase 1~3)에 명시된 핵심 기능을 완성한다. 현재 Core와 Adapter는 MVP 수준의 Mock 위주로 구현되어 있으며, API route와 contract가 누락되어 있다. 본 계획을 통해 시스템의 정합성을 확보하고 분석 품질을 고도화한다.

## 2. 가치 제안 (Value Proposition)

- **정합성 확보**: 문서에 명시된 데이터 계약과 실제 구현을 일치시켜 소비자(QTS, n8n)와의 연동 안정성을 보장한다.
- **분석 심화**: 단순 키워드 기반 Mock scoring에서 탈피하여, 신뢰도와 긴급도를 포함한 다각도 평가 체계를 구축한다.
- **운영 안정성**: 장중 heavy job 보호 정책을 API 계층에 강제하여 OCI 서버 리소스 경합을 방지한다.
- **확장성**: Generic 및 Workflow Adapter 구현으로 다양한 형태의 인텔리전스 소비를 지원한다.

## 3. 기능 범위 (Scope)

### 3.1 Contract & Model 보완
- [ ] `src/contracts/core.py`: `NewsEvaluation`에 `urgency_score`, `actionability_score`, `content_value_score`, `credibility_breakdown` 추가.
- [ ] `src/contracts/payloads.py`: `GenericInsightPayload`, `WorkflowTriggerPayload` 추가.

### 3.2 Core Logic 고도화
- [ ] `src/core/score.py`: `MockNewsScorer`를 확장하여 신뢰도 평가(Credibility Breakdown) 로직 반영.
- [ ] `src/core/aggregate.py`: Theme/Stock signal 생성 시 관련 뉴스 id(driver_news_ids) 선별 로직 정교화.

### 3.3 Adapter 완성
- [ ] `src/adapters/generic/`: 브리핑 및 랭킹용 Generic Adapter 구현.
- [ ] `src/adapters/workflow/`: n8n 트리거용 Workflow Adapter 구현.

### 3.4 API Route 확장
- [ ] `src/api/routes/ingest.py`: 뉴스 수집 및 batch ingest 엔드포인트.
- [ ] `src/api/routes/signals.py`: Market/Theme/Stock signal 조회 엔드포인트.
- [ ] `src/api/routes/qts.py`, `src/api/routes/generic.py`, `src/api/routes/workflow.py`: Adapter payload 조회 엔드포인트.
- [ ] `src/api/routes/ops.py`: Health check 및 Job status 조회 엔드포인트.

### 3.5 Operational Policy 적용
- [ ] `src/api/dependencies.py`: `MARKET_HOURS_GUARD` 적용하여 장중 write/heavy 작업 차단.

### 3.6 문서 보완
- [ ] `docs/00-pm/prd.md`: 제품 요구사항 정의서(PRD) 작성.
- [ ] `docs/meta/implementation_traceability.md`: 기능 구현 추적 매트릭스 업데이트.

## 4. 구현 전략 (Implementation Strategy)

1.  **Bottom-up Contract Refactoring**: Core contract를 먼저 수정하여 모든 레이어의 데이터 흐름을 맞춘다.
2.  **Logic Enhancement**: Scorer와 Aggregator의 Mock 수준을 낮추고 실제 문서의 수식을 반영한다.
3.  **Adapter Implementation**: QTS 외의 소비자를 위한 Adapter를 독립 모듈로 추가한다.
4.  **API Skeleton & Guard**: 모든 route를 생성하고 `MARKET_HOURS_GUARD`를 우선적으로 적용하여 안전한 API 환경을 조성한다.
5.  **Documentation Sync**: 구현이 완료된 부분은 Traceability 문서에 기록하여 설계와의 gap을 상시 모니터링한다.

## 5. 검증 계획 (Verification Plan)

- **Unit Test**: 확장된 `NewsEvaluation` 필드들이 올바르게 채워지는지 확인 (`tests/test_discovery_quality.py` 등).
- **Integration Test**: 각 API route가 올바른 DTO를 반환하는지 확인.
- **Policy Test**: KST 장중 시간(Mock clock 이용)에 분석 API 호출 시 `409 Conflict` 또는 `MARKET_HOURS_GUARD` 에러가 발생하는지 확인.
- **Adapter Test**: 생성된 Snapshot이 각 Adapter를 통해 예상된 Payload 구조로 변환되는지 확인.

## 6. 일정 및 우선순위 (Timeline & Priority)

1.  **P0 (Critical)**: Contract 보완, API Skeleton & Market Hours Guard.
2.  **P1 (High)**: Core Scorer 고도화, Ingest/Signals API 구현.
3.  **P2 (Normal)**: Generic/Workflow Adapters, PRD 작성.
