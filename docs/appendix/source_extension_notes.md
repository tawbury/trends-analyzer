# 외부 소스 확장 참고 노트

## 1. 문서 메타데이터

- 문서 유형: 비권위 구현 참고
- 상태: Draft v0.1
- 권위 범위: Phase 1 이후 source provider 확장 후보와 추가 절차 참고
- 상위 문서: `../architecture/environment_config.md`, `../specification/source/source_module_spec.md`
- 관련 문서: `../architecture/module_design.md`, `../meta/implementation_traceability.md`
- 최종 수정일: 2026-04-15

## 2. 현재 Phase 1 범위

현재 실데이터 검증 범위는 KIS와 Kiwoom으로 제한한다.

- KIS: 국내주식 종목투자의견 응답을 우선 `RawNewsItem`으로 변환하고, 응답이 없으면 현재가/시세 계열 응답을 fallback으로 변환한다.
- Kiwoom: 국내주식 종목정보/시세 계열 TR 응답을 `RawNewsItem`으로 변환한다.
- 두 provider 모두 완전한 뉴스 본문 제공자가 아니므로 `mapping_type`을 통해 research/market-data-derived item임을 명시한다.
- provider 원문 응답은 `RawNewsItem.metadata.provider_payload`에 문자열 JSON으로 보존한다.

이 방식은 Core가 provider-specific schema를 알지 못하게 유지하면서, 실데이터가 현재 MVP scoring/aggregation/QTS payload 흐름을 통과할 수 있는지 검증하기 위한 임시 연결이다.

## 3. 향후 확장 후보

다음 후보는 아직 구현하지 않는다.

| 후보 | 예상 위치 | 구현 시 주의사항 |
|------|-----------|------------------|
| Naver News API 또는 검색 기반 대안 | `src/ingestion/clients/naver_client.py`, `src/ingestion/loaders/naver_news_loader.py` | title/body/url/published_at 품질과 검색어 정책을 먼저 정의해야 한다. |
| Google News-compatible collection | `src/ingestion/clients/google_news_client.py`, `src/ingestion/loaders/google_news_loader.py` | 공식 API 부재/약관/수집 안정성을 별도로 검토해야 한다. |
| RSS/feed ingestion | `src/ingestion/clients/rss_client.py`, `src/ingestion/loaders/rss_loader.py` | feed별 신뢰도 tier와 중복 제거 기준이 필요하다. |
| 기타 금융/뉴스 API | provider별 client/loader 쌍 | provider 응답은 Core로 직접 전달하지 않고 `RawNewsItem`으로 정규화한다. |

## 4. 새 provider 추가 절차

1. `src/ingestion/clients/{provider}_client.py`에 인증/HTTP/session 로직을 둔다.
2. `src/ingestion/loaders/{provider}_loader.py`에서 provider 응답을 `RawNewsItem`으로 변환한다.
3. `src/shared/config.py`에 최소 환경 변수만 추가한다.
4. `src/bootstrap/container.py`의 source factory에 provider 이름을 등록한다.
5. provider loader mapping 테스트를 추가한다.
6. `docs/architecture/environment_config.md`에 필요한 환경 변수를 추가한다.

## 5. Core 보호 원칙

- Core는 KIS, Kiwoom, Naver, Google, RSS 같은 provider 이름을 분기 조건으로 사용하지 않는다.
- provider-specific 필드는 `metadata`에만 보존한다.
- scoring 개선이 필요하면 source tier, credibility, language, symbol inference 같은 중립 속성으로 승격한 뒤 contracts 문서를 먼저 갱신한다.
