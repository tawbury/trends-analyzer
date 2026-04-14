# Trend Intelligence Platform 아키텍처 명세

## 문서 메타데이터

- 문서 유형: Architecture Specification
- 상태: Draft v0.4
- 권위 범위: 시스템 컨텍스트, 계층 경계, dependency direction, runtime/integration boundary
- 상위 문서: `docs/architecture/master_planning.md`
- 관련 문서: `docs/architecture/module_design.md`, `docs/specification/source/source_module_spec.md`, `docs/architecture/runtime_scheduling_policy.md`
- 최종 수정일: 2026-04-15

## 1. 시스템 컨텍스트

Trend Intelligence Platform은 뉴스 source와 자동화 유입 데이터를 분석해 중립 signal과 소비자별 payload를 생산하는 독립 플랫폼이다.

외부 시스템:

- News Sources: KIS, Kiwoom, RSS, 외신
- n8n: upstream webhook orchestrator, downstream workflow consumer
- QTS: QTS Adapter payload consumer
- Generic Projects: briefing/ranking/watchlist/report seed consumer
- Operator/IDE Agent: Windows 11 + WSL2 기반 개발 및 문서/코드 생성 workflow
- OCI Server: 초기 운영 배포 대상

## 2. 논리 아키텍처

```text
API / Batch / Scheduler / n8n Inbound
        |
        v
Application / UseCase Layer
  - orchestrate ingestion ports
  - orchestrate analysis and payload generation
        |
        +--> Ingestion Ports / Source Clients
        |      - fetch or receive raw inputs
        |
        +--> Trend Core
        |      - normalize/deduplicate/filter/score/map/aggregate
        |
        +--> Adapter Layer
        |      - QTS Adapter
        |      - Generic Adapter
        |      - Workflow Adapter
        |
        +--> Runtime Dispatch / Integration
               - dispatch policy gate
               - n8n gateway

Contracts Layer
  - core contracts
  - payload contracts
  - API transport DTO contracts
  - runtime/job/port contracts

Consumers
  - QTS
  - Generic external projects
  - n8n workflows
```

## 3. 계층과 책임

### 3.1 Ingestion Layer

역할:

- UseCase가 호출한 source/client/loader port를 통해 RawNewsItem을 생성한다.
- source별 오류와 수집 상태를 기록한다.
- n8n inbound webhook을 RawNewsItem 또는 external event로 변환한다.

구현 경계:

- Ingestion은 Application보다 상위의 독립 orchestration layer가 아니다.
- API route, Batch Worker, Scheduler가 ingestion client를 직접 호출하지 않는다.
- `IngestNewsUseCase`, `AnalyzeDailyTrendsUseCase` 같은 UseCase가 ingestion port를 호출하고 이후 Core 실행 순서를 결정한다.

비책임:

- 점수화
- QTS payload 생성
- workflow routing 결정

### 3.2 Application / UseCase Layer

역할:

- API, Batch Worker, Scheduler가 직접 Core/Adapter/Repository를 조합하지 않도록 orchestration boundary를 제공한다.
- `AnalyzeDailyTrendsUseCase`, `GenerateQtsPayloadUseCase`, `GenerateWorkflowPayloadUseCase`, `DispatchWorkflowPayloadUseCase`처럼 업무 흐름 단위로 의존성을 조합한다.
- ingestion port 호출, Core 실행, Adapter 변환, repository 저장, dispatch 요청을 업무 흐름으로 조율한다.
- transaction boundary, job/correlation id 전달, market-hours guard 이후 실행 흐름, 저장 순서를 명확히 한다.

UseCase가 필요한 이유:

- API route가 얇게 유지된다.
- batch runner가 분석 알고리즘이나 adapter mapping을 직접 알지 않아도 된다.
- scheduler가 job 실행 시점만 결정하고 업무 흐름은 use case에 위임한다.
- Core와 Adapter가 서로를 직접 호출하지 않고 application 계층이 조율한다.

### 3.3 Contracts Layer

역할:

- Core signal contract를 정의한다.
- Adapter payload contract를 정의한다.
- API DTO contract를 정의한다.
- Runtime/job/correlation contract를 정의한다.
- Repository/source/dispatch port contract를 정의한다.

Contracts가 필요한 이유:

- Core, Adapter, API, DB가 서로의 구현에 의존하지 않게 한다.
- Signal API가 QTS payload 용어를 실수로 노출하지 않게 한다.
- n8n gateway가 Workflow Adapter 구현이 아니라 payload contract에 의존하게 한다.

### 3.4 Trend Core

역할:

- 뉴스 정규화
- 중복 제거
- 관련성 필터링
- sentiment/impact/confidence/novelty 점수화
- theme/sector/ticker 매핑
- MarketSignal, ThemeSignal, StockSignal, TrendSnapshot 생성

Core boundary:

- Core는 QTS 매매 정책을 모른다.
- Core는 n8n routing condition을 만들지 않는다.
- Core는 브리핑 문장을 최종 포맷으로 생성하지 않는다.
- Core output은 소비자 독립적인 neutral signal model이어야 한다.

### 3.5 Adapter Layer

역할:

- neutral signal을 consumer-specific payload로 변환한다.

Adapter 구분:

- QTS Adapter: QTS 의사결정 보조 payload
- Generic Adapter: 범용 insight payload
- Workflow Adapter: n8n 및 자동화 control payload

Adapter boundary:

- Adapter는 Core score를 수정하지 않는다.
- Adapter는 Core 알고리즘을 재구현하지 않는다.
- Adapter는 자신의 consumer payload만 책임진다.

### 3.6 API Layer

역할:

- `/api/v1` REST API 제공
- analysis trigger 제공
- read-only signal 조회 제공
- QTS/Generic/Workflow payload 조회 제공
- n8n inbound/outbound integration endpoint 제공
- ops/status endpoint 제공

API-first가 필요한 이유:

- QTS와 직접 결합하지 않고도 통합할 수 있다.
- n8n이 upstream/downstream 양방향으로 연결될 수 있다.
- 로컬 검증과 OCI 운영 검증이 같은 계약을 사용한다.
- 추후 별도 서버 분리 시 외부 계약을 유지할 수 있다.

### 3.7 Integration / n8n Layer

역할:

- n8n inbound webhook 수신
- webhook signature 또는 token 검증
- Workflow Adapter가 만든 payload를 downstream n8n workflow로 dispatch
- dispatch result, retry 대상, failure reason 기록

중요 경계:

- Workflow Adapter는 payload mapping만 수행한다.
- `integration/n8n`은 HTTP/webhook/dispatch와 verification을 수행한다.
- runtime dispatch 정책은 `runtime/dispatch`와 UseCase에서 수행한다.

### 3.8 Runtime / Dispatch Layer

역할:

- UseCase가 업무 흐름상 dispatch를 요청하면 최종 실행 정책 gate로 동작한다.
- dispatch idempotency 확인
- retry/rebuild 금지 시간 확인
- retry 가능 여부 판정
- dispatch execution job 상태 기록
- n8n gateway 호출을 실행 단위로 감싼다.

주의:

- Workflow Adapter payload mapping과 dispatch 실행 정책을 분리한다.
- n8n webhook verification은 `integration/n8n` 책임으로 둔다.
- UseCase는 dispatch 요청과 correlation context 전달을 책임지고, Runtime Dispatch는 idempotency/retryability/실제 dispatch 실행 여부에 대한 최종 책임을 가진다.

### 3.9 Runtime Layer

역할:

- Batch Worker
- API Service
- Scheduler
- Webhook Runtime
- 미래 QTS Embedded Runtime 가능성

Runtime boundary:

- Batch Worker는 장외 heavy analysis를 담당한다.
- API Service는 조회와 제한된 trigger를 담당한다.
- Scheduler는 언제 job을 실행할지 결정한다.
- Webhook Runtime은 n8n inbound를 받는다.
- QTS Embedded Runtime은 미래 검토 대상이며 현재 기본안이 아니다.

## 4. Runtime 분리 전략

초기에는 단일 OCI 서버에서 하나의 앱으로 운영하더라도, code boundary는 다음 분리를 지켜야 한다.

```text
src/api/        -> API service runtime
src/application/-> use case orchestration
src/batch/      -> batch worker runtime
src/scheduler/  -> schedule runtime
src/ingestion/  -> source client and loader implementations called by use cases
src/adapters/   -> reusable mapping layer
src/contracts/  -> cross-layer contracts
src/integration/-> external system gateway
src/runtime/    -> dispatch/runtime policies
src/core/       -> pure analysis core
```

미래에 API service와 batch worker를 별도 container로 분리할 수 있어야 한다.

## 5. 스케줄 제약

한국 장중(KST 09:00~15:30)에는 다음을 금지한다.

- 대량 뉴스 수집
- LLM 기반 대량 분석
- daily/incremental/rebuild analysis
- DB 전체 재처리
- 대규모 n8n dispatch
- job retry/rebuild

장중 허용:

- health check
- read-only API
- job status 조회
- config/version 조회
- 로그 확인
- lightweight 상태 점검

## 6. OCI 배포 가정

초기 OCI 배포는 다음 전제를 둔다.

- 기존 QTS/Observer 서버의 3번째 앱
- Docker container 기반 runtime
- 장외 batch 중심
- CPU/메모리 상한 설정
- QTS/Observer와 batch 시간 충돌 최소화
- read-only API는 장중 허용 가능

운영 중 리소스 영향이 확인되면 별도 서버 분리를 검토한다.

## 7. Local Validation 전략

로컬 검증은 다음 순서를 따른다.

1. sample news ingest
2. normalize/deduplicate
3. score and credibility breakdown
4. theme/sector/ticker map
5. TrendSnapshot aggregate
6. QTS/Generic/Workflow adapter mapping
7. FastAPI route local test
8. batch dry-run
9. JSONL or dev PostgreSQL persistence

예비 Windows 11 + WSL2 노트북은 장시간 API/batch 테스트 노드로 사용할 수 있다.
