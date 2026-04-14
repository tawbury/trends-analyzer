# Meta 문서

이 폴더는 문서 구조, 문서 관리 기준, 구현 추적성, 미결 의사결정, 리팩터링 이력을 관리한다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `docs_index.md` | 전체 문서 구조, 분류 기준, source-of-truth 관계 |
| `document_metadata_standard.md` | 문서 metadata header와 문서 상태/version 기준 |
| `implementation_traceability.md` | 문서 개념에서 source directory/file로의 매핑, MVP 구현 slice, doc-to-code update rule |
| `open_decisions.md` | 구현 전 확정해야 할 미결 의사결정 |
| `refactoring_notes.md` | 설계 보정 이력과 변경 이유 |
| `specification_index.md` | specification 문서 목록과 유지보수 규칙 |

## 사용 기준

- 문서가 충돌하면 `docs_index.md`를 먼저 확인한다.
- 새 문서나 큰 변경을 만들 때 `document_metadata_standard.md`를 따른다.
- 구현 작업을 시작할 때 `implementation_traceability.md`로 문서와 코드 위치를 연결한다.
