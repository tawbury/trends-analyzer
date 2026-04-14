# 문서 메타데이터 표준

## 1. 문서 메타데이터

- 문서 유형: 문서 관리 기준
- 상태: Draft v0.4
- 권위 범위: 문서 header 표준, 문서 권위 범위 표시, drift 방지 규칙
- 상위 문서: `docs_index.md`
- 관련 문서: `refactoring_notes.md`, `open_decisions.md`
- 최종 수정일: 2026-04-15

## 2. 목적

문서 세트가 커지면 같은 주제가 여러 문서에 반복된다. 문서마다 권위 범위와 상위 문서를 명확히 표시하지 않으면 구현 에이전트가 오래된 설명을 기준으로 코드를 작성할 위험이 있다.

이 표준은 각 문서의 첫 부분에 가벼운 메타데이터를 두어 문서 drift를 줄이기 위한 기준이다.

## 3. 권장 Header 형식

신규 문서는 제목 직후에 다음 block을 둔다.

```markdown
## 문서 메타데이터

- 문서 유형: Architecture Spec
- 상태: Draft v0.3
- 권위 범위: 계층, 경계, dependency direction
- 상위 문서: `master_planning.md`
- 관련 문서: `module_design.md`, `docs/spec/source_module_spec.md`
- 최종 수정일: 2026-04-14
```

이미 작성된 문서에는 한 번에 모두 적용하지 않아도 된다. 다만 v0.3 이후 새 문서와 크게 수정되는 문서는 이 형식을 따른다.

## 4. 필드 정의

| 필드 | 의미 |
|------|------|
| 문서 유형 | planning, architecture, module design, API spec, runtime policy, ops 등 문서 성격 |
| 상태 | draft, accepted, deprecated 등 문서 상태와 버전 |
| 권위 범위 | 이 문서가 source of truth로 책임지는 범위 |
| 상위 문서 | 충돌 시 먼저 확인해야 하는 상위 문서 |
| 관련 문서 | 함께 갱신해야 할 문서 |
| 최종 수정일 | 마지막 의미 있는 수정일 |

## 5. 상태 값

권장 상태 값:

- `Draft v0.x`: 구현 전 설계 초안
- `Accepted v1.0`: MVP 구현 기준으로 승인된 문서
- `Superseded`: 다른 문서로 대체됨
- `Deprecated`: 더 이상 사용하지 않음

현재 문서 세트는 구현 전이므로 `Draft v0.4`를 기본으로 둔다.

## 6. 충돌 해결 규칙

- 제품 방향 충돌: `master_planning.md` 우선
- 아키텍처 경계 충돌: `architecture_specification.md` 우선
- 모듈/소스 구조 충돌: `module_design.md`와 `docs/spec/source_module_spec.md` 우선
- API 제품 방향 충돌: `api_draft.md` 우선
- API 구현 계약 충돌: `docs/spec/api_spec.md` 우선
- 데이터/저장소 충돌: `data_contract_draft.md`, `docs/spec/data_model_spec.md`, `docs/spec/persistence_spec.md` 우선
- 런타임/스케줄 충돌: `runtime_scheduling_policy.md` 우선
- 환경 설정 충돌: `environment_config.md` 우선

충돌을 발견하면 참조 문서만 고치지 말고 권위 문서를 먼저 수정한다.

## 7. 구현 에이전트 작업 규칙

- 문서 수정 시 해당 문서의 권위 범위를 먼저 확인한다.
- 새 endpoint는 API 문서와 spec 문서를 함께 수정한다.
- 새 source module은 module design과 source module spec을 함께 수정한다.
- 새 환경 변수는 `environment_config.md`를 먼저 갱신한다.
- 문서의 권위 범위를 벗어난 내용을 추가해야 한다면 관련 권위 문서 링크를 남긴다.
