# Trends Analyzer Project Rules

> [!CAUTION]
> ## Agent Context Sync Required
>
> 이 규칙은 `/home/tawbu/projects/trends-analyzer` 및 하위 폴더에서 작업하는 모든 Codex 세션에 적용한다.
>
> 작업을 시작하기 전 이 파일의 **Current Goal** 섹션과 **Code Consistency Rules** 섹션을 확인한다.
> 새 모듈, 함수, 데이터 계약, 실행 패턴을 만들면 **Code Consistency Rules**에 패턴을 기록해 프로젝트 전체 일관성을 유지한다.
>
> | 시점 | 수행 내용 | 필수 |
> |------|----------|------|
> | 작업 시작 전 | 가능한 경우 `git branch --show-current`로 브랜치 확인 후 **Current Goal** 섹션 확인 및 필요 시 업데이트 | 필수 |
> | 코드 생성/수정 중 | 새 모듈/함수/데이터 계약/실행 패턴 생성 시 **Code Consistency Rules**에 기록 | 필수 |
> | 작업 완료 시 | **Current Goal** 완료 조건을 확인하고 결과를 반영 | 필수 |
> | 레거시 파일 발생 시 | 프로젝트 폴더 내 `backups/` 폴더를 생성하고 레거시 파일을 백업한 다음 원본 파일은 삭제 | 필수 |
>
> 이 규칙을 건너뛰면 컨텍스트 불일치로 구조와 코드 패턴이 어긋날 수 있으므로 생략하지 않는다.

이 파일은 현재 폴더 `/home/tawbu/projects/trends-analyzer` 및 그 하위 폴더에서 Codex가 우선 적용해야 할 프로젝트 전용 작업 규칙이다.
기준 문서는 `docs/trend_intelligence_platform_draft_v_0.md`이다.

## Current Goal

<!-- 에이전트가 작업 시작 시 현재 작업 내용에 맞게 이 섹션을 업데이트한다. 이 폴더가 git 저장소가 아닐 수 있으므로 브랜치 확인이 실패하면 해당 사실을 기록한다. -->

| 항목 | 내용 |
|------|------|
| 작업 브랜치 | `main` |
| 목표 | 문서 close-out: 메타데이터 확인, API DTO MVP 구조 정리, 구현 traceability 문서 추가 |
| 최근 완료 | 최종 정합성 패스: ingestion/usecase, runtime dispatch, API 문서 권위, API DTO 범위 정리 |
| 완료 조건 | 구현 traceability 문서를 추가하고 docs_index/관련 권위 문서에 doc-to-code handoff 기준 반영 |

## Code Consistency Rules

<!-- 새로운 모듈/함수/계약/패턴을 만들 때 여기에 기록하여 프로젝트 전체 일관성을 유지한다. -->

| 패턴 | 위치 | 설명 |
|------|------|------|
| Trend Core | `src/core/` | 뉴스 정규화, 중복 제거, 필터링, 점수화, 테마/섹터/종목 매핑, signal 집계의 단일 소스 오브 트루스 |
| Application UseCases | `src/application/use_cases/` | API, Batch, Scheduler의 orchestration boundary. Core/Adapter/Repository 호출 순서를 조율 |
| Contracts | `src/contracts/` | Core signal, consumer payload, API DTO, runtime/job 계약을 분리해 계층 간 의존성을 고정 |
| Adapter Layer | `src/adapters/` | QTS/Generic/Workflow 소비자별 payload 변환 책임. Core가 소비자 포맷을 알지 않도록 분리 |
| n8n Integration | `src/integration/n8n/` | n8n inbound webhook, outbound dispatch, verification, dispatch result 기록. Workflow Adapter와 분리 |
| Runtime Dispatch | `src/runtime/dispatch/` | workflow payload dispatch 실행 정책, idempotency, retry, dispatch status 관리. Adapter mapping과 n8n HTTP gateway와 분리 |
| API Layer | `src/api/` | FastAPI 기반 `/api/v1` REST API, 웹훅, ops endpoint 경계 유지 |
| Batch/Scheduler | `src/batch/` 또는 `src/scheduler/` | 장전/장후/야간 배치 중심. KST 09:00~15:30 대량 작업 금지 가드 포함 |
| Persistence | `src/db/` | PostgreSQL 우선. 초기 검증용 JSONL은 보조 저장소로만 사용 |
| Workflow Payload | `src/adapters/workflow/` | neutral signal을 자동화/워크플로우 payload로 변환. n8n 인증, webhook, HTTP dispatch는 담당하지 않음 |
| News Credibility | `src/core/credibility.py` | source tier, source_weight, evidence/corroboration, content quality, conflict penalty 기반 신뢰도 평가 |

## Project Context

- 이 프로젝트는 독립 Trend Intelligence Platform이며, QTS는 Adapter를 통해 연동되는 소비자 중 하나다.
- 목표는 뉴스 기반 트렌드 분석, QTS 의사결정 보조 payload, n8n/API 연동용 범용 인텔리전스 엔진 구축이다.
- 대상 환경은 Windows 11 + WSL2 개발, OCI ARM 운영, n8n 연동이다.
- 초기 운영 위치는 QTS/Observer와 동일한 OCI 서버 내 3번째 앱으로 본다.
- 실시간 초저지연 매매 엔진이 아니라 뉴스 수집, 필터링, 스코어링, 집계 중심 시스템이다.

## Architecture Rules

- Trend Core는 단일 소스 오브 트루스로 유지한다.
- 뉴스 정규화, 중복 제거, 필터링, 점수화, 테마/섹터/종목 매핑, signal 집계 로직은 코어에 둔다.
- Core는 소비자를 몰라야 한다. QTS, Generic, Workflow 특화 포맷은 Adapter 계층에서 처리한다.
- 소비 계층은 `QTS Adapter`, `Generic Adapter`, `Workflow Adapter`로 분리한다.
- API Layer를 정식 계층으로 두고 REST API, 웹훅, 배치 실행을 모두 수용할 수 있게 설계한다.
- 초기에는 단일 OCI 서버 배치를 허용하되, 런타임과 모듈 경계는 추후 별도 서비스 또는 QTS 내부 모듈로 분리 가능해야 한다.

## Operational Rules

- 한국 장중(KST 09:00~15:30)에는 기본적으로 트렌드 앱의 배치, 대량 수집, LLM 분석, 재처리 작업을 금지한다.
- 장중에는 health check, read-only API 조회, 로그 확인, lightweight 상태 점검만 허용한다.
- 주요 배치 시간대는 장전 06:00~08:00 KST, 장후 16:00~18:00 KST, 야간 20:00~23:00 KST를 우선 고려한다.
- QTS/Observer 안정성을 항상 우선한다. CPU/메모리 상한, 배치 시간 분리, 장애 전파 최소화를 설계에 반영한다.
- 장중 상시 구동, 리소스 영향, n8n 호출 증가, 상시 API 요청, 별도 보안/배포 주기가 필요해지면 서버 분리를 재검토한다.

## Scope Rules

- 1차 범위는 국내 뉴스 및 외신 헤드라인 수집, 뉴스 정규화, 중복 제거, relevance/sentiment/impact/confidence 점수화, 테마/섹터/종목 매핑, 일일 트렌드 스냅샷, QTS/Generic/Workflow payload, 기본 REST API, 장외 배치 실행이다.
- 초단위 실시간 뉴스 매매, 장중 자동 재학습, 장중 고빈도 이벤트 반응형 매매, 멀티서버 분산처리, 독립 대시보드 제품화는 초기 범위에서 제외한다.
- QTS 정책은 Adapter 계층에만 둔다. Core는 중립적 signal model을 유지한다.
- n8n 연동은 초기에는 inbound/outbound 최소 시나리오부터 구현하고 Workflow Adapter를 별도 계층으로 유지한다.

## API And Data Rules

- API는 `/api/v1` 네임스페이스를 기본으로 한다.
- Ingestion API, Analysis API, Signal API, QTS API, Generic API, Workflow API, Ops API의 경계를 유지한다.
- 핵심 엔티티는 `RawNewsItem`, `NormalizedNewsItem`, `NewsEvaluation`, `ThemeSignal`, `StockSignal`, `MarketSignal`, `TrendSnapshot`, `QTSInputPayload`, `GenericInsightPayload`, `WorkflowTriggerPayload`를 우선 기준으로 삼는다.
- 핵심 점수는 `relevance_score`, `sentiment_score`, `impact_score`, `confidence_score`, `novelty_score`, `source_weight`, `actionability_score`, `urgency_score`, `content_value_score`를 기준으로 삼는다.
- 저장소는 PostgreSQL을 우선으로 하고, 초기 검증 단계에서만 JSONL 보조를 허용한다.

## Implementation Preferences

- 언어는 Python 3.11+를 우선한다.
- API는 FastAPI를 우선한다.
- 런타임은 Docker 컨테이너 기반을 우선한다.
- 스케줄링은 cron 또는 앱 내부 scheduler 중 기존 운영 체계에 더 단순한 방식을 택한다.
- Redis 같은 캐시/큐는 초기 필수 요소로 두지 말고 후속 단계에서 필요성이 확인되면 검토한다.
- 로컬 WSL2에서 API, 배치, DB, 로그, 점수화 품질을 먼저 검증한 뒤 OCI 배포를 진행한다.

## Workspace Scope Rules

- 기본 작업 범위는 현재 폴더 `/home/tawbu/projects/trends-analyzer` 및 하위 폴더로 제한한다.
- QTS, Observer, Deployment 등 형제 프로젝트 파일은 사용자가 명시적으로 요청한 경우에만 읽거나 수정한다.
- 현재 프로젝트 내부 작업은 가능한 한 상대 경로를 사용한다.
- 크로스 프로젝트 변경이 필요하면 변경 대상과 이유를 먼저 분리해서 설명하고, 사용자 지시 범위 안에서만 수행한다.

## Source Of Record Priority

1. 현재 프로젝트 코드와 실제 파일 구조
2. 이 `AGENTS.md`
3. `docs/trend_intelligence_platform_draft_v_0.md`
4. 기타 `docs/` 설계 문서
5. 환경별 설정 파일

코드와 문서가 충돌하면 현재 코드와 실제 런타임 동작을 먼저 확인하고, 문서를 갱신해야 하는지 별도로 판단한다.

## Safety Rules

- QTS/Observer 운영 안정성을 해칠 수 있는 변경을 기본적으로 피한다.
- 장중(KST 09:00~15:30) 보호 원칙을 우회하는 스케줄, 재처리, 대량 수집, LLM 분석 작업을 만들지 않는다.
- 배치/분석 작업에는 장중 실행 방지, 리소스 상한, 실패 시 중단/재시도 정책을 명확히 둔다.
- 운영성 변경에는 로그, 상태 확인 API, 재처리 가능성, n8n 호출량 영향을 함께 검토한다.
- 외부 API, n8n dispatch, OCI 배포, 대량 데이터 처리처럼 부작용이 큰 작업은 사용자 승인과 실행 범위를 명확히 한 뒤 진행한다.

## Delivery Workflow

- 구현 전 기존 코드 구조와 문서의 책임 경계를 먼저 확인한다.
- 기능 추가는 Phase 1 Core MVP, Phase 2 QTS Adapter MVP, Phase 3 Generic/Workflow Adapter MVP, Phase 4 OCI 운영 안정화 순서를 우선한다.
- 장중 보호 원칙을 위반하는 자동 실행, 대량 처리, 스케줄 추가는 기본적으로 만들지 않는다.
- QTS 연동을 강화할 때도 Core와 Adapter 경계를 깨지 않는다.
- 외부 자동화나 블로그/리포트/브리핑 확장 요구가 생기면 Generic/Workflow payload를 통해 확장한다.
