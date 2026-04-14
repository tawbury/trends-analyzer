# Data Specification 문서

이 폴더는 Core signal, Adapter payload, 데이터 모델, 저장소, 뉴스 신뢰도 계약을 보관한다.

## 포함 문서

| 문서 | 목적 |
|------|------|
| `data_contract_draft.md` | Core signal, Adapter payload, API/runtime/port 계약 분류 |
| `data_model_spec.md` | 핵심 엔티티, score model, payload 구조 |
| `news_credibility_spec.md` | source tier, confidence breakdown, 뉴스 신뢰도 산정 기준 |
| `persistence_spec.md` | PostgreSQL schema, JSONL 보조 저장소, repository 규칙 |

## 사용 기준

- 새 contract field를 추가할 때 `data_contract_draft.md`와 `data_model_spec.md`를 함께 확인한다.
- 저장소나 repository 규칙은 `persistence_spec.md`를 따른다.
- 신뢰도 산식과 source tier 변경은 `news_credibility_spec.md`를 우선 확인한다.
