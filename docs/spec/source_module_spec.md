# 소스 및 모듈 명세

## 1. 범위

이 문서는 `src/` 하위 소스 구조, 모듈 책임, 의존 방향, 파일 생성 규칙을 정의한다.

현재 프로젝트의 핵심 구조 원칙은 다음과 같다.

- Trend Core는 단일 소스 오브 트루스다.
- Adapter는 소비자별 포맷 변환만 담당한다.
- API는 요청/응답 경계와 실행 진입점만 담당한다.
- Batch/Scheduler는 장외 실행과 job orchestration만 담당한다.

## 2. 권장 디렉토리 구조

```text
src/
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
│   ├── clients/
│   ├── loaders/
│   └── webhook.py
├── scheduler/
├── shared/
│   ├── clock.py
│   ├── market_hours.py
│   └── logging.py
└── workflow/
```

## 3. 의존 방향

허용 방향:

```text
api -> adapters -> core
api -> batch
batch -> ingestion -> core -> db
batch -> adapters -> db
scheduler -> batch
adapters -> contracts
core -> contracts
db -> contracts
shared <- all layers
```

금지 방향:

- `core -> adapters`
- `core -> api`
- `core -> scheduler`
- `core -> workflow dispatch`
- `db -> api`
- `ingestion -> adapters`

## 4. 모듈 책임

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

- n8n용 `WorkflowTriggerPayload` 생성
- `trigger_type`, `priority`, `recommended_actions`, `routing_conditions`, `downstream_payload` 구성

금지:

- HTTP dispatch 직접 수행
- 대량 자동화 정책 우회

### 4.5 `src/api/`

책임:

- FastAPI app 구성
- route registration
- request/response schema 변환
- auth/dependency/market-hours guard

금지:

- Core 알고리즘 구현
- DB query를 route 함수에 직접 작성
- 장중 보호 가드 우회

### 4.6 `src/batch/`

책임:

- batch job orchestration
- source ingest -> core analyze -> adapter generation 순서 제어
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
- 새 알고리즘은 `src/core/`에 두고 adapter나 API에 중복 구현하지 않는다.
- 새 소비자 포맷은 `src/adapters/{consumer}/`에 둔다.
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
