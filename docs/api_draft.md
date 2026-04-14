# API Draft

## 문서 메타데이터

- 문서 유형: API Product Draft
- 상태: Draft v0.4
- 권위 범위: API endpoint group, product-level usage intent, consumer-facing API 방향
- 상위 문서: `architecture_specification.md`
- 관련 문서: `docs/spec/api_spec.md`, `data_contract_draft.md`, `runtime_scheduling_policy.md`
- 최종 수정일: 2026-04-15

## 0. 문서 역할

이 문서는 API의 제품/개요 수준 초안이다. endpoint group, 사용 의도, 소비자별 API 경계를 설명한다.

구현 시 상세 계약의 source of truth는 `docs/spec/api_spec.md`다. request/response 필드, 인증, idempotency, error model, pagination/filter/sort 규칙이 충돌하면 `docs/spec/api_spec.md`를 우선한다.

## 1. API 설계 원칙

- 모든 endpoint는 `/api/v1` 아래에 둔다.
- read-only endpoint와 write/heavy endpoint를 분리한다.
- write/heavy endpoint는 KST 장중 보호 가드를 통과해야 한다.
- QTS, Generic, Workflow output은 각각 별도 endpoint group으로 제공한다.
- n8n은 inbound와 downstream consumer 양쪽 흐름을 모두 가진다.
- API route는 Core/Adapter/Repository를 직접 조합하지 않고 Application UseCase만 호출한다.
- API transport DTO는 `src/contracts/api.py` 또는 규모 증가 시 `src/contracts/api_requests.py`, `src/contracts/api_responses.py`에 둔다.
- API transport DTO는 Core signal contract나 Adapter payload contract로 재사용하지 않는다.

## 2. 공통 API 계약

### 2.1 인증

초기 운영 전 최소 인증 방식을 확정해야 한다.

권장 기본안:

- 내부 운영 API: Bearer token 또는 reverse proxy 인증
- n8n webhook: shared secret header 또는 HMAC signature
- 로컬 개발: 명시적 `DEV_AUTH_DISABLED=true` 같은 로컬 전용 설정만 허용

모든 운영 요청은 `requested_by`를 추적할 수 있어야 한다.

### 2.2 Idempotency

write/heavy endpoint는 중복 실행을 막기 위해 idempotency key를 지원한다.

권장 header:

- `Idempotency-Key`
- `X-Correlation-Id`

적용 대상:

- `POST /api/v1/ingest/batch`
- `POST /api/v1/analyze/daily`
- `POST /api/v1/analyze/rebuild`
- `POST /api/v1/workflow/dispatch`
- `POST /api/v1/jobs/retry`

정책:

- 같은 `Idempotency-Key`와 같은 request body는 같은 job 또는 dispatch 결과를 반환한다.
- 같은 key로 다른 body가 들어오면 `IDEMPOTENCY_CONFLICT`를 반환한다.
- key 보관 기간은 운영 정책으로 확정하되 MVP에서는 24시간 이상을 권장한다.

### 2.3 Error Response Model

모든 에러는 같은 구조를 사용한다.

```json
{
  "error": {
    "code": "MARKET_HOURS_GUARD",
    "message": "장중에는 heavy analysis를 실행할 수 없습니다.",
    "details": {
      "blocked_window": "09:00-15:30 KST",
      "operation": "analyze_daily"
    }
  },
  "correlation_id": "corr_20260414_0001"
}
```

권장 에러 코드:

- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `MARKET_HOURS_GUARD`
- `IDEMPOTENCY_CONFLICT`
- `JOB_NOT_FOUND`
- `DISPATCH_FAILED`
- `INTERNAL_ERROR`

### 2.4 Async Job Behavior

분석, rebuild, dispatch처럼 오래 걸릴 수 있는 작업은 동기 완료를 전제하지 않는다.

권장 응답:

```json
{
  "job_id": "job_20260414_daily_001",
  "status": "queued",
  "correlation_id": "corr_20260414_0001"
}
```

상태 조회:

- `GET /api/v1/jobs/status?job_id=job_20260414_daily_001`

### 2.5 Pagination And Filters

목록 조회 API는 다음 규칙을 따른다.

- 기본 `limit`: 50
- 최대 `limit`: 500
- `offset` 또는 cursor 중 하나를 endpoint별로 명시한다.
- 시간 필터는 `from`, `to`, `as_of`를 ISO 8601로 받는다.
- symbol/theme/source 필터는 문자열 배열을 허용할 수 있다.
- 정렬은 `sort`와 `order`를 사용한다.
- 기본 정렬은 최신 생성 시각 내림차순이다.

### 2.6 Webhook Verification

n8n webhook은 다음 정보를 검증/기록한다.

- `X-Webhook-Source`
- `X-Correlation-Id`
- shared secret 또는 signature
- payload size
- received_at
- upstream provenance

검증 실패 시 `401` 또는 `403`을 반환하고 `webhook_ingest_logs`에 실패 사유를 남긴다.

### 2.7 Signal DTO와 Payload DTO 분리

Signal API는 neutral DTO만 반환한다.

- 허용: `bias_hint`, `impact_score`, `confidence_score`, `driver_themes`
- 금지: `market_bias`, `risk_overrides`, `universe_adjustments`

`market_bias`는 QTS Adapter가 `bias_hint`를 QTS 문맥으로 변환한 결과이며, Signal API에 노출하지 않는다.

## 3. Endpoint Groups

| Group | 목적 |
|-------|------|
| Ingestion API | 뉴스 및 외부 이벤트 수집 |
| Analysis API | daily/incremental/rebuild 분석 실행 |
| Signal API | neutral core signal 조회 |
| QTS API | QTS Adapter payload 조회 |
| Generic API | generic insight payload 조회 |
| Workflow API | n8n workflow payload 조회/dispatch |
| Ops API | health, job status, config version |

## 4. Ingestion API

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

## 5. Analysis API

### POST `/api/v1/analyze/daily`

목적:

- 일일 TrendSnapshot 생성.

사용 의도:

- 장전 또는 야간 batch에서 사용.

장중 정책:

- 금지.

요청 예시:

```json
{
  "as_of": "2026-04-14T08:00:00+09:00",
  "mode": "daily",
  "requested_by": "scheduler",
  "dry_run": false
}
```

응답 예시:

```json
{
  "job_id": "job_20260414_daily_001",
  "status": "queued",
  "correlation_id": "corr_20260414_0001"
}
```

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

## 6. Signal API

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

## 7. QTS API

QTS API는 QTS를 소비자로 보는 adapter output API다. 이 API는 QTS 내부 모듈이 아니라 독립 플랫폼의 consumer endpoint다.

### GET `/api/v1/qts/daily-input`

목적:

- QTS가 장전/장후 의사결정 보조 payload를 조회한다.

응답 예시:

```json
{
  "snapshot_id": "snapshot_20260414_morning",
  "market_bias": "risk_on",
  "universe_adjustments": ["005930", "000660"],
  "risk_overrides": [],
  "confidence_score": 0.72,
  "adapter_version": "qts-adapter-v0.1"
}
```

### GET `/api/v1/qts/universe-adjustments`

목적:

- QTS용 universe adjustment 후보 조회.

### GET `/api/v1/qts/risk-overrides`

목적:

- QTS용 risk override 후보 조회.

## 8. Generic API

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

## 9. Workflow API

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

요청 예시:

```json
{
  "payload_id": "workflow_20260414_evening",
  "dispatch_mode": "manual",
  "requested_by": "operator",
  "reason": "evening workflow dispatch"
}
```

응답 예시:

```json
{
  "dispatch_id": "dispatch_20260414_001",
  "status": "queued",
  "correlation_id": "corr_20260414_0002"
}
```

### GET `/api/v1/workflow/status`

목적:

- workflow dispatch 상태와 실패 사유 조회.

## 10. Ops API

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
