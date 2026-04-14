# API Spec

## 1. 범위

이 문서는 Trend Intelligence Platform의 `/api/v1` REST API 계약을 정의한다.

API 계층의 목적은 다음과 같다.

- Trend Core와 Adapter 산출물을 외부 소비자가 조회할 수 있게 한다.
- 뉴스 수집, 분석 실행, workflow dispatch 같은 write/heavy 작업을 명시적으로 분리한다.
- 한국 장중(KST 09:00~15:30)에는 read-only 조회와 lightweight 상태 점검만 허용한다.

## 2. 공통 규칙

- 모든 endpoint는 `/api/v1` 하위에 둔다.
- API route는 `src/api/routes/`에 그룹별로 분리한다.
- write/heavy endpoint는 `src/api/dependencies.py`의 장중 보호 dependency를 통과해야 한다.
- response는 Core 내부 모델을 그대로 노출하지 않고 API schema로 변환한다.
- timestamp는 ISO 8601 문자열을 사용하고 timezone을 명시한다.
- pagination이 필요한 조회 API는 `limit`, `offset` 또는 cursor 방식을 명시적으로 선택한다.
- 초기 인증 방식은 배포 전 확정하되, 운영 배포 전에는 최소 Bearer token 또는 reverse proxy 인증을 둔다.

## 3. 장중 정책

| 분류 | 장중 허용 여부 | 예시 |
|------|----------------|------|
| read-only 조회 | 허용 | signal, qts payload, briefing, health |
| lightweight inbound | 예외 검토 | 작은 n8n webhook 수신 |
| 분석 실행 | 금지 | daily, incremental, rebuild |
| 대량 수집 | 금지 | batch ingest |
| workflow dispatch | 대규모 dispatch 금지 | n8n 후속 자동화 |
| job retry | 금지 | 실패 job 재실행 |

장중 금지 endpoint는 기본적으로 `409 Conflict` 또는 정책 전용 에러 코드를 반환한다.

권장 에러 payload:

```json
{
  "error": {
    "code": "MARKET_HOURS_GUARD",
    "message": "Heavy job is blocked during KST market hours.",
    "details": {
      "market": "KR",
      "blocked_window": "09:00-15:30 KST",
      "job_type": "analyze_daily"
    }
  }
}
```

## 4. Ingestion API

### 4.1 POST `/api/v1/ingest/news`

용도:

- 단건 뉴스 또는 소량 뉴스 payload를 수집한다.

장중 정책:

- 원칙적으로 금지한다.
- 운영상 필요 시 lightweight inbound만 허용하도록 별도 flag를 둔다.

요청 예시:

```json
{
  "source": "rss",
  "source_id": "rss:example:20260414:001",
  "title": "AI chip demand accelerates in Asia",
  "body": "Article body or summary",
  "url": "https://example.com/news/001",
  "published_at": "2026-04-14T06:30:00+09:00",
  "language": "en",
  "symbols": ["NVDA"],
  "metadata": {
    "feed": "example-rss"
  }
}
```

응답 예시:

```json
{
  "raw_news_id": "raw_20260414_000001",
  "status": "accepted"
}
```

### 4.2 POST `/api/v1/ingest/batch`

용도:

- source별 batch loader 실행 또는 batch payload 업로드.

장중 정책:

- 금지.

요청 예시:

```json
{
  "source": "rss",
  "batch_id": "rss_20260414_morning",
  "items": []
}
```

응답 예시:

```json
{
  "batch_id": "rss_20260414_morning",
  "accepted_count": 120,
  "rejected_count": 3
}
```

### 4.3 POST `/api/v1/ingest/webhook/n8n`

용도:

- n8n에서 유입되는 외부 뉴스/이벤트 데이터를 수신한다.

장중 정책:

- lightweight inbound만 예외 검토.
- 대량 payload는 금지.

## 5. Analysis API

### 5.1 POST `/api/v1/analyze/daily`

용도:

- 일일 TrendSnapshot을 생성한다.

장중 정책:

- 금지.

요청 예시:

```json
{
  "as_of": "2026-04-14T08:00:00+09:00",
  "source_scope": ["kis", "kiwoom", "rss"],
  "force": false
}
```

응답 예시:

```json
{
  "job_id": "job_20260414_daily",
  "snapshot_id": "snapshot_20260414_morning",
  "status": "queued"
}
```

### 5.2 POST `/api/v1/analyze/incremental`

용도:

- 새로 들어온 뉴스만 대상으로 증분 분석을 수행한다.

장중 정책:

- 금지.

### 5.3 POST `/api/v1/analyze/rebuild`

용도:

- 특정 기간의 평가와 signal을 재생성한다.

장중 정책:

- 금지.

요청에는 `from`, `to`, `reason`, `dry_run` 필드를 포함한다.

## 6. Signal API

### 6.1 GET `/api/v1/signals/market`

query:

- `as_of`: optional
- `snapshot_id`: optional

응답 예시:

```json
{
  "snapshot_id": "snapshot_20260414_morning",
  "as_of": "2026-04-14T08:00:00+09:00",
  "market_signal": {
    "market_bias": "risk_on",
    "confidence_score": 0.71,
    "impact_score": 0.64,
    "drivers": ["AI infrastructure", "semiconductor demand"]
  }
}
```

### 6.2 GET `/api/v1/signals/themes`

query:

- `snapshot_id`: optional
- `limit`: default 20
- `min_confidence`: optional

### 6.3 GET `/api/v1/signals/stocks`

query:

- `snapshot_id`: optional
- `symbol`: optional
- `limit`: default 50

### 6.4 GET `/api/v1/news/evaluations`

query:

- `snapshot_id`: optional
- `source`: optional
- `symbol`: optional
- `theme`: optional
- `limit`: default 100
- `offset`: default 0

## 7. QTS API

### 7.1 GET `/api/v1/qts/daily-input`

응답은 `QTSInputPayload`를 반환한다.

핵심 필드:

- `snapshot_id`
- `market_bias`
- `sector_weights`
- `strategy_activation_hints`
- `generated_at`
- `rules_version`

### 7.2 GET `/api/v1/qts/universe-adjustments`

핵심 필드:

- `add_candidates`
- `remove_candidates`
- `watch_candidates`
- `reasons`

### 7.3 GET `/api/v1/qts/risk-overrides`

핵심 필드:

- `risk_level`
- `risk_overrides`
- `confidence_score`
- `expires_at`

## 8. Generic API

### 8.1 GET `/api/v1/generic/briefing`

용도:

- daily briefing payload 조회.

### 8.2 GET `/api/v1/generic/theme-ranking`

용도:

- theme ranking payload 조회.

### 8.3 GET `/api/v1/generic/watchlist`

용도:

- watchlist candidate payload 조회.

### 8.4 GET `/api/v1/generic/alerts`

용도:

- alert summary payload 조회.

## 9. Workflow API

### 9.1 GET `/api/v1/workflow/payload`

용도:

- n8n이 polling 또는 수동 호출로 workflow payload를 조회한다.

### 9.2 POST `/api/v1/workflow/dispatch`

용도:

- n8n 또는 downstream workflow로 payload를 dispatch한다.

장중 정책:

- 대규모 dispatch 금지.
- 소량 수동 dispatch도 `reason`과 `requested_by`를 기록한다.

요청 예시:

```json
{
  "payload_id": "workflow_20260414_evening",
  "dispatch_mode": "manual",
  "reason": "evening briefing dispatch",
  "requested_by": "operator"
}
```

### 9.3 GET `/api/v1/workflow/status`

용도:

- workflow dispatch 상태와 실패 사유 조회.

## 10. Ops API

### 10.1 GET `/api/v1/health`

응답 예시:

```json
{
  "status": "ok",
  "service": "trends-analyzer",
  "time": "2026-04-14T08:00:00+09:00"
}
```

### 10.2 GET `/api/v1/jobs/status`

용도:

- 최근 batch job과 scheduler 상태 조회.

### 10.3 POST `/api/v1/jobs/retry`

장중 정책:

- 금지.

요청에는 `job_id`, `reason`, `requested_by`를 포함한다.

### 10.4 GET `/api/v1/config/version`

용도:

- 실행 중인 rules/config/model prompt version 확인.
