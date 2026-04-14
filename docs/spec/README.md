# Spec 문서 인덱스

이 폴더는 `docs/development_architecture.md`를 유지보수 가능한 세부 구현 문서로 분리해 보관한다.

## 문서 목록

| 문서 | 목적 |
|------|------|
| `api_spec.md` | `/api/v1` REST API, 장중 정책, 요청/응답 계약 |
| `source_module_spec.md` | 권장 `src/` 디렉토리, 모듈 책임, 의존 방향 |
| `data_model_spec.md` | 핵심 엔티티, 점수 모델, payload 계약 |
| `news_credibility_spec.md` | 뉴스 신뢰도 산정 기준, source tier, confidence breakdown |
| `persistence_spec.md` | PostgreSQL schema 그룹, JSONL 보조 저장소, repository 규칙 |
| `batch_runtime_spec.md` | 배치 job, 스케줄, KST 장중 보호 가드, 런타임 구성 |

## 유지보수 규칙

- API endpoint가 추가되면 `api_spec.md`를 먼저 갱신한다.
- 새 모듈이나 디렉토리를 추가하면 `source_module_spec.md`와 `AGENTS.md`의 `Code Consistency Rules`를 함께 갱신한다.
- 데이터 계약 필드가 바뀌면 `data_model_spec.md`와 `persistence_spec.md`를 함께 갱신한다.
- 뉴스 source 등급, 신뢰도 산식, confidence breakdown이 바뀌면 `news_credibility_spec.md`와 `data_model_spec.md`를 함께 갱신한다.
- 배치 job, scheduler, n8n dispatch 정책이 바뀌면 `batch_runtime_spec.md`를 갱신한다.
- `docs/development_architecture.md`는 상위 구조 문서로 유지하고, 세부 구현 변경은 이 폴더의 spec 문서에 먼저 반영한다.
