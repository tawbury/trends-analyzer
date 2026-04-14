# 트렌드 인텔리전스 플랫폼 기획서 초안 v0.1

## 1. 문서 메타데이터

* 문서 유형: 기획서 초안
* 문서 ID: TIP-DRAFT-001
* 문서명: QTS 연계형 트렌드 인텔리전스 플랫폼 구축 기획서 초안
* 상태: Draft v0.1
* 작성일: 2026-04-14
* 대상 환경: Windows 11 + WSL2 개발 / OCI ARM 운영 / n8n 연동
* 연관 시스템: QTS, Observer, n8n, Ghost
* 목표 배포 위치: OCI 서버 내 3번째 앱

---

## 2. 문서 목적

본 문서는 뉴스 기반 트렌드 분석 시스템의 초기 기획 및 아키텍처 방향을 정리하기 위한 초안이다.

본 시스템은 다음 목적을 가진다.

* 국내/해외 뉴스 기반 최신 트렌드 분석
* QTS의 종목 선정 및 리스크/비중 조절 보조
* 향후 n8n 워크플로우와 API로 연결되는 범용 인텔리전스 엔진 구축
* 장기적으로 QTS 내부 모듈 전환 또는 별도 서비스 고도화를 모두 수용 가능한 구조 확보

---

## 3. 배경 및 문제 정의

현재 QTS와 Observer는 OCI 서버에서 운영 중이며, 신규 트렌드 분석 앱은 동일한 OCI 서버 내 3번째 앱으로 구동하는 방안을 우선 검토한다.

신규 앱의 주요 특성은 다음과 같다.

* 실시간 초저지연 매매 엔진이 아님
* 뉴스 수집, 필터링, 스코어링, 집계 중심
* 한국 장중(KST 09:00~15:30)에는 원칙적으로 구동하지 않음
* 한국 장외 시간대에 집중적으로 동작
* 향후 QTS 내부 모듈 편입 가능성 존재
* n8n 기반 외부 프로젝트로 결과를 확장 활용할 계획

따라서 본 시스템은 초기에는 QTS와 느슨하게 연동되되, 향후 더 밀접하게 통합될 수 있는 구조가 필요하다.

---

## 4. 핵심 의사결정

### 4.1 초기 운영 위치

초기 운영은 OCI 기존 서버 내 3번째 앱으로 배치하는 것을 기본안으로 채택한다.

채택 이유:

* 현재 OCI 서버에 일정 수준의 여유 리소스가 존재함
* 신규 앱은 장외 시간 위주로 구동 예정이므로 장중 핵심 서비스와 직접 충돌 가능성이 상대적으로 낮음
* 앱별 서버 분리는 운영비용과 관리 포인트 증가 리스크가 큼
* QTS/Observer와의 연계 점검이 초기에는 같은 서버에 있을 때 더 단순함

### 4.2 장중 비구동 원칙

신규 트렌드 앱은 한국 장중(KST 09:00~15:30)에는 기본적으로 구동하지 않는 것을 원칙으로 한다.

장중 비구동 목적:

* QTS/Observer 리소스 보호
* 장중 장애 전파 리스크 최소화
* 분석 작업을 장전/장후 중심으로 고정하여 운영 단순화

예외:

* 운영상 필요시 장중에는 상태 조회 API만 허용 가능
* 장중 재분석/대용량 수집/LLM 분석/배치 작업은 금지

### 4.3 구조 방향

구조는 다음 원칙으로 설계한다.

* 트렌드 코어는 단일화
* 소비 계층은 어댑터로 분리
* 런타임은 분리 가능하게 설계
* API 중심 연동 우선

즉, 기본 방향은 다음과 같다.

* Trend Core 1개
* QTS Adapter 1개
* Generic Adapter 1개
* Workflow Adapter 1개
* API Layer 1개

---

## 5. 시스템 비전

본 시스템은 단순 뉴스 수집기가 아니라, 다음 역할을 수행하는 공통 인텔리전스 레이어를 목표로 한다.

* 뉴스 기반 트렌드 해석
* 시장/테마/종목 단위 신호 생성
* QTS용 의사결정 보조 데이터 제공
* n8n 및 외부 프로젝트용 자동화 데이터 제공
* 향후 블로그, 리포트, 브리핑, 알림, 분석 파이프라인에 재사용 가능한 공통 자산 역할 수행

---

## 6. 범위 정의

### 6.1 1차 범위

* 국내 뉴스 및 외신 헤드라인 수집
* 뉴스 정규화 및 중복 제거
* relevance / sentiment / impact / confidence 점수화
* 테마/섹터/종목 매핑
* 일일 트렌드 스냅샷 생성
* QTS용 payload 생성
* Generic briefing / ranking payload 생성
* n8n 연계용 workflow payload 생성
* 기본 REST API 제공
* 장외 시간 기준 배치 실행

### 6.2 제외 범위

* 초단위 실시간 뉴스 매매
* 장중 자동 재학습
* 장중 고빈도 이벤트 반응형 매매
* 멀티서버 분산처리
* 독립 대시보드 제품화

---

## 7. 운영 전략

### 7.1 초기 운영 전략

초기에는 다음 3단계 운영 전략을 채택한다.

1단계: 로컬 우선 검증

* Windows 11 + WSL2 개발 환경에서 기능 검증
* 배치 실행, API 응답, DB 저장, 로그 구조, 점수화 품질 확인
* 필요시 유휴 노트북을 임시 테스트 서버로 활용

2단계: OCI 단일 서버 배치

* QTS/Observer와 동일 OCI 서버 내 3번째 앱으로 배치
* 장중 비구동 스케줄 준수
* 리소스 상한 및 배치 시간 분리 적용

3단계: 통합 또는 분리 재판단

* 트렌드 앱이 QTS 의사결정에 깊이 결합될 경우 내부 모듈화 검토
* 반대로 범용 자동화 활용이 커질 경우 서비스 분리 검토

### 7.2 서버 분리 판단 기준

다음 조건 중 2개 이상 충족 시 서버 분리를 재검토한다.

* 장중에도 상시 구동이 필요해짐
* CPU/메모리 사용량이 QTS/Observer 안정성에 유의미한 영향 발생
* 외부 프로젝트 수가 늘어나 n8n 호출량 증가
* API 요청이 상시화됨
* 별도 보안/배포 주기가 필요해짐

---

## 8. 아키텍처 원칙

### 원칙 1. 코어는 단일 소스 오브 트루스

뉴스 정규화, 점수화, 신호 집계 로직은 한 곳에만 존재한다.

### 원칙 2. 코어는 소비자를 모른다

코어는 뉴스 해석만 수행하고, QTS/브리핑/n8n 특화 포맷은 어댑터가 책임진다.

### 원칙 3. API 우선 구조

내부 모듈 호출뿐 아니라 REST API, 웹훅, 배치 실행을 모두 수용한다.

### 원칙 4. 장중 보호 우선

장중에는 대용량 분석/수집/LLM 작업을 금지하고 시스템 보호를 우선한다.

### 원칙 5. 나중에 분리 가능한 구조

초기엔 OCI 단일 서버에 두되, 추후 별도 서비스 또는 QTS 내부 모듈로 재배치 가능한 경계를 유지한다.

---

## 9. 논리 아키텍처

### 9.1 상위 구조

* News Sources

  * KIS 뉴스
  * Kiwoom 뉴스
  * RSS / 외신
  * n8n 유입 데이터
* Trend Core

  * Normalize
  * Deduplicate
  * Filter
  * Score
  * Map
  * Aggregate
* Adapter Layer

  * QTS Adapter
  * Generic Adapter
  * Workflow Adapter
* Delivery Layer

  * QTS Embedded Runtime
  * Batch Worker
  * API Service
  * Scheduler
  * n8n Gateway

### 9.2 실행 형태

* 로컬 개발 런타임
* OCI 서버 배치 런타임
* API 서비스 런타임
* n8n 웹훅 연동 런타임

---

## 10. 모듈 상세 설계

### 10.1 Trend Core

역할:

* 뉴스 의미 해석의 공통 엔진

주요 기능:

* 뉴스 정규화
* 중복 제거
* 관련성 평가
* 감성 점수화
* 영향도 점수화
* 신뢰도 추정
* 테마/섹터 분류
* 종목 매핑
* 시장/테마/종목 signal 집계

출력:

* NewsEvaluation
* MarketSignal
* ThemeSignal
* StockSignal
* TrendSnapshot

### 10.2 QTS Adapter

역할:

* 코어 산출물을 QTS가 직접 읽을 수 있는 매매 보조 포맷으로 변환

대표 출력:

* market_bias
* universe_adjustments
* risk_overrides
* sector_weights
* strategy_activation_hints

### 10.3 Generic Adapter

역할:

* 코어 결과를 범용 인사이트 포맷으로 변환

대표 출력:

* daily_briefing
* theme_ranking
* watchlist_candidates
* alert_summary
* report_seed

### 10.4 Workflow Adapter

역할:

* n8n 및 자동화 시스템이 처리 가능한 워크플로우 payload 생성

대표 출력:

* trigger_type
* priority
* recommended_actions
* routing_conditions
* downstream_payload

---

## 11. API 설계 초안

### 11.1 Ingestion API

* POST /api/v1/ingest/news
* POST /api/v1/ingest/batch
* POST /api/v1/ingest/webhook/n8n

### 11.2 Analysis API

* POST /api/v1/analyze/daily
* POST /api/v1/analyze/incremental
* POST /api/v1/analyze/rebuild

### 11.3 Signal API

* GET /api/v1/signals/market
* GET /api/v1/signals/themes
* GET /api/v1/signals/stocks
* GET /api/v1/news/evaluations

### 11.4 QTS API

* GET /api/v1/qts/daily-input
* GET /api/v1/qts/universe-adjustments
* GET /api/v1/qts/risk-overrides

### 11.5 Generic API

* GET /api/v1/generic/briefing
* GET /api/v1/generic/theme-ranking
* GET /api/v1/generic/watchlist
* GET /api/v1/generic/alerts

### 11.6 Workflow API

* GET /api/v1/workflow/payload
* POST /api/v1/workflow/dispatch
* GET /api/v1/workflow/status

### 11.7 Ops API

* GET /api/v1/health
* GET /api/v1/jobs/status
* POST /api/v1/jobs/retry
* GET /api/v1/config/version

---

## 12. 데이터 모델 초안

### 핵심 엔티티

* RawNewsItem
* NormalizedNewsItem
* NewsEvaluation
* ThemeSignal
* StockSignal
* MarketSignal
* TrendSnapshot
* QTSInputPayload
* GenericInsightPayload
* WorkflowTriggerPayload

### 핵심 점수

* relevance_score
* sentiment_score
* impact_score
* confidence_score
* novelty_score
* source_weight
* actionability_score
* urgency_score
* content_value_score

---

## 13. 저장소 구조 초안

### Core Schema

* raw_news
* normalized_news
* news_evaluations
* theme_signals
* stock_signals
* market_signals
* trend_snapshots

### QTS Schema

* qts_daily_inputs
* qts_universe_adjustments
* qts_risk_overrides

### Generic Schema

* generic_briefings
* generic_theme_rankings
* generic_watchlists
* generic_alert_payloads

### Workflow Schema

* workflow_requests
* workflow_outputs
* workflow_dispatch_logs
* webhook_ingest_logs

---

## 14. 배치 및 스케줄 정책

### 기본 원칙

* 장중(KST 09:00~15:30) 배치 작업 금지
* 장전/장후/야간 배치 중심 운영

### 권장 시간대 예시

* 06:00~08:00 KST: 장전 뉴스 정리 및 일일 분석
* 16:00~18:00 KST: 장후 집계 및 재평가
* 20:00~23:00 KST: 외신 반영, 브리핑 생성, n8n 후속 작업

### 장중 허용 항목

* health check
* read-only API 조회
* 로그 확인
* 관리용 lightweight 상태 점검

### 장중 금지 항목

* 대량 뉴스 수집
* LLM 기반 대량 분석
* 재빌드 배치
* DB 전체 재처리
* n8n 대규모 자동화 트리거

---

## 15. 개발 및 배포 전략

### 15.1 개발 환경

* Windows 11
* WSL2
* 안티그래비티 IDE 사용
* Codex, Claude Code, Gemini CLI 병행 활용

### 15.2 개발 방식

* 로컬 우선 검증
* API/배치/DB/로그/점수화 규칙을 로컬에서 먼저 안정화
* 필요시 유휴 노트북을 임시 서버로 활용해 상시 구동 테스트 수행

### 15.3 배포 전략

초기 배포는 OCI 서버 내 3번째 앱으로 진행한다.

권장 배포 순서:

1. 로컬 단위 테스트
2. 로컬 배치 시뮬레이션
3. 로컬 API 테스트
4. 노트북 임시 서버 장시간 테스트(Optional)
5. OCI 스테이징성 배포
6. 스케줄 기반 운영 시작

---

## 16. 운영 판단 비교

### 안 1. 로컬 충분 검증 후 OCI 배포

장점:

* 운영 서버 영향 최소화
* 초기 시행착오를 로컬에서 흡수 가능

단점:

* 서버 환경 차이로 재현 이슈 가능
* OCI 이전 시 추가 튜닝 필요

### 안 2. 노트북 임시 서버 활용

장점:

* 24시간 테스트 가능
* API 및 배치 장시간 구동 검증 가능

단점:

* 운영 환경과 완전 동일하지 않음
* 네트워크/보안/접근 제약 가능

### 안 3. OCI 직접 배치

장점:

* 실제 운영 환경 기준 검증 가능
* QTS/Observer와 통합 테스트 용이

단점:

* 초기 불안정성이 운영 서버에 직접 반영될 수 있음

### 최종 권장

* 기능 검증은 로컬에서 우선
* 필요시 노트북으로 장시간 구동 테스트
* 이후 OCI에 올리는 단계적 전개

---

## 17. 기술 선택 초안

* 언어: Python 3.11+
* API: FastAPI
* 저장소: PostgreSQL 우선, 초기 일부 JSONL 보조 허용
* 캐시/큐: 초기엔 선택 사항, 후속 단계에서 Redis 검토
* 스케줄링: cron 또는 앱 내부 scheduler
* 런타임: Docker 컨테이너 기반 우선
* 배포: OCI 기존 운영 체계에 맞춘 3번째 앱 형태

---

## 18. 리스크 및 대응

### 리스크 1. OCI 리소스 경쟁

대응:

* 장중 비구동 원칙 유지
* CPU/메모리 상한 설정
* 배치 시간 고정

### 리스크 2. 분석 품질 불안정

대응:

* 점수화 기준 분리
* 수동 검증 샘플셋 운영
* 프롬프트 및 룰 버전 관리

### 리스크 3. n8n 연동 과복잡화

대응:

* 초기엔 inbound / outbound 최소 시나리오만 구현
* Workflow Adapter를 별도 계층으로 유지

### 리스크 4. QTS와 결합도 증가

대응:

* QTS 정책은 Adapter 계층에만 위치
* Core는 중립적 signal model 유지

### 리스크 5. 초기 운영 포인트 증가

대응:

* 단일 서버 초기 운영
* 로컬 우선 검증
* 단계별 배포

---

## 19. 단계별 로드맵

### Phase 0. 설계 확정

* 본 초안 리뷰
* 경계/책임/API/DB 계약 확정

### Phase 1. Core MVP

* 뉴스 ingest
* normalize
* deduplicate
* score
* aggregate
* snapshot 생성

### Phase 2. QTS Adapter MVP

* daily input
* universe adjustments
* risk overrides

### Phase 3. Generic / Workflow Adapter MVP

* briefing
* ranking
* workflow payload
* n8n webhook 연동

### Phase 4. OCI 배포 및 운영 안정화

* 장외 시간 스케줄 적용
* 로깅/모니터링/재처리 보강

### Phase 5. 구조 재판단

* QTS 내부 모듈화 여부
* 별도 서버 분리 여부
* 로컬/노트북/OCI 역할 재배치 여부

---

## 20. 최종 제안

초기 전략은 다음으로 정리한다.

* 트렌드 코어는 단일화한다.
* QTS / Generic / Workflow Adapter로 소비 계층을 분리한다.
* 로컬에서 충분히 검증한 뒤 OCI에 3번째 앱으로 배치한다.
* 장중에는 구동하지 않는 원칙으로 설계한다.
* n8n API 연동을 처음부터 고려해 API Layer를 정식 계층으로 포함한다.
* 추후 실매매 밀착도가 커질 경우 QTS 내부 모듈 편입을 재검토한다.
* 범용 자동화 활용이 커질 경우 별도 서버 또는 별도 서비스 분리를 재검토한다.

이 구조는 현재 운영비용을 최소화하면서도, 향후 QTS 통합과 외부 프로젝트 확장을 모두 열어두는 가장 현실적인 방향이다.

---

## 21. 다음 작업 제안

본 초안 승인 이후 바로 이어서 정리할 문서는 다음과 같다.

* 시스템 컨텍스트 다이어그램
* 실제 디렉토리 구조 설계
* API 계약서 초안
* DB 스키마 초안
* 배치 스케줄 설계서
* 로컬/OCI 테스트 계획서
* Codex / Claude Code / Gemini CLI용 메타프롬프트 세트
