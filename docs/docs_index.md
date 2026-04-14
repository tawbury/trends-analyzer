# 문서 인덱스 및 권위 기준

## 문서 메타데이터

- 문서 유형: Documentation Index
- 상태: Draft v0.4
- 권위 범위: 문서 역할, source-of-truth 관계, 변경 규칙
- 상위 문서: 없음
- 관련 문서: `document_metadata_standard.md`, `refactoring_notes.md`, `open_decisions.md`
- 최종 수정일: 2026-04-15

## 1. 목적

문서 수가 늘어나면 같은 내용을 여러 곳에서 반복하면서 drift가 발생할 수 있다. 이 문서는 각 문서의 역할과 권위 기준을 정의한다.

## 2. 문서 역할

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `master_planning.md` | 제품 방향과 전략 | 제품 비전, 목표/비목표, 범위, 로드맵 |
| `architecture_specification.md` | 상위 아키텍처 | 계층, 경계, runtime separation, integration direction |
| `module_design.md` | 모듈 설계 | 모듈 책임, UseCase, Adapter, Gateway, Ports |
| `api_draft.md` | API 제품/개요 초안 | endpoint group, usage intent, consumer-facing API 방향 |
| `data_contract_draft.md` | 데이터 계약 | core signal, consumer payload, score 정의 |
| `runtime_scheduling_policy.md` | 런타임 정책 | 장중 제한, batch window, retry/rebuild, runtime mode |
| `deployment_topology.md` | 배포 토폴로지 | local/laptop/OCI 배포 구조, entrypoint |
| `environment_config.md` | 환경 및 런타임 설정 | local/laptop/OCI 설정 차이, env var group, feature flag, secret/config 경계 |
| `observability_ops.md` | 운영/관측성 | logs, job ids, correlation ids, dispatch results, health/readiness |
| `document_metadata_standard.md` | 문서 관리 기준 | 문서 header, 상태/version, authority scope, parent/related document 표기 |
| `open_decisions.md` | 미결 의사결정 | 구현 전 확정해야 할 결정사항 |
| `refactoring_notes.md` | 설계 보정 기록 | 이전 문서의 모호점과 변경 내역 |
| `example_code_appendix.md` | 예시 코드 | 구현 방향을 설명하는 짧은 Python 예시 |
| `docs/spec/*` | 세부 spec | API/source/data/persistence/runtime/news credibility 세부 기준 |

## 3. Source Of Truth 규칙

- 제품 방향은 `master_planning.md`가 우선한다.
- 아키텍처 경계는 `architecture_specification.md`가 우선한다.
- 모듈 책임과 dependency direction은 `module_design.md`와 `docs/spec/source_module_spec.md`가 우선한다.
- API 제품 방향과 endpoint group은 `api_draft.md`가 우선한다.
- API 구현 계약은 `docs/spec/api_spec.md`가 우선한다.
- request/response 필드, 인증, idempotency, error model, pagination/filter/sort, webhook verification이 충돌하면 `docs/spec/api_spec.md`를 따른다.
- 데이터/저장소 계약은 `data_contract_draft.md`, `docs/spec/data_model_spec.md`, `docs/spec/persistence_spec.md`가 우선한다.
- 런타임/스케줄 정책은 `runtime_scheduling_policy.md`와 `docs/spec/batch_runtime_spec.md`가 우선한다.
- 배포 구조는 `deployment_topology.md`가 우선한다.
- 환경 변수, feature flag, secret/config 경계는 `environment_config.md`가 우선한다.
- 운영/관측성은 `observability_ops.md`가 우선한다.
- 문서 header와 문서 drift 방지 기준은 `document_metadata_standard.md`가 우선한다.

## 4. 변경 규칙

- 문서 간 내용이 충돌하면 권위 문서를 먼저 수정하고 참조 문서를 맞춘다.
- 새 모듈이 생기면 `module_design.md`, `docs/spec/source_module_spec.md`, `AGENTS.md`를 함께 확인한다.
- 새 endpoint가 생기면 `api_draft.md`와 `docs/spec/api_spec.md`를 함께 갱신한다.
- 새 데이터 필드가 생기면 `data_contract_draft.md`, `docs/spec/data_model_spec.md`, `docs/spec/persistence_spec.md`를 함께 갱신한다.
- 배포 방식이 바뀌면 `deployment_topology.md`와 `runtime_scheduling_policy.md`를 함께 갱신한다.
- 새 환경 변수가 생기면 `environment_config.md`를 먼저 갱신하고 관련 runtime/API/ops 문서를 맞춘다.
- 신규 문서 또는 큰 폭으로 수정되는 문서는 `document_metadata_standard.md`의 header 기준을 따른다.

## 5. 문서 메타데이터 적용 기준

v0.3 이후 새 문서에는 다음 메타데이터를 제목 직후에 둔다.

- 문서 유형
- 상태
- 권위 범위
- 상위 문서
- 관련 문서
- 최종 수정일

기존 문서는 즉시 전면 변환하지 않아도 된다. 다만 해당 문서를 크게 수정하는 시점에는 `document_metadata_standard.md` 기준에 맞춘다.
