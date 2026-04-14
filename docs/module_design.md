# Trend Intelligence Platform 모듈 설계서

## 1. 모듈 설계 원칙

- Core와 Adapter 책임을 분리한다.
- 분석 output과 consumer-specific payload를 분리한다.
- API, Batch, Scheduler는 Core와 Adapter를 직접 조합하지 않고 `application/use_cases`를 호출한다.
- UseCase는 Core, Adapter, Repository, 외부 port 호출 순서를 조율하는 orchestration boundary다.
- 계약은 `contracts` 계층에서 먼저 정의하고 Core/Adapter/API/DB는 해당 계약에 의존한다.
- repository와 port를 통해 저장소와 외부 시스템 의존성을 격리한다.

## 2. Contracts Layer

책임:

- Core signal contracts 정의
- consumer payload contracts 정의
- API DTO 정의
- runtime/job contracts 정의
- repository/port protocol 정의

권장 위치:

- `src/contracts/core.py`
- `src/contracts/payloads.py`
- `src/contracts/api.py`
- `src/contracts/runtime.py`
- `src/contracts/ports.py`

주의:

- Adapter는 API DTO가 아니라 payload contract에 의존한다.
- Core는 API schema를 import하지 않는다.
- DB repository는 repository contract를 구현한다.

## 3. Application / UseCases

책임:

- API route, batch runner, scheduler가 호출하는 업무 흐름을 제공한다.
- Core 분석, Adapter 변환, repository 저장, integration port 호출을 조율한다.
- job_id, correlation_id, requested_by, runtime mode를 전달한다.

권장 use case:

- `IngestNewsUseCase`
- `AnalyzeDailyTrendsUseCase`
- `GenerateQtsPayloadUseCase`
- `GenerateGenericInsightUseCase`
- `GenerateWorkflowPayloadUseCase`
- `DispatchWorkflowPayloadUseCase`

금지:

- Core 알고리즘 직접 구현
- Adapter mapping 직접 구현
- HTTP route validation 직접 구현

## 4. Trend Core

책임:

- RawNewsItem normalize
- normalized news deduplicate
- relevance filter
- sentiment/impact/confidence/novelty/urgency/actionability score
- theme/sector/ticker map
- neutral signal aggregate

주요 output:

- NewsEvaluation
- MarketSignal
- ThemeSignal
- StockSignal
- TrendSnapshot

금지:

- QTS 전용 `market_bias`, `risk_overrides`, `universe_adjustments` 생성
- Generic briefing 최종 문구 생성
- n8n trigger_type/routing_conditions 생성

권장 파일:

- `src/core/normalize.py`
- `src/core/deduplicate.py`
- `src/core/filter.py`
- `src/core/score.py`
- `src/core/credibility.py`
- `src/core/map.py`
- `src/core/aggregate.py`

## 5. QTS Adapter

책임:

- neutral signal을 QTS decision support payload로 변환한다.
- QTS에 필요한 market bias, universe adjustment, risk override 후보를 만든다.

입력:

- TrendSnapshot
- MarketSignal
- ThemeSignal
- StockSignal

출력:

- QTSInputPayload

주의:

- output은 매매 명령이 아니다.
- 낮은 confidence signal은 강한 risk override로 변환하지 않는다.
- QTS 정책은 이 adapter 내부에만 둔다.

## 6. Generic Adapter

책임:

- neutral signal을 범용 insight payload로 변환한다.

출력:

- daily_briefing
- theme_ranking
- watchlist_candidates
- alert_summary
- report_seed

주의:

- Generic Adapter는 n8n workflow control을 만들지 않는다.
- Generic output은 사람이 읽거나 외부 프로젝트가 소비할 수 있는 insight 중심이다.

## 7. Workflow Adapter

책임:

- neutral signal을 자동화 control payload로 변환한다.
- n8n workflow가 routing, priority, recommended action을 결정할 수 있게 한다.

출력:

- trigger_type
- priority
- recommended_actions
- routing_conditions
- downstream_payload

주의:

- Workflow Adapter는 Generic Adapter가 아니다.
- HTTP dispatch는 gateway/runtime 책임이며 adapter 책임이 아니다.
- 낮은 confidence와 높은 urgency 조합은 자동 dispatch보다 manual review를 추천할 수 있다.

## 8. n8n Integration Gateway

책임:

- inbound webhook 수신 및 검증
- outbound dispatch 실행
- dispatch result 기록
- retry 대상 식별
- n8n 요청량과 실패 상태 추적

주의:

- Workflow Adapter payload mapping과 n8n gateway 실행 로직을 섞지 않는다.
- gateway는 `WorkflowTriggerPayload` 계약과 dispatch port에 의존한다.

## 9. Runtime Dispatch

책임:

- dispatch 실행 정책 적용
- idempotency key 확인
- retry 가능 여부 확인
- dispatch job status 기록
- `N8nDispatchGateway` 호출

권장 위치:

- `src/runtime/dispatch/`

주의:

- Workflow Adapter는 payload를 만든다.
- n8n Integration Gateway는 webhook/HTTP 경계를 처리한다.
- Runtime Dispatch는 언제/어떻게 dispatch를 실행할지 결정한다.

## 10. API Service

책임:

- `/api/v1` route 제공
- request validation
- use case 호출
- response schema 변환
- market-hours guard dependency 적용
- use case 호출

권장 route 파일:

- `src/api/routes/ingest.py`
- `src/api/routes/analyze.py`
- `src/api/routes/signals.py`
- `src/api/routes/qts.py`
- `src/api/routes/generic.py`
- `src/api/routes/workflow.py`
- `src/api/routes/ops.py`

## 11. Batch Worker

책임:

- 장외 heavy job 실행
- use case 실행
- job result 기록
- 실패 범위와 재시도 가능성 기록
- Core/Adapter 직접 orchestration 금지

## 12. Scheduler

책임:

- 장전/장후/야간 batch window에 맞춰 job 실행
- KST market-hours guard 적용
- job overlap 방지
- Batch Worker 또는 UseCase trigger만 호출

## 13. Repositories / Ports

권장 port:

- `NewsSourcePort`
- `NewsRepository`
- `EvaluationRepository`
- `SnapshotRepository`
- `PayloadRepository`
- `WorkflowDispatchPort`

Repository는 `src/contracts/ports.py`의 protocol을 구현하고, DB 세부 구현은 `src/db/`에 둔다.
