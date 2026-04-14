# 소스 및 모듈 명세

## 1. 범위

이 문서는 `src/` 하위 소스 구조, 모듈 책임, 의존 방향, 파일 생성 규칙을 정의한다.

현재 프로젝트의 핵심 구조 원칙은 다음과 같다.

- Trend Core는 단일 소스 오브 트루스다.
- Adapter는 소비자별 포맷 변환만 담당한다.
- Application UseCase는 API, Batch, Scheduler의 orchestration boundary다.
- Contracts는 Core/Adapter/API/DB/runtime의 계층 간 계약을 고정한다.
- API는 요청/응답 경계와 실행 진입점만 담당하고 UseCase를 호출한다.
- Batch/Scheduler는 장외 실행과 job trigger만 담당하고 Core/Adapter를 직접 조합하지 않는다.

## 2. 권장 디렉토리 구조

```text
src/
├── application/
│   └── use_cases/
├── contracts/
│   ├── api.py                  # MVP default for API transport DTOs
│   ├── api_requests.py        # optional when API DTO grows
│   ├── api_responses.py       # optional when API DTO grows
│   ├── core.py
│   ├── payloads.py
│   ├── ports.py
│   ├── runtime.py
│   └── symbols.py
├── adapters/
│   ├── generic/
│   ├── qts/
│   └── workflow/
├── api/
│   ├── routes/
│   ├── dependencies.py
│   └── app.py
├── batch/
│   ├── jobs/
│   └── runner.py
├── config/
├── core/
│   ├── aggregate.py
│   ├── deduplicate.py
│   ├── filter.py
│   ├── map.py
│   ├── normalize.py
│   └── score.py
├── db/
│   ├── repositories/
│   ├── schema/
│   └── jsonl_store.py
├── ingestion/
│   ├── catalog/
│   ├── clients/
│   ├── loaders/
│   └── webhook.py
├── integration/
│   └── n8n/
├── runtime/
│   └── dispatch/
├── scheduler/
├── shared/
│   ├── clock.py
│   ├── market_hours.py
│   └── logging.py
```

## 3. 의존 방향

허용 방향:

```text
api -> application
batch -> application
scheduler -> batch 또는 application
application -> core
application -> adapters
application -> contracts.ports
application -> integration/n8n ports
application -> runtime/dispatch ports
adapters -> contracts
core -> contracts
core -> shared
integration/n8n -> contracts.payloads
integration/n8n -> contracts.ports
runtime/dispatch -> contracts.runtime
runtime/dispatch -> contracts.ports
db -> contracts.ports
shared <- all layers
```

금지 방향:

- `core -> adapters`
- `core -> api`
- `core -> scheduler`
- `core -> workflow dispatch`
- `api -> core`
- `api -> adapters`
- `batch -> core`
- `batch -> adapters`
- `db -> api`
- `ingestion -> adapters`
- `adapters -> api`
- `adapters/workflow -> integration/n8n`
- `integration/n8n -> adapters/workflow`

## 4. 모듈 책임

### 4.0 `src/contracts/`

책임:

- `core.py`: RawNewsItem, NormalizedNewsItem, NewsEvaluation, MarketSignal, ThemeSignal, StockSignal, TrendSnapshot
- `payloads.py`: QTSInputPayload, GenericInsightPayload, WorkflowTriggerPayload
- `api.py`: MVP 기본 API transport request/response DTO, ErrorResponse, pagination DTO
- `api_requests.py`: API request DTO가 커질 때 선택적으로 분리
- `api_responses.py`: API response DTO가 커질 때 선택적으로 분리
- `runtime.py`: RuntimeMode, JobRequest, JobResult, CorrelationContext
- `symbols.py`: SymbolRecord, SymbolCatalog
- `ports.py`: repository, source, dispatch protocol

규칙:

- Core는 `contracts.core`와 `shared`만 의존한다.
- Adapter는 `contracts.core`와 `contracts.payloads`에 의존한다.
- API는 `contracts.api`와 application use case에 의존한다.
- API transport DTO는 Core signal contract나 Adapter payload contract로 재사용하지 않는다.
- DB는 `contracts.ports`를 구현한다.

### 4.0.2 `src/ingestion/catalog/`

책임:

- KIS official stock master MST ZIP 또는 임시 JSON artifact에서 symbol catalog 원천을 읽는다.
- provider-specific 원천 포맷을 `SymbolRecord`로 정규화한다.
- code/name/alias lookup과 source 실행용 symbol selection을 제공한다.
- validation report를 생성해 종목 코드, 중복, 시장 분포, 분류 분포, 의심 record를 점검한다.
- selection report를 생성해 catalog id, 선택 정책, 선택 종목 수, invalid-code 제외 수를 운영에서 확인할 수 있게 한다.
- QTS/Observer universe의 전일종가 4000원 미만 제외 필터를 적용하지 않는다.
- 전체 시장 catalog와 후속 news discovery 후보군 생성을 위한 입력을 제공한다.

금지:

- QTS 매매 유니버스 정책 구현
- Core signal scoring 구현
- API transport DTO import

### 4.6.1 Provider source 실행 리포트

`src/ingestion/loaders/`의 provider source는 실행 후 `SourceExecutionReport`를 남긴다.

- 요청한 symbol 수
- 성공 symbol 수
- 실패 symbol 수
- 생성된 item 수
- partial success 여부
- 실패 symbol 목록

이 리포트는 Core scoring 결과가 아니라 runtime/source 관측성 자료다.

### 4.0.1 `src/application/use_cases/`

책임:

- API, Batch, Scheduler에서 호출하는 업무 흐름 orchestration
- ingestion port 호출, Core 분석, Adapter 변환, Repository 저장, dispatch 요청 순서 조율
- job_id/correlation_id/runtime_mode 전달

금지:

- Core score 알고리즘 구현
- Adapter payload mapping 구현
- HTTP/webhook 세부 처리 구현

### 4.1 `src/core/`

책임:

- normalize
- deduplicate
- filter
- score
- theme/sector/stock map
- aggregate

입력:

- `RawNewsItem`
- `NormalizedNewsItem`

출력:

- `NewsEvaluation`
- `MarketSignal`
- `ThemeSignal`
- `StockSignal`
- `TrendSnapshot`

금지:

- QTS 전용 정책
- n8n routing condition
- 브리핑 문장 생성
- FastAPI schema import

### 4.2 `src/adapters/qts/`

책임:

- `TrendSnapshot`을 QTS용 payload로 변환한다.
- `market_bias`, `universe_adjustments`, `risk_overrides`, `sector_weights`, `strategy_activation_hints`를 생성한다.

금지:

- 뉴스 정규화/점수화 재구현
- Core score를 직접 수정
- 실제 주문/매매 명령 생성

### 4.3 `src/adapters/generic/`

책임:

- `daily_briefing`
- `theme_ranking`
- `watchlist_candidates`
- `alert_summary`
- `report_seed`

금지:

- QTS 전용 risk override 생성
- n8n dispatch 실행

### 4.4 `src/adapters/workflow/`

책임:

- 자동화/워크플로우용 `WorkflowTriggerPayload` 생성
- `trigger_type`, `priority`, `recommended_actions`, `routing_conditions`, `downstream_payload` 구성

금지:

- HTTP dispatch 직접 수행
- 대량 자동화 정책 우회

### 4.4.1 `src/integration/n8n/`

책임:

- inbound webhook 검증 및 수신
- outbound dispatch 실행
- dispatch result 기록
- n8n retry/failure 상태 수집

금지:

- WorkflowTriggerPayload mapping 구현
- Core signal 계산
- Generic briefing 생성

### 4.4.2 `src/runtime/dispatch/`

책임:

- dispatch 실행 정책 적용
- idempotency key 확인
- retry 가능 여부 판단
- dispatch job 상태 기록
- `integration/n8n` gateway 호출 조율

금지:

- WorkflowTriggerPayload mapping 구현
- n8n webhook signature 검증 구현
- Core signal 계산

### 4.5 `src/api/`

책임:

- FastAPI app 구성
- route registration
- request/response schema 변환
- auth/dependency/market-hours guard

금지:

- Core 알고리즘 구현
- Core/Adapter 직접 orchestration
- DB query를 route 함수에 직접 작성
- 장중 보호 가드 우회

### 4.6 `src/batch/`

책임:

- batch job trigger
- use case 실행
- job status와 실패 사유 기록

필수:

- 모든 heavy job 실행 직전 장중 보호 가드 확인
- 실패 시 source/job 단위 로그 기록

### 4.7 `src/scheduler/`

책임:

- 장전/장후/야간 job schedule 등록
- job 실행 전 policy check

금지:

- job 내부 로직 구현
- QTS/Generic/Workflow payload 직접 생성

### 4.8 `src/db/`

책임:

- PostgreSQL repository
- schema migration 또는 DDL 초안
- JSONL local verification store

금지:

- API response 포맷 생성
- Core score 계산

### 4.9 `src/ingestion/`

책임:

- source client
- source-specific loader
- webhook inbound mapping

출력:

- `RawNewsItem`

### 4.10 `src/shared/`

책임:

- clock/timezone
- KST market hours guard
- logging helpers
- 공통 error types

## 5. 파일 생성 규칙

- 새 데이터 계약은 가능하면 `contracts.py` 또는 역할별 `schemas.py`에 둔다.
- 새 계약은 우선 `src/contracts/`에 둔다.
- 새 업무 흐름은 `src/application/use_cases/`에 둔다.
- 새 알고리즘은 `src/core/`에 두고 adapter나 API에 중복 구현하지 않는다.
- 새 소비자 포맷은 `src/adapters/{consumer}/`에 둔다.
- 새 n8n gateway 로직은 `src/integration/n8n/`에 둔다.
- 새 dispatch 실행 정책은 `src/runtime/dispatch/`에 둔다.
- 새 API route는 `src/api/routes/{group}.py`에 둔다.
- 새 batch job은 `src/batch/jobs/{job_name}.py`에 둔다.
- 새 scheduler 설정은 `src/scheduler/`에 둔다.
- 새 모듈 패턴은 `AGENTS.md`의 `Code Consistency Rules`에 추가한다.

## 6. 테스트 위치 권장

```text
tests/
├── unit/
│   ├── core/
│   ├── adapters/
│   └── shared/
├── integration/
│   ├── api/
│   ├── batch/
│   └── db/
└── fixtures/
```

우선 테스트 대상:

- Core score/aggregate deterministic behavior
- Adapter가 Core output을 변형하지 않고 payload만 생성하는지
- 장중 보호 가드가 write/heavy endpoint와 batch runner에서 모두 동작하는지
- n8n dispatch payload가 로그 가능한지
