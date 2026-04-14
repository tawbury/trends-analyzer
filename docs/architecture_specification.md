# Trend Intelligence Platform 아키텍처 명세

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
News Sources / n8n Inbound
        |
        v
Ingestion Layer
        |
        v
Trend Core
  - normalize
  - deduplicate
  - filter relevance
  - score sentiment/impact/confidence/novelty
  - map themes/sectors/tickers
  - aggregate neutral signals
        |
        v
Adapter Layer
  - QTS Adapter
  - Generic Adapter
  - Workflow Adapter
        |
        v
Delivery / Integration Layer
  - REST API
  - inbound webhook
  - outbound workflow trigger
  - repository/storage contracts
        |
        v
Consumers
  - QTS
  - Generic external projects
  - n8n workflows
```

## 3. 계층과 책임

### 3.1 Ingestion Layer

역할:

- source별 client와 loader를 통해 RawNewsItem을 생성한다.
- source별 오류와 수집 상태를 기록한다.
- n8n inbound webhook을 RawNewsItem 또는 external event로 변환한다.

비책임:

- 점수화
- QTS payload 생성
- workflow routing 결정

### 3.2 Trend Core

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

### 3.3 Adapter Layer

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

### 3.4 API Layer

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

### 3.5 Runtime Layer

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
src/batch/      -> batch worker runtime
src/scheduler/  -> schedule runtime
src/ingestion/  -> ingestion runtime
src/adapters/   -> reusable mapping layer
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
