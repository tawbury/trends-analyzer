# Source Specification 문서

이 폴더는 권장 `src/` 구조와 모듈 의존 방향을 정의한다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `source_module_spec.md` | `src/` 디렉터리 구조, 모듈 책임, 허용/금지 dependency direction, 파일 생성 규칙 |

## 사용 기준

- 새 모듈이나 디렉터리를 만들기 전에 `source_module_spec.md`를 확인한다.
- UseCase, Contracts, Adapter, Integration, Runtime Dispatch 경계는 이 문서의 dependency direction을 따른다.
- 새 모듈 패턴이 생기면 `../../meta/implementation_traceability.md`와 `../../../AGENTS.md`도 함께 확인한다.
