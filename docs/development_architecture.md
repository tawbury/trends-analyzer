# 트렌드 인텔리전스 플랫폼 개발용 아키텍처

## 1. 문서 목적

이 문서는 `trend_intelligence_platform_draft_v_0.md`를 구현 관점으로 재정리한 개발용 아키텍처 문서다.

목표는 다음과 같다.

- 초기 MVP 구현자가 모듈 경계와 책임을 빠르게 이해한다.
- QTS, Generic, n8n 소비 계층이 Trend Core와 결합되지 않도록 구현 기준을 고정한다.
- 한국 장중(KST 09:00~15:30) 보호 원칙을 코드와 운영 구조에 반영한다.
- 로컬 WSL2 검증에서 OCI 단일 서버 배포까지 이어지는 개발 순서를 명확히 한다.

## 2. 시스템 성격

이 시스템은 뉴스 기반 트렌드 분석과 의사결정 보조 payload 생성을 담당하는 공통 인텔리전스 레이어다.

실시간 초저지연 매매 엔진이 아니며, 다음 작업에 집중한다.

- 국내 뉴스 및 외신 헤드라인 수집
- 뉴스 정규화 및 중복 제거
- relevance, sentiment, impact, confidence 기반 점수화
- 테마, 섹터, 종목 매핑
- 시장, 테마, 종목 단위 signal 집계
- QTS용 매매 보조 payload 생성
- Generic briefing/ranking/watchlist payload 생성
- n8n 연동용 workflow payload 생성
- 장외 시간대 배치 실행 및 API 조회 제공

## 3. 핵심 설계 원칙

- Trend Core는 단일 소스 오브 트루스다.
- Core는 소비자를 모른다.
- QTS, Generic, Workflow 특화 포맷은 Adapter 계층에서만 처리한다.
- API Layer는 REST API, 웹훅, 배치 실행을 모두 수용한다.
- 런타임은 로컬 개발, OCI 배치, API 서비스, n8n 웹훅 연동으로 분리 가능해야 한다.
- 초기에는 QTS/Observer와 같은 OCI 서버의 3번째 앱으로 운영하되, 별도 서비스 또는 QTS 내부 모듈 전환이 가능해야 한다.
- 장중에는 상태 조회와 lightweight 점검만 허용하고, 대량 수집/분석/재처리/LLM 작업은 금지한다.

## 4. 논리 아키텍처

```text
News Sources
  ├─ KIS News
  ├─ Kiwoom News
  ├─ RSS / Foreign News
  └─ n8n Inbound Data

Ingestion Layer
  ├─ Source Clients
  ├─ Webhook Receiver
  └─ Batch Loader

Trend Core
  ├─ Normalize
  ├─ Deduplicate
  ├─ Filter
  ├─ Score
  ├─ Map
  └─ Aggregate

Adapter Layer
  ├─ QTS Adapter
  ├─ Generic Adapter
  └─ Workflow Adapter

Delivery Layer
  ├─ API Service
  ├─ Batch Worker
  ├─ Scheduler
  ├─ QTS Read Model
  └─ n8n Gateway

Persistence
  ├─ PostgreSQL
  └─ JSONL Local Verification Store
```

## 5. 권장 디렉토리 구조

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

디렉토리 원칙은 다음과 같다.

- `src/core/`는 뉴스 해석과 signal 산출만 담당한다.
- `src/adapters/`는 Core 산출물을 소비자별 payload로 변환한다.
- `src/api/`는 FastAPI 라우팅과 요청/응답 경계만 담당한다.
- `src/batch/`와 `src/scheduler/`는 장외 실행 정책과 job orchestration을 담당한다.
- `src/db/`는 PostgreSQL repository와 로컬 검증용 JSONL 저장소를 분리한다.
- `src/shared/market_hours.py`에는 KST 장중 보호 가드를 둔다.

## 6. 모듈 책임

### 6.1 Ingestion Layer

책임:

- KIS, Kiwoom, RSS, 외신, n8n 유입 데이터를 RawNewsItem으로 수집한다.
- 원본 source, 수집 시각, 원문 제목/본문, URL, 언어, symbol 힌트 등을 보존한다.
- source별 실패가 전체 배치를 중단하지 않도록 source 단위 실패를 기록한다.

주요 출력:

- `RawNewsItem`
- `raw_news`

### 6.2 Trend Core

책임:

- RawNewsItem을 NormalizedNewsItem으로 정규화한다.
- URL, 제목, 본문, source, 시각 기준으로 중복을 제거한다.
- 관련성, 감성, 영향도, 신뢰도, novelty, urgency, actionability를 점수화한다.
- 테마, 섹터, 종목에 매핑한다.
- MarketSignal, ThemeSignal, StockSignal, TrendSnapshot을 생성한다.

Core 금지사항:

- QTS 전용 필드명 생성 금지
- n8n 라우팅 조건 직접 생성 금지
- 브리핑 문구나 블로그용 output 생성 금지
- API response schema에 직접 의존 금지

### 6.3 QTS Adapter

책임:

- TrendSnapshot과 signal을 QTS가 읽을 수 있는 매매 보조 payload로 변환한다.
- QTS 정책은 이 계층에만 둔다.
- Core signal을 직접 매매 명령으로 해석하지 않는다.

대표 출력:

- `market_bias`
- `universe_adjustments`
- `risk_overrides`
- `sector_weights`
- `strategy_activation_hints`

### 6.4 Generic Adapter

책임:

- Core 결과를 사람이 읽거나 범용 서비스가 사용할 수 있는 인사이트 payload로 변환한다.
- 블로그, 리포트, 브리핑, 알림으로 확장 가능한 중립 포맷을 만든다.

대표 출력:

- `daily_briefing`
- `theme_ranking`
- `watchlist_candidates`
- `alert_summary`
- `report_seed`

### 6.5 Workflow Adapter

책임:

- n8n 및 자동화 시스템이 처리할 workflow payload를 생성한다.
- 초기에는 inbound/outbound 최소 시나리오만 구현한다.
- 대규모 자동화 dispatch는 장중 보호 정책을 반드시 통과해야 한다.

대표 출력:

- `trigger_type`
- `priority`
- `recommended_actions`
- `routing_conditions`
- `downstream_payload`

### 6.6 API Service

책임:

- `/api/v1` 네임스페이스를 제공한다.
- ingestion, analysis, signal, qts, generic, workflow, ops API 경계를 유지한다.
- 장중에는 read-only 조회와 health/status 중심으로 제한한다.

## 7. 데이터 계약

### 7.1 핵심 엔티티

| 엔티티 | 책임 |
|--------|------|
| `RawNewsItem` | source에서 수집한 원본 뉴스 |
| `NormalizedNewsItem` | 정규화와 언어/시간/본문 정리 완료 뉴스 |
| `NewsEvaluation` | 뉴스별 relevance/sentiment/impact/confidence 등 평가 결과 |
| `MarketSignal` | 시장 전체 방향성 signal |
| `ThemeSignal` | 테마 단위 signal |
| `StockSignal` | 종목 단위 signal |
| `TrendSnapshot` | 특정 분석 시점의 market/theme/stock signal 묶음 |
| `QTSInputPayload` | QTS 소비용 payload |
| `GenericInsightPayload` | 브리핑/랭킹/알림 소비용 payload |
| `WorkflowTriggerPayload` | n8n 자동화 소비용 payload |

### 7.2 핵심 점수

| 점수 | 의미 |
|------|------|
| `relevance_score` | 투자/시장/테마와의 관련성 |
| `sentiment_score` | 긍정/부정 방향성 |
| `impact_score` | 시장 또는 종목 영향 가능성 |
| `confidence_score` | source와 내용 기반 신뢰도 |
| `novelty_score` | 기존 signal 대비 새로움 |
| `source_weight` | source별 가중치 |
| `actionability_score` | 실제 후속 행동으로 연결 가능한 정도 |
| `urgency_score` | 즉시성 또는 시간 민감도 |
| `content_value_score` | 브리핑/리포트 소재 가치 |

## 8. 저장소 설계

초기 저장소는 PostgreSQL을 우선한다. JSONL은 로컬 검증과 장애 시 최소한의 보조 로그 용도로만 사용한다.

권장 schema 그룹:

```text
Core Schema
  ├─ raw_news
  ├─ normalized_news
  ├─ news_evaluations
  ├─ theme_signals
  ├─ stock_signals
  ├─ market_signals
  └─ trend_snapshots

QTS Schema
  ├─ qts_daily_inputs
  ├─ qts_universe_adjustments
  └─ qts_risk_overrides

Generic Schema
  ├─ generic_briefings
  ├─ generic_theme_rankings
  ├─ generic_watchlists
  └─ generic_alert_payloads

Workflow Schema
  ├─ workflow_requests
  ├─ workflow_outputs
  ├─ workflow_dispatch_logs
  └─ webhook_ingest_logs
```

저장 규칙:

- Core 산출물과 Adapter 산출물은 테이블을 분리한다.
- Adapter payload는 재생성 가능하도록 `trend_snapshot_id`를 참조한다.
- workflow dispatch 결과는 별도 로그로 남긴다.
- 점수화 기준과 프롬프트/룰 버전은 추적 가능해야 한다.

## 9. API 계약 초안

### 9.1 Ingestion API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `POST` | `/api/v1/ingest/news` | 단건 뉴스 수집 | 원칙적 금지 |
| `POST` | `/api/v1/ingest/batch` | 배치 뉴스 수집 | 금지 |
| `POST` | `/api/v1/ingest/webhook/n8n` | n8n 유입 데이터 수신 | lightweight inbound만 예외 검토 |

### 9.2 Analysis API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `POST` | `/api/v1/analyze/daily` | 일일 분석 생성 | 금지 |
| `POST` | `/api/v1/analyze/incremental` | 증분 분석 | 금지 |
| `POST` | `/api/v1/analyze/rebuild` | 전체 재분석 | 금지 |

### 9.3 Signal API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `GET` | `/api/v1/signals/market` | 시장 signal 조회 | 허용 |
| `GET` | `/api/v1/signals/themes` | 테마 signal 조회 | 허용 |
| `GET` | `/api/v1/signals/stocks` | 종목 signal 조회 | 허용 |
| `GET` | `/api/v1/news/evaluations` | 뉴스 평가 조회 | 허용 |

### 9.4 QTS API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `GET` | `/api/v1/qts/daily-input` | QTS 일일 입력 조회 | 허용 |
| `GET` | `/api/v1/qts/universe-adjustments` | universe 조정 조회 | 허용 |
| `GET` | `/api/v1/qts/risk-overrides` | risk override 조회 | 허용 |

### 9.5 Generic API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `GET` | `/api/v1/generic/briefing` | 브리핑 조회 | 허용 |
| `GET` | `/api/v1/generic/theme-ranking` | 테마 랭킹 조회 | 허용 |
| `GET` | `/api/v1/generic/watchlist` | 관심 후보 조회 | 허용 |
| `GET` | `/api/v1/generic/alerts` | 알림 요약 조회 | 허용 |

### 9.6 Workflow API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `GET` | `/api/v1/workflow/payload` | workflow payload 조회 | 허용 |
| `POST` | `/api/v1/workflow/dispatch` | n8n 후속 dispatch | 대규모 dispatch 금지 |
| `GET` | `/api/v1/workflow/status` | workflow 상태 조회 | 허용 |

### 9.7 Ops API

| Method | Path | 용도 | 장중 정책 |
|--------|------|------|-----------|
| `GET` | `/api/v1/health` | health check | 허용 |
| `GET` | `/api/v1/jobs/status` | job 상태 조회 | 허용 |
| `POST` | `/api/v1/jobs/retry` | 실패 job 재시도 | 금지 |
| `GET` | `/api/v1/config/version` | 설정/버전 조회 | 허용 |

## 10. 장중 보호 가드

모든 배치, 분석, 재처리, 대량 dispatch 진입점은 KST 기준 장중 보호 가드를 통과해야 한다.

기본 정책:

- 금지 시간: KST 09:00~15:30
- 허용 작업: health check, read-only API 조회, 로그 확인, lightweight 상태 점검
- 금지 작업: 대량 뉴스 수집, LLM 기반 대량 분석, 재빌드 배치, DB 전체 재처리, n8n 대규모 자동화 트리거

구현 위치:

- `src/shared/market_hours.py`: 시간대 판정
- `src/scheduler/`: 스케줄 등록 전 가드
- `src/batch/runner.py`: job 실행 직전 가드
- `src/api/dependencies.py`: write/heavy endpoint 보호 dependency

권장 인터페이스:

```python
def is_korean_market_hours(now: datetime) -> bool:
    ...

def assert_heavy_job_allowed(now: datetime, job_type: str) -> None:
    ...
```

## 11. 런타임 구성

### 11.1 Local Development Runtime

목적:

- 기능 검증
- API 응답 확인
- 배치 시뮬레이션
- DB 저장 확인
- 로그 구조와 점수화 품질 검증

구성:

- Python 3.11+
- FastAPI local server
- PostgreSQL local 또는 dev DB
- JSONL local store optional
- `.env.local` 또는 로컬 config

### 11.2 OCI Batch Runtime

목적:

- 장전/장후/야간 배치 실행
- QTS/Observer와 같은 서버 내 3번째 앱으로 초기 운영

필수 조건:

- 장중 비구동 스케줄
- CPU/메모리 상한
- 배치 시간 분리
- 실패 로그와 재처리 기준

### 11.3 API Service Runtime

목적:

- QTS, n8n, 외부 자동화가 조회 가능한 API 제공
- 장중에는 read-only 중심으로 제한

필수 조건:

- `/api/v1/health`
- `/api/v1/jobs/status`
- 조회 endpoint와 write/heavy endpoint 분리
- 인증 방식은 배포 전 확정

### 11.4 n8n Webhook Runtime

목적:

- n8n 유입 데이터 수신
- workflow payload 제공
- 후속 자동화 dispatch

필수 조건:

- 초기 inbound/outbound 최소 시나리오만 구현
- dispatch 로그 저장
- 장중 대규모 자동화 금지

## 12. 배치 스케줄

권장 시간대:

| 시간대 KST | 작업 |
|------------|------|
| 06:00~08:00 | 장전 뉴스 정리 및 일일 분석 |
| 16:00~18:00 | 장후 집계 및 재평가 |
| 20:00~23:00 | 외신 반영, 브리핑 생성, n8n 후속 작업 |

초기 job 후보:

- `ingest_morning_news`
- `analyze_daily_snapshot`
- `aggregate_after_market`
- `generate_generic_briefing`
- `generate_qts_payload`
- `generate_workflow_payload`
- `dispatch_workflow_payload`

## 13. 개발 순서

### Phase 0. 설계 확정

- API 계약 확정
- DB schema 초안 확정
- Core/Adapter 경계 확정
- 장중 보호 가드 정책 확정

### Phase 1. Core MVP

- `RawNewsItem`, `NormalizedNewsItem`, `NewsEvaluation`, `TrendSnapshot` 계약 작성
- ingest, normalize, deduplicate, score, aggregate 구현
- 로컬 JSONL 또는 dev PostgreSQL 저장 검증
- 샘플 뉴스 기반 수동 검증셋 작성

### Phase 2. QTS Adapter MVP

- `QTSInputPayload` 계약 작성
- market_bias, universe_adjustments, risk_overrides 변환 구현
- QTS 정책이 Core로 새지 않는지 확인

### Phase 3. Generic / Workflow Adapter MVP

- daily_briefing, theme_ranking, watchlist_candidates 구현
- trigger_type, priority, recommended_actions, routing_conditions 구현
- n8n webhook inbound/outbound 최소 시나리오 검증

### Phase 4. OCI 배포 및 운영 안정화

- Docker runtime 구성
- 장외 시간 스케줄 적용
- 로그/모니터링/재처리 기준 보강
- QTS/Observer 리소스 영향 확인

### Phase 5. 구조 재판단

- QTS 내부 모듈화 여부 판단
- 별도 서버 분리 여부 판단
- 범용 자동화 서비스화 여부 판단

## 14. 리스크와 대응

| 리스크 | 대응 |
|--------|------|
| OCI 리소스 경쟁 | 장중 비구동, CPU/메모리 상한, 배치 시간 고정 |
| 분석 품질 불안정 | 점수화 기준 분리, 수동 검증 샘플셋, 룰/프롬프트 버전 관리 |
| n8n 연동 과복잡화 | inbound/outbound 최소 시나리오부터 구현, Workflow Adapter 분리 |
| QTS 결합도 증가 | QTS 정책은 QTS Adapter에만 위치, Core는 중립 signal model 유지 |
| 초기 운영 포인트 증가 | 로컬 우선 검증, 단일 서버 초기 운영, 단계별 배포 |

## 15. 구현 체크리스트

- Core가 QTS/n8n/브리핑 포맷을 직접 알지 않는가?
- Adapter output이 `TrendSnapshot` 또는 signal을 입력으로 받는가?
- 모든 write/heavy endpoint가 장중 보호 가드를 통과하는가?
- batch job이 장중에 실행되지 않도록 scheduler와 runner 양쪽에서 보호되는가?
- API endpoint가 read-only와 write/heavy로 구분되는가?
- Adapter payload가 재생성 가능하도록 원본 snapshot과 연결되는가?
- n8n dispatch 결과가 별도 로그로 남는가?
- 로컬 검증과 OCI 운영 설정이 분리되어 있는가?
- QTS/Observer 리소스 보호 조건이 배포 설정에 반영되어 있는가?
