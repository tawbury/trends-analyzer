# Architecture 문서

이 폴더는 Trend Intelligence Platform의 설계 의도, 시스템 경계, 책임 분리, 런타임/배포/운영 전략을 다룬다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `master_planning.md` | 제품 방향, 목표/비목표, 범위, 로드맵 |
| `architecture_specification.md` | 시스템 컨텍스트, 논리 아키텍처, 계층 경계 |
| `module_design.md` | 모듈 책임, UseCase, Adapter, Gateway, Runtime Dispatch, Ports |
| `runtime_scheduling_policy.md` | KST 장중 보호, batch window, retry/rebuild, runtime mode |
| `deployment_topology.md` | local/laptop/OCI 배포 토폴로지와 entrypoint |
| `environment_config.md` | 환경 변수, feature flag, runtime role/mode, n8n secret/config 경계 |
| `observability_ops.md` | logs, job/correlation id, dispatch result, health/readiness |

## 사용 기준

- 설계 방향이나 책임 경계를 판단할 때 이 폴더를 먼저 확인한다.
- 구현 세부 필드, API request/response, DB schema는 `../specification/` 문서를 따른다.
- 문서 간 충돌이 있으면 `../meta/docs_index.md`의 source-of-truth 규칙을 따른다.
