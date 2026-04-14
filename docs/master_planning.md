# Trend Intelligence Platform 마스터 기획서

## 1. 요약

Trend Intelligence Platform은 뉴스와 외부 이벤트를 분석해 시장, 테마, 종목 단위의 중립적인 트렌드 인텔리전스를 생성하는 독립 플랫폼이다. 이 시스템의 정체성은 QTS 내부 기능이 아니라, 여러 소비자가 재사용할 수 있는 독립 서비스다.

QTS는 중요한 1차 소비자이지만 시스템의 중심이 아니다. QTS 연동은 `QTS Adapter`를 통해 수행하며, Trend Core는 QTS의 매매 정책, universe 조정 방식, risk override 규칙을 알지 않는다. 같은 Core 산출물은 Generic Adapter를 통해 브리핑, 랭킹, watchlist, 리포트 seed로 변환되고, Workflow Adapter를 통해 n8n 자동화 payload로 변환된다.

초기 운영은 기존 OCI 서버의 3번째 앱으로 배치하는 것을 기본안으로 한다. 단, 개발과 검증은 Windows 11 + WSL2 환경에서 local-first로 진행하고, 필요 시 예비 Windows 11 + WSL2 노트북을 임시 상시 테스트 노드로 사용할 수 있다. 한국 장중(KST 09:00~15:30)에는 heavy analysis, 대량 수집, rebuild, LLM 기반 분석, 대규모 n8n dispatch를 금지한다.

## 2. 제품 비전

본 플랫폼의 비전은 단순 뉴스 수집기가 아니라, 여러 제품과 자동화 흐름이 공유할 수 있는 공통 트렌드 인텔리전스 계층을 제공하는 것이다.

핵심 제품 가치:

- 국내/해외 뉴스 기반 최신 트렌드 해석
- 시장/테마/종목 단위 중립 signal 생성
- QTS 의사결정 보조 payload 제공
- 외부 프로젝트용 generic insight payload 제공
- n8n 및 자동화 시스템용 workflow control payload 제공
- 향후 블로그, 리포트, 알림, 브리핑, 분석 파이프라인으로 확장 가능한 기반 확보

## 3. 목표

- Trend Core를 소비자 독립적인 단일 분석 엔진으로 구현한다.
- QTS, Generic, Workflow 소비자는 Adapter로 분리한다.
- API-first 구조를 초기부터 공식 계층으로 둔다.
- n8n을 upstream orchestrator이자 downstream consumer로 설계에 반영한다.
- 장중 heavy workload 금지 정책을 API, batch, scheduler에 반영한다.
- 로컬 WSL2 검증 후 OCI 단일 서버에 단계적으로 배포한다.
- 추후 QTS 내부 모듈화, 독립 서비스 유지, 별도 서버 분리 중 어느 방향으로도 이동 가능한 경계를 유지한다.

## 4. 비목표

초기 단계에서 다음은 목표가 아니다.

- QTS 내부 모듈로 직접 편입
- 초단위 실시간 뉴스 매매
- 장중 자동 재학습
- 장중 고빈도 이벤트 반응형 매매
- 멀티서버 분산처리
- 독립 대시보드 제품화
- n8n 대규모 자동화 dispatch의 장중 상시 실행

## 5. 1차 범위

- 뉴스 수집: KIS, Kiwoom, RSS, 외신, n8n 유입 데이터
- 정규화: 언어, URL, published_at, 제목/본문 구조 정리
- 중복 제거: URL, content hash, 제목 유사도, source cluster 기준
- 필터링: 시장/테마/종목 관련성 판단
- 점수화: relevance, sentiment, impact, confidence, novelty, urgency, actionability
- 신뢰도 평가: source tier, evidence, corroboration, content quality, freshness, penalty 기반 산정
- 매핑: theme, sector, ticker
- 집계: MarketSignal, ThemeSignal, StockSignal, TrendSnapshot
- Adapter 산출물: QTSInputPayload, GenericInsightPayload, WorkflowTriggerPayload
- API: ingestion, analysis, signals, qts, generic, workflow, ops
- Batch/Scheduler: 장전/장후/야간 중심 실행

## 6. 핵심 아키텍처 원칙

### 6.1 Core는 단일 소스 오브 트루스다

뉴스 정규화, 중복 제거, 필터링, 점수화, 매핑, signal 집계는 Trend Core에서만 수행한다. Adapter나 API route에서 Core 로직을 재구현하지 않는다.

### 6.2 Core는 소비자를 모른다

Trend Core는 QTS의 `market_bias`, `risk_overrides`, `universe_adjustments`를 생성하지 않는다. Core는 중립적인 signal model만 생성한다.

### 6.3 Adapter는 소비자별 언어를 책임진다

- QTS Adapter: 중립 signal을 QTS 의사결정 보조 payload로 변환
- Generic Adapter: 중립 signal을 브리핑/랭킹/watchlist/report seed로 변환
- Workflow Adapter: 중립 signal을 n8n 및 자동화 control payload로 변환

Workflow Adapter는 Generic Adapter가 아니다. Generic Adapter는 사람이 읽거나 외부 프로젝트가 소비할 insight를 만들고, Workflow Adapter는 자동화 시스템이 라우팅/우선순위/후속 작업을 결정할 수 있는 control payload를 만든다.

### 6.4 API Layer는 정식 계층이다

API는 후순위 부가 기능이 아니다. QTS, n8n, 외부 프로젝트, 운영자가 같은 분석 결과를 안정적으로 조회하거나 제한된 작업을 트리거하기 위한 공식 인터페이스다.

### 6.5 Runtime은 분리 가능해야 한다

초기에는 단일 OCI 서버에서 API service, batch worker, scheduler가 함께 운영될 수 있다. 하지만 runtime boundary는 별도 process/container/server로 분리할 수 있게 둔다.

## 7. 배포 전략

### 7.1 Local-first 검증

로컬 Windows 11 + WSL2 환경에서 다음을 먼저 검증한다.

- sample news ingest
- normalize/deduplicate/score/aggregate
- TrendSnapshot 생성
- Adapter payload 생성
- FastAPI local API 응답
- batch dry-run
- PostgreSQL 또는 JSONL 저장 흐름

local-first 전략은 운영 서버 영향을 줄이고, 점수화 품질과 데이터 계약을 빠르게 반복 검증하기 위한 선택이다.

### 7.2 예비 노트북 테스트 노드

필요 시 예비 Windows 11 + WSL2 노트북을 임시 상시 테스트 노드로 사용할 수 있다. 이 노드는 운영 환경과 완전히 같지는 않지만, API와 batch의 장시간 구동 안정성을 확인하는 중간 단계로 유효하다.

### 7.3 OCI 초기 배포

초기 운영은 QTS/Observer와 동일한 OCI 서버 내 3번째 앱으로 배치한다. 이유는 다음과 같다.

- 신규 앱은 장외 시간 중심으로 동작한다.
- 초기 운영 비용과 관리 복잡도를 낮출 수 있다.
- QTS 연계 검증이 같은 서버에 있을 때 단순하다.
- API와 Adapter 계약이 안정화되기 전 별도 서버 운영은 과한 비용을 만들 수 있다.

단, QTS/Observer 안정성을 위해 CPU/메모리 상한, batch 시간 분리, 장중 heavy job 금지 정책을 반드시 적용한다.

## 8. 런타임 전략

초기 runtime mode:

- Local Development Runtime
- OCI Batch Runtime
- API Service Runtime
- n8n Webhook Runtime

미래 runtime option:

- QTS Embedded Runtime: QTS 내부 모듈화가 필요할 때만 검토
- Separate Service Runtime: API 요청량이나 n8n 자동화가 커질 때 검토

## 9. 통합 전략

### 9.1 QTS 통합

QTS는 consumer다. QTS 정책은 QTS Adapter에만 둔다. 초기에는 API 또는 DB read model을 통해 QTS가 payload를 소비하는 구조를 우선한다.

### 9.2 Generic 외부 프로젝트 통합

Generic Adapter는 외부 프로젝트가 재사용할 수 있는 브리핑, 랭킹, watchlist, alert, report seed를 생성한다. 이 output은 특정 자동화 엔진에 종속되지 않는다.

### 9.3 n8n 통합

n8n은 upstream orchestrator이자 downstream consumer다.

- Upstream: webhook을 통해 뉴스/이벤트를 전달할 수 있다.
- Downstream: workflow payload를 조회하거나 dispatch trigger를 받을 수 있다.

n8n 연동은 처음부터 API와 Workflow Adapter의 정식 책임으로 다룬다.

## 10. 로드맵

### Phase 0. 계약 확정

- Core/Adapter/API 경계 확정
- 데이터 계약 확정
- 신뢰도 평가 기준 확정
- 장중 보호 정책 확정

### Phase 1. Core MVP

- ingest, normalize, deduplicate, score, map, aggregate
- TrendSnapshot 생성
- JSONL 또는 dev DB 저장 검증

### Phase 2. Adapter MVP

- QTSInputPayload
- GenericInsightPayload
- WorkflowTriggerPayload

### Phase 3. API MVP

- read-only signal/QTS/generic/workflow API
- analysis trigger API
- ops API
- 장중 write/heavy endpoint guard

### Phase 4. Batch/Scheduler MVP

- 장전/장후/야간 batch job
- job status 기록
- retry/rebuild 정책

### Phase 5. OCI 운영 안정화

- Docker runtime
- CPU/메모리 상한
- 로그/모니터링
- QTS/Observer 리소스 영향 확인

### Phase 6. 구조 재판단

다음 조건 중 2개 이상이면 별도 서버 분리 또는 QTS 내부 모듈화를 재검토한다.

- 장중 상시 구동 필요
- QTS/Observer에 리소스 영향 발생
- n8n 호출량 증가
- API 요청 상시화
- 독립 보안/배포 주기 필요
- QTS 의사결정에 깊은 동기 실행이 필요
