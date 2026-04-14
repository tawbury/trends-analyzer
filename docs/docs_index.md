# 문서 인덱스 및 권위 기준

## 1. 목적

문서 수가 늘어나면 같은 내용을 여러 곳에서 반복하면서 drift가 발생할 수 있다. 이 문서는 각 문서의 역할과 권위 기준을 정의한다.

## 2. 문서 역할

| 문서 | 역할 | 권위 범위 |
|------|------|-----------|
| `master_planning.md` | 제품 방향과 전략 | 제품 비전, 목표/비목표, 범위, 로드맵 |
| `architecture_specification.md` | 상위 아키텍처 | 계층, 경계, runtime separation, integration direction |
| `module_design.md` | 모듈 설계 | 모듈 책임, UseCase, Adapter, Gateway, Ports |
| `api_draft.md` | API 초안 | endpoint group, API 공통 계약, 요청/응답 방향 |
| `data_contract_draft.md` | 데이터 계약 | core signal, consumer payload, score 정의 |
| `runtime_scheduling_policy.md` | 런타임 정책 | 장중 제한, batch window, retry/rebuild, runtime mode |
| `deployment_topology.md` | 배포 토폴로지 | local/laptop/OCI 배포 구조, entrypoint |
| `observability_ops.md` | 운영/관측성 | logs, job ids, correlation ids, dispatch results, health/readiness |
| `open_decisions.md` | 미결 의사결정 | 구현 전 확정해야 할 결정사항 |
| `refactoring_notes.md` | 설계 보정 기록 | 이전 문서의 모호점과 변경 내역 |
| `example_code_appendix.md` | 예시 코드 | 구현 방향을 설명하는 짧은 Python 예시 |
| `docs/spec/*` | 세부 spec | API/source/data/persistence/runtime/news credibility 세부 기준 |

## 3. Source Of Truth 규칙

- 제품 방향은 `master_planning.md`가 우선한다.
- 아키텍처 경계는 `architecture_specification.md`가 우선한다.
- 모듈 책임과 dependency direction은 `module_design.md`와 `docs/spec/source_module_spec.md`가 우선한다.
- API 계약은 `api_draft.md`와 `docs/spec/api_spec.md`가 우선한다.
- 데이터/저장소 계약은 `data_contract_draft.md`, `docs/spec/data_model_spec.md`, `docs/spec/persistence_spec.md`가 우선한다.
- 런타임/스케줄 정책은 `runtime_scheduling_policy.md`와 `docs/spec/batch_runtime_spec.md`가 우선한다.
- 배포 구조는 `deployment_topology.md`가 우선한다.
- 운영/관측성은 `observability_ops.md`가 우선한다.

## 4. 변경 규칙

- 문서 간 내용이 충돌하면 권위 문서를 먼저 수정하고 참조 문서를 맞춘다.
- 새 모듈이 생기면 `module_design.md`, `docs/spec/source_module_spec.md`, `AGENTS.md`를 함께 확인한다.
- 새 endpoint가 생기면 `api_draft.md`와 `docs/spec/api_spec.md`를 함께 갱신한다.
- 새 데이터 필드가 생기면 `data_contract_draft.md`, `docs/spec/data_model_spec.md`, `docs/spec/persistence_spec.md`를 함께 갱신한다.
- 배포 방식이 바뀌면 `deployment_topology.md`와 `runtime_scheduling_policy.md`를 함께 갱신한다.
