# API Draft

## 1. API 설계 원칙

- 모든 endpoint는 `/api/v1` 아래에 둔다.
- read-only endpoint와 write/heavy endpoint를 분리한다.
- write/heavy endpoint는 KST 장중 보호 가드를 통과해야 한다.
- QTS, Generic, Workflow output은 각각 별도 endpoint group으로 제공한다.
- n8n은 inbound와 downstream consumer 양쪽 흐름을 모두 가진다.

## 2. Endpoint Groups

| Group | 목적 |
|-------|------|
| Ingestion API | 뉴스 및 외부 이벤트 수집 |
| Analysis API | daily/incremental/rebuild 분석 실행 |
| Signal API | neutral core signal 조회 |
| QTS API | QTS Adapter payload 조회 |
| Generic API | generic insight payload 조회 |
| Workflow API | n8n workflow payload 조회/dispatch |
| Ops API | health, job status, config version |

## 3. Ingestion API

### POST `/api/v1/ingest/news`

목적:

- 단건 또는 소량 뉴스 수집.

장중 정책:

- 원칙적으로 금지.
- n8n lightweight inbound는 별도 정책으로 예외 검토.

### POST `/api/v1/ingest/batch`

목적:

- batch news ingestion.

장중 정책:

- 금지.

### POST `/api/v1/ingest/webhook/n8n`

목적:

- n8n이 upstream orchestrator로 전달하는 외부 뉴스/이벤트 수신.

장중 정책:

- 대량 payload 금지.
- provenance가 없으면 낮은 source tier로 기록.

## 4. Analysis API

### POST `/api/v1/analyze/daily`

목적:

- 일일 TrendSnapshot 생성.

사용 의도:

- 장전 또는 야간 batch에서 사용.

장중 정책:

- 금지.

### POST `/api/v1/analyze/incremental`

목적:

- 새 수집분만 대상으로 증분 분석.

장중 정책:

- 금지.

### POST `/api/v1/analyze/rebuild`

목적:

- 특정 기간의 평가와 signal 재생성.

장중 정책:

- 금지.
- rebuild reason과 requester를 기록.

## 5. Signal API

### GET `/api/v1/signals/market`

목적:

- neutral MarketSignal 조회.

### GET `/api/v1/signals/themes`

목적:

- neutral ThemeSignal 목록 조회.

### GET `/api/v1/signals/stocks`

목적:

- neutral StockSignal 목록 또는 symbol별 조회.

### GET `/api/v1/news/evaluations`

목적:

- 뉴스별 평가 결과, confidence breakdown 확인.

## 6. QTS API

QTS API는 QTS를 소비자로 보는 adapter output API다. 이 API는 QTS 내부 모듈이 아니라 독립 플랫폼의 consumer endpoint다.

### GET `/api/v1/qts/daily-input`

목적:

- QTS가 장전/장후 의사결정 보조 payload를 조회한다.

### GET `/api/v1/qts/universe-adjustments`

목적:

- QTS용 universe adjustment 후보 조회.

### GET `/api/v1/qts/risk-overrides`

목적:

- QTS용 risk override 후보 조회.

## 7. Generic API

### GET `/api/v1/generic/briefing`

목적:

- 범용 daily briefing 조회.

### GET `/api/v1/generic/theme-ranking`

목적:

- theme ranking 조회.

### GET `/api/v1/generic/watchlist`

목적:

- watchlist 후보 조회.

### GET `/api/v1/generic/alerts`

목적:

- alert summary 조회.

## 8. Workflow API

Workflow API는 n8n과 자동화 시스템을 위한 별도 concern이다. Generic API와 섞지 않는다.

### GET `/api/v1/workflow/payload`

목적:

- n8n이 실행할 workflow payload 조회.

### POST `/api/v1/workflow/dispatch`

목적:

- downstream n8n workflow trigger.

장중 정책:

- 대규모 dispatch 금지.
- 낮은 confidence/high urgency 조합은 manual review routing 권장.

### GET `/api/v1/workflow/status`

목적:

- workflow dispatch 상태와 실패 사유 조회.

## 9. Ops API

### GET `/api/v1/health`

목적:

- service health check.

### GET `/api/v1/jobs/status`

목적:

- batch job 상태 조회.

### POST `/api/v1/jobs/retry`

목적:

- 실패 job 수동 재시도.

장중 정책:

- 금지.

### GET `/api/v1/config/version`

목적:

- rules/config/model/prompt/adapter version 조회.
