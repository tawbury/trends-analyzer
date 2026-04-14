# 저장소 명세

## 1. 범위

이 문서는 PostgreSQL 중심 저장소 구조와 로컬 검증용 JSONL 저장소 사용 규칙을 정의한다.

원칙:

- PostgreSQL을 1차 저장소로 사용한다.
- JSONL은 초기 로컬 검증과 장애 분석 보조 용도로만 사용한다.
- Core 산출물과 Adapter payload를 분리 저장한다.
- Adapter payload는 `trend_snapshot_id` 기준으로 재생성 가능해야 한다.
- DB 계층은 `src/contracts/ports.py`의 repository protocol을 구현한다.
- DB 모델은 API DTO에 의존하지 않는다.

## 2. Schema 그룹

### 2.1 Core Schema

| 테이블 | 목적 |
|--------|------|
| `raw_news` | source에서 수집한 원본 뉴스 |
| `normalized_news` | 정규화 및 중복 제거 기준이 적용된 뉴스 |
| `news_evaluations` | 뉴스별 점수화 결과 |
| `news_credibility_scores` | 뉴스별 신뢰도 breakdown과 산정 버전 |
| `theme_signals` | 테마 단위 signal |
| `stock_signals` | 종목 단위 signal |
| `market_signals` | 시장 단위 signal |
| `trend_snapshots` | 특정 분석 시점의 signal 묶음 |

### 2.2 QTS Schema

| 테이블 | 목적 |
|--------|------|
| `qts_daily_inputs` | QTS 일일 입력 payload |
| `qts_universe_adjustments` | universe 조정 payload |
| `qts_risk_overrides` | risk override payload |

### 2.3 Generic Schema

| 테이블 | 목적 |
|--------|------|
| `generic_briefings` | daily briefing payload |
| `generic_theme_rankings` | theme ranking payload |
| `generic_watchlists` | watchlist candidate payload |
| `generic_alert_payloads` | alert summary payload |

### 2.4 Workflow Schema

| 테이블 | 목적 |
|--------|------|
| `workflow_requests` | workflow payload 생성 요청 |
| `workflow_outputs` | workflow payload 결과 |
| `workflow_dispatch_logs` | n8n 또는 downstream dispatch 로그 |
| `webhook_ingest_logs` | webhook inbound 수신 로그 |

## 3. 관계 규칙

- `normalized_news.raw_news_id`는 `raw_news.id`를 참조한다.
- `news_evaluations.normalized_news_id`는 `normalized_news.id`를 참조한다.
- `news_credibility_scores.news_evaluation_id`는 `news_evaluations.id`를 참조한다.
- `market_signals.snapshot_id`, `theme_signals.snapshot_id`, `stock_signals.snapshot_id`는 `trend_snapshots.id`를 참조한다.
- QTS/Generic/Workflow payload 테이블은 `trend_snapshot_id`를 보존한다.
- dispatch log는 `workflow_payload_id`와 dispatch result를 함께 기록한다.

## 4. Repository 규칙

권장 위치:

```text
src/contracts/ports.py
src/db/repositories/
├── raw_news_repository.py
├── normalized_news_repository.py
├── news_evaluation_repository.py
├── news_credibility_repository.py
├── signal_repository.py
├── snapshot_repository.py
├── qts_payload_repository.py
├── generic_payload_repository.py
├── workflow_payload_repository.py
├── dispatch_log_repository.py
└── symbol_catalog_repository.py
```

규칙:

- API route에서 SQL을 직접 작성하지 않는다.
- Core에서 직접 connection을 관리하지 않는다.
- Application UseCase는 repository protocol에 의존하고, 실제 PostgreSQL 구현은 dependency injection으로 주입한다.
- Repository 구현은 `contracts.core`, `contracts.payloads`, `contracts.ports`에만 의존한다.
- Repository 구현은 FastAPI request/response DTO에 의존하지 않는다.
- repository는 명시적 method 이름을 사용한다.
- batch job은 repository 또는 service 계층을 통해 저장한다.
- write 작업은 가능한 한 idempotent key를 가진다.
- 신뢰도 breakdown은 최종 `confidence_score`만 저장하지 말고 산정 근거를 재검토할 수 있게 별도 JSON 또는 정규화 컬럼으로 보존한다.
- symbol catalog repository는 full market catalog를 저장하며 QTS 가격 필터가 적용된 universe artifact와 섞지 않는다.

예시 method:

```python
class RawNewsRepository:
    async def insert_many(self, items: list[RawNewsItem]) -> InsertResult:
        ...

class SnapshotRepository:
    async def get_latest(self) -> TrendSnapshot | None:
        ...
```

## 5. JSONL 로컬 검증 저장소

목적:

- 로컬 WSL2 검증
- 샘플 뉴스 평가 결과 보관
- DB 미구성 상태의 초기 개발 보조

권장 위치:

```text
data/local/
├── raw_news.jsonl
├── normalized_news.jsonl
├── news_evaluations.jsonl
├── trend_snapshots.jsonl
├── adapter_payloads.jsonl
└── symbol_catalog/
    ├── YYYYMMDD_symbol_catalog.json
    └── latest_symbol_catalog.json
```

규칙:

- 운영 저장소로 사용하지 않는다.
- JSONL schema는 `docs/specification/data/data_model_spec.md`의 계약을 따른다.
- 민감 정보나 API token을 저장하지 않는다.
- PostgreSQL 도입 이후에도 테스트 fixture와 디버그 용도로만 유지한다.

## 6. Migration 및 Schema 버전 관리

초기에는 SQL 파일 또는 migration tool을 선택한다.

권장:

- `src/db/schema/` 아래 DDL 초안을 둔다.
- schema version table을 둔다.
- destructive migration은 금지하거나 명시 승인 후 수행한다.
- DB schema 변경 시 `docs/specification/data/data_model_spec.md`와 `docs/specification/data/persistence_spec.md`를 함께 갱신한다.

## 7. 보관 정책

초기 제안:

- raw news: 90일 이상 보관
- normalized news/evaluations: 180일 이상 보관
- snapshots/payloads: 1년 이상 보관
- dispatch logs: 180일 이상 보관

운영 서버 리소스와 분석 품질 검증 필요에 따라 조정한다.
