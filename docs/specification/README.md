# Specification 문서

이 폴더는 구현자가 따라야 할 세부 계약을 보관한다.

## 하위 폴더

| 폴더 | 목적 |
|------|------|
| `api/` | API endpoint, request/response, auth, idempotency, webhook verification |
| `data/` | Core signal, Adapter payload, data model, persistence, news credibility |
| `source/` | 권장 `src/` 구조, dependency direction, 모듈 생성 규칙 |
| `runtime/` | batch job, scheduler, runtime job, KST 장중 보호 구현 기준 |

## 사용 기준

- 코드 구현 시 실제 계약은 이 폴더의 문서를 우선한다.
- 상위 설계 의도는 `../architecture/` 문서를 확인한다.
- 문서 구조와 권위 관계는 `../meta/docs_index.md`를 따른다.
