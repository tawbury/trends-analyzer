# Trends Analyzer 문서 구조

이 폴더는 Trend Intelligence Platform의 설계, 구현 계약, 문서 거버넌스, 참고 자료를 역할별로 분리해 보관한다.

## 폴더 구조

| 폴더 | 목적 |
|------|------|
| `architecture/` | 설계 의도, 시스템 경계, 모듈 책임, 런타임/배포/운영 전략 |
| `specification/` | 구현 계약, API, 데이터, 소스 구조, 런타임 job 명세 |
| `meta/` | 문서 인덱스, 문서 관리 기준, 의사결정, 리팩터링 이력, 구현 추적성 |
| `appendix/` | 예시 코드와 과거 초안 등 비권위 참고 자료 |

## 읽는 순서

처음 읽는 경우:

1. `meta/docs_index.md`
2. `architecture/master_planning.md`
3. `architecture/architecture_specification.md`
4. `architecture/module_design.md`
5. `meta/implementation_traceability.md`

구현 작업을 시작하는 경우:

1. `meta/docs_index.md`
2. `meta/implementation_traceability.md`
3. 작업 대상에 맞는 `specification/` 하위 문서
4. 관련 `architecture/` 문서

## 원칙

- Architecture는 설계 방향과 경계를 설명한다.
- Specification은 구현자가 따라야 할 계약을 정의한다.
- Meta는 문서 권위와 변경 규칙을 관리한다.
- Appendix는 참고 자료이며 source of truth가 아니다.
