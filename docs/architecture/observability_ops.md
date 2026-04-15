# 운영 및 관측성 문서

## 1. 목적

이 문서는 Trend Intelligence Platform의 로그, job 추적, correlation id, workflow dispatch 결과, health/readiness, 장중 위반 처리 기준을 정의한다.

초기 OCI 단일 서버 배포에서도 관측성은 선택 사항이 아니다. QTS/Observer와 같은 서버를 공유하므로 작은 장애도 운영 영향으로 이어질 수 있다.

## 2. 로그 원칙

- 구조화 로그를 기본으로 한다.
- 모든 API 요청, batch job, workflow dispatch에는 `correlation_id`를 포함한다.
- 장중 보호 가드 위반은 warning 이상으로 기록한다.
- source별 수집 실패는 전체 batch 실패와 분리해 기록한다.
- provider source 실행은 요청 symbol 수, 성공 symbol 수, 실패 symbol 수, item count, partial success 여부를 기록한다.
- symbol selection은 catalog id, 선택 정책, selected symbol count, invalid-code 제외 수를 기록한다.
- payload 생성과 dispatch 실행은 별도 이벤트로 기록한다.

권장 공통 필드:

```json
{
  "timestamp": "2026-04-14T08:00:00+09:00",
  "level": "INFO",
  "service": "trends-analyzer",
  "runtime": "batch",
  "correlation_id": "corr_20260414_0001",
  "job_id": "job_20260414_daily_001",
  "event": "job_completed",
  "message": "daily analysis completed"
}
```

## 3. Job ID / Correlation ID

권장 규칙:

- `correlation_id`: 요청 또는 workflow 전체 추적 id
- `job_id`: batch/use case 실행 단위 id
- `dispatch_id`: n8n outbound dispatch 단위 id
- `snapshot_id`: 분석 결과 단위 id

예시:

```text
correlation_id = corr_YYYYMMDD_NNNN
job_id = job_YYYYMMDD_{job_type}_NNN
dispatch_id = dispatch_YYYYMMDD_NNN
snapshot_id = snapshot_YYYYMMDD_{window}
```

## 4. Batch Run Tracking

Batch job은 다음 상태를 기록한다.

- `queued`
- `running`
- `succeeded`
- `failed`
- `blocked`
- `skipped`

필수 기록:

- `job_id`
- `job_type`
- `correlation_id`
- `runtime_mode`
- `started_at`
- `finished_at`
- `status`
- `input_count`
- `output_count`
- `error_code`
- `error_message`

## 4.1 Source Execution Tracking

KIS/Kiwoom source 실행은 다음 이벤트를 남긴다.

- `source_symbol_selection`
- `source_fetch_started`
- `source_execution_report`
- `source_fetch_failed`
- `source_fetch_completed`

필수 필드:

- `catalog_id`
- `symbol_selection_policy`
- `selected_symbol_count`
- `catalog_invalid_code_count`
- `selection_invalid_code_excluded_count`
- `explicit_override_used`
- `catalog_missing_fallback_used`
- `provider`
- `requested_symbol_count`
- `succeeded_symbol_count`
- `failed_symbol_count`
- `failed_symbol_sample`
- `query_count`
- `failed_query_count`
- `failed_query_sample`
- `item_count`
- `partial_success`

## 5. Workflow Dispatch Results

n8n dispatch는 다음을 기록한다.

- `dispatch_id`
- `payload_id`
- `workflow_target`
- `dispatch_mode`
- `requested_by`
- `correlation_id`
- `status`
- `http_status`
- `response_summary`
- `error_code`
- `error_message`
- `dispatched_at`

Workflow Adapter가 payload를 만든 사실과 n8n Gateway가 dispatch를 실행한 사실은 별도 이벤트로 남긴다.

## 6. Health / Readiness

`GET /api/v1/health`:

- process alive 확인
- 의존성 체크 없이 빠르게 응답

`GET /api/v1/readiness`를 추가할 수 있다.

readiness 후보:

- DB 연결 가능 여부
- config loaded 여부
- source tier config loaded 여부
- scheduler enabled 여부
- market-hours guard 정상 여부

## 7. KST 장중 위반 처리

장중 heavy job이 요청되면 다음을 수행한다.

- 실행하지 않는다.
- `MARKET_HOURS_GUARD` 에러를 반환한다.
- `blocked` job event를 기록한다.
- `correlation_id`, `requested_by`, `operation`, `blocked_window`를 기록한다.

예시:

```json
{
  "event": "market_hours_blocked",
  "level": "WARNING",
  "operation": "analyze_daily",
  "blocked_window": "09:00-15:30 KST",
  "correlation_id": "corr_20260414_0003"
}
```

## 8. 최소 운영 대시보드 후보

초기에는 독립 대시보드 제품화가 목표가 아니므로, API와 로그 기반으로 최소 관측성을 확보한다.

필수 조회:

- 최근 job status
- 최근 dispatch status
- 마지막 snapshot id
- 마지막 QTS payload generated_at
- 장중 blocked count
- source별 ingest failure count
