# 문서 인덱스 및 권위 기준

## 문서 메타데이터

- 문서 유형: Documentation Index
- 상태: Draft v0.4
- 권위 범위: 문서 역할, source-of-truth 관계, 변경 규칙
- 상위 문서: 없음
- 관련 문서: `docs/meta/document_metadata_standard.md`, `docs/meta/implementation_traceability.md`, `docs/meta/refactoring_notes.md`, `docs/meta/open_decisions.md`
- 최종 수정일: 2026-04-15

## 1. 목적

문서 수가 늘어나면 같은 내용을 여러 곳에서 반복하면서 drift가 발생할 수 있다. 이 문서는 각 문서의 역할과 권위 기준을 정의한다.

## 2. 문서 분류 기준

문서 구조는 문서의 의미를 바로 드러내기 위해 다음 네 범주로 나눈다.

| 분류 | 경로 | 기준 |
|------|------|------|
| Architecture | `docs/architecture/` | 설계 의도, 시스템 경계, 책임, 런타임/배포 전략, 상위 정책 |
| Specification | `docs/specification/` | 구현 계약, API 요청/응답, 데이터 구조, 저장소 schema, source module 구조, runtime job spec |
| Meta | `docs/meta/` | 문서 거버넌스, 인덱스, 의사결정, 리팩터링 이력, 구현 추적성 |
| Appendix | `docs/appendix/` | 예시 코드, 과거 초안, 비권위 참조 자료 |

이 분리는 coding agent가 먼저 읽어야 할 문서 유형을 빠르게 판단하게 하기 위한 것이다. 설계 방향을 확인할 때는 Architecture를 보고, 구현 계약을 작성할 때는 Specification을 보고, 문서 갱신 규칙과 추적성을 확인할 때는 Meta를 본다. Appendix는 참고 자료이며 source of truth로 사용하지 않는다.

## 3. 문서 역할

### 3.1 Architecture

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `docs/architecture/master_planning.md` | 제품 방향과 전략 | 제품 비전, 목표/비목표, 범위, 로드맵 |
| `docs/architecture/architecture_specification.md` | 상위 아키텍처 | 계층, 경계, runtime separation, integration direction |
| `docs/architecture/module_design.md` | 모듈 설계 | 모듈 책임, UseCase, Adapter, Gateway, Ports |
| `docs/architecture/runtime_scheduling_policy.md` | 런타임 정책 | 장중 제한, batch window, retry/rebuild, runtime mode |
| `docs/architecture/deployment_topology.md` | 배포 토폴로지 | local/laptop/OCI 배포 구조, entrypoint |
| `docs/architecture/environment_config.md` | 환경 및 런타임 설정 | local/laptop/OCI 설정 차이, env var group, feature flag, secret/config 경계 |
| `docs/architecture/observability_ops.md` | 운영/관측성 | logs, job ids, correlation ids, dispatch results, health/readiness |

### 3.2 Specification

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `docs/specification/api/api_draft.md` | API 제품/개요 초안 | endpoint group, usage intent, consumer-facing API 방향 |
| `docs/specification/api/api_spec.md` | API 구현 명세 | `/api/v1` request/response, 인증, idempotency, error model, webhook verification |
| `docs/specification/data/data_contract_draft.md` | 데이터 계약 | core signal, consumer payload, score 정의 |
| `docs/specification/data/data_model_spec.md` | 데이터 모델 명세 | 핵심 엔티티, score model, payload 구조 |
| `docs/specification/data/news_credibility_spec.md` | 뉴스 신뢰도 명세 | source tier, confidence breakdown, 신뢰도 산정 기준 |
| `docs/specification/data/persistence_spec.md` | 저장소 명세 | PostgreSQL schema, JSONL 보조 저장소, repository 규칙 |
| `docs/specification/source/source_module_spec.md` | source/module 명세 | `src/` 구조, dependency direction, 파일 생성 규칙 |
| `docs/specification/runtime/batch_runtime_spec.md` | batch/runtime 명세 | batch job, scheduler, KST 장중 보호, runtime job 계약 |

### 3.3 Meta

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `docs/meta/docs_index.md` | 문서 인덱스 | 문서 구조, 분류 기준, source-of-truth 관계 |
| `docs/meta/document_metadata_standard.md` | 문서 관리 기준 | 문서 header, 상태/version, authority scope, parent/related document 표기 |
| `docs/meta/implementation_traceability.md` | 구현 추적성 | 문서 개념에서 source directory/file로의 매핑, MVP 구현 slice, doc-to-code update rule |
| `docs/meta/open_decisions.md` | 미결 의사결정 | 구현 전 확정해야 할 결정사항 |
| `docs/meta/refactoring_notes.md` | 설계 보정 기록 | 이전 문서의 모호점과 변경 내역 |
| `docs/meta/specification_index.md` | specification 문서 인덱스 | specification 문서 목록과 유지보수 규칙 |

### 3.4 Appendix

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `docs/appendix/example_code_appendix.md` | 예시 코드 | 구현 방향을 설명하는 짧은 Python 예시 |
| `docs/appendix/development_architecture.md` | 개발용 아키텍처 참조 | 과거 개발용 통합 아키텍처. 현재 source of truth 아님 |
| `docs/appendix/trend_intelligence_platform_draft_v_0.md` | 원본 초안 | 과거 기획 초안 참조. 현재 source of truth 아님 |
| `docs/appendix/source_extension_notes.md` | 외부 소스 확장 참고 | KIS/Kiwoom 이후 provider 추가 절차와 후보. 현재 source of truth 아님 |
| `docs/appendix/observer_universe_review.md` | Observer universe 검토 | Observer universe 분석과 symbol catalog 판단 근거. 현재 source of truth 아님 |

## 4. Source Of Truth 규칙

- 제품 방향은 `docs/architecture/master_planning.md`가 우선한다.
- 아키텍처 경계는 `docs/architecture/architecture_specification.md`가 우선한다.
- 모듈 책임과 dependency direction은 `docs/architecture/module_design.md`와 `docs/specification/source/source_module_spec.md`가 우선한다.
- API 제품 방향과 endpoint group은 `docs/specification/api/api_draft.md`가 우선한다.
- API 구현 계약은 `docs/specification/api/api_spec.md`가 우선한다.
- request/response 필드, 인증, idempotency, error model, pagination/filter/sort, webhook verification이 충돌하면 `docs/specification/api/api_spec.md`를 따른다.
- 데이터/저장소 계약은 `docs/specification/data/data_contract_draft.md`, `docs/specification/data/data_model_spec.md`, `docs/specification/data/persistence_spec.md`가 우선한다.
- 런타임/스케줄 정책은 `docs/architecture/runtime_scheduling_policy.md`와 `docs/specification/runtime/batch_runtime_spec.md`가 우선한다.
- 배포 구조는 `docs/architecture/deployment_topology.md`가 우선한다.
- 환경 변수, feature flag, secret/config 경계는 `docs/architecture/environment_config.md`가 우선한다.
- 운영/관측성은 `docs/architecture/observability_ops.md`가 우선한다.
- 문서 header와 문서 drift 방지 기준은 `docs/meta/document_metadata_standard.md`가 우선한다.
- 문서 개념에서 코드 위치로의 매핑과 MVP 구현 slice는 `docs/meta/implementation_traceability.md`가 우선한다.

## 5. 변경 규칙

- 문서 간 내용이 충돌하면 권위 문서를 먼저 수정하고 참조 문서를 맞춘다.
- 새 모듈이 생기면 `docs/architecture/module_design.md`, `docs/specification/source/source_module_spec.md`, `AGENTS.md`를 함께 확인한다.
- 새 endpoint가 생기면 `docs/specification/api/api_draft.md`와 `docs/specification/api/api_spec.md`를 함께 갱신한다.
- 새 데이터 필드가 생기면 `docs/specification/data/data_contract_draft.md`, `docs/specification/data/data_model_spec.md`, `docs/specification/data/persistence_spec.md`를 함께 갱신한다.
- 배포 방식이 바뀌면 `docs/architecture/deployment_topology.md`와 `docs/architecture/runtime_scheduling_policy.md`를 함께 갱신한다.
- 새 환경 변수가 생기면 `docs/architecture/environment_config.md`를 먼저 갱신하고 관련 runtime/API/ops 문서를 맞춘다.
- 새 UseCase, route, contract, runtime concern이 생기면 `docs/meta/implementation_traceability.md`의 매핑도 함께 확인한다.
- 신규 문서 또는 큰 폭으로 수정되는 문서는 `docs/meta/document_metadata_standard.md`의 header 기준을 따른다.

## 6. 문서 메타데이터 적용 기준

v0.4 이후 새 문서에는 다음 메타데이터를 제목 직후에 둔다.

- 문서 유형
- 상태
- 권위 범위
- 상위 문서
- 관련 문서
- 최종 수정일

기존 문서는 즉시 전면 변환하지 않아도 된다. 다만 해당 문서를 크게 수정하는 시점에는 `docs/meta/document_metadata_standard.md` 기준에 맞춘다.
