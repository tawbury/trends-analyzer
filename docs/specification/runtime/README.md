# Runtime Specification 문서

이 폴더는 batch job, scheduler, runtime job, 장중 보호 구현 기준을 보관한다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `batch_runtime_spec.md` | batch job, scheduler, KST 장중 보호 가드, 로컬/OCI/API/n8n 런타임 구성 |

## 사용 기준

- batch runner, scheduler, runtime job 상태를 구현할 때 이 문서를 확인한다.
- 상위 정책은 `../../architecture/runtime_scheduling_policy.md`를 따른다.
- 장중 보호 원칙은 KST 09:00~15:30 heavy job 차단을 기본값으로 둔다.
