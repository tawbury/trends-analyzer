# API Specification 문서

이 폴더는 `/api/v1` API의 제품 방향과 구현 계약을 보관한다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `api_draft.md` | API endpoint group, usage intent, consumer-facing API 방향 |
| `api_spec.md` | 구현자가 따라야 할 request/response, auth, idempotency, error model, webhook verification 계약 |

## 사용 기준

- API 제품 방향과 endpoint group은 `api_draft.md`를 확인한다.
- 구현 계약은 `api_spec.md`를 source of truth로 사용한다.
- request/response 필드, 인증, idempotency, pagination/filter/sort, webhook verification이 충돌하면 `api_spec.md`를 따른다.
