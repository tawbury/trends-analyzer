# Trend Intelligence Platform 모듈 설계서

## 1. 모듈 설계 원칙

- Core와 Adapter 책임을 분리한다.
- 분석 output과 consumer-specific payload를 분리한다.
- API, Batch, Scheduler는 Core를 직접 호출할 수 있지만 consumer logic은 Adapter를 통해서만 적용한다.
- repository와 port를 통해 저장소와 외부 시스템 의존성을 격리한다.

## 2. Trend Core

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

## 3. QTS Adapter

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

## 4. Generic Adapter

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

## 5. Workflow Adapter

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

## 6. API Service

책임:

- `/api/v1` route 제공
- request validation
- use case 호출
- response schema 변환
- market-hours guard dependency 적용

권장 route 파일:

- `src/api/routes/ingest.py`
- `src/api/routes/analyze.py`
- `src/api/routes/signals.py`
- `src/api/routes/qts.py`
- `src/api/routes/generic.py`
- `src/api/routes/workflow.py`
- `src/api/routes/ops.py`

## 7. Batch Worker

책임:

- 장외 heavy job 실행
- ingest -> analyze -> persist -> adapter generation 흐름 제어
- job result 기록
- 실패 범위와 재시도 가능성 기록

## 8. Scheduler

책임:

- 장전/장후/야간 batch window에 맞춰 job 실행
- KST market-hours guard 적용
- job overlap 방지

## 9. n8n Gateway

책임:

- inbound webhook 수신
- outbound workflow dispatch
- dispatch result 기록
- n8n 요청량과 실패 상태 추적

주의:

- n8n은 upstream orchestrator이자 downstream consumer다.
- n8n gateway는 Workflow Adapter payload를 전달하지만 payload 생성 정책 자체는 Workflow Adapter가 담당한다.

## 10. Repositories / Ports / Use Cases

권장 port:

- `NewsSourcePort`
- `NewsRepository`
- `EvaluationRepository`
- `SnapshotRepository`
- `PayloadRepository`
- `WorkflowDispatchPort`

권장 use case:

- `IngestNewsUseCase`
- `AnalyzeDailyTrendsUseCase`
- `GenerateQtsPayloadUseCase`
- `GenerateGenericInsightUseCase`
- `GenerateWorkflowPayloadUseCase`
- `DispatchWorkflowPayloadUseCase`

Use case는 application orchestration을 담당하고, Core 알고리즘과 Adapter mapping을 직접 구현하지 않는다.
