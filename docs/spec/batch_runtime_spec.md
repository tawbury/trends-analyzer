# Batch And Runtime Spec

## 1. 범위

이 문서는 batch job, scheduler, KST 장중 보호 가드, 로컬/OCI/API/n8n 런타임 구성을 정의한다.

핵심 원칙:

- 한국 장중(KST 09:00~15:30)에는 heavy job을 실행하지 않는다.
- 장전/장후/야간 배치 중심으로 운영한다.
- QTS/Observer 리소스 보호를 우선한다.
- 로컬 검증 후 OCI 단일 서버의 3번째 앱으로 배포한다.

## 2. Market Hours Guard

금지 시간:

- KST 09:00~15:30

허용 작업:

- health check
- read-only API 조회
- 로그 확인
- lightweight 상태 점검

금지 작업:

- 대량 뉴스 수집
- LLM 기반 대량 분석
- 재빌드 배치
- DB 전체 재처리
- n8n 대규모 자동화 트리거
- job retry

권장 위치:

```text
src/shared/market_hours.py
src/api/dependencies.py
src/batch/runner.py
src/scheduler/
```

권장 인터페이스:

```python
def is_korean_market_hours(now: datetime) -> bool:
    ...

def assert_heavy_job_allowed(now: datetime, job_type: str) -> None:
    ...
```

## 3. Batch Jobs

초기 job 후보:

| Job | 목적 | 권장 시간 |
|-----|------|-----------|
| `ingest_morning_news` | 장전 뉴스 수집 | 06:00~08:00 KST |
| `analyze_daily_snapshot` | 일일 TrendSnapshot 생성 | 06:00~08:00 KST |
| `aggregate_after_market` | 장후 집계 및 재평가 | 16:00~18:00 KST |
| `generate_qts_payload` | QTS payload 생성 | 16:00~18:00 KST |
| `generate_generic_briefing` | 브리핑/랭킹 생성 | 20:00~23:00 KST |
| `generate_workflow_payload` | n8n payload 생성 | 20:00~23:00 KST |
| `dispatch_workflow_payload` | n8n 후속 dispatch | 20:00~23:00 KST |

## 4. Batch Runner Rules

- 모든 job은 실행 직전 `assert_heavy_job_allowed()`를 호출한다.
- source별 실패가 전체 batch를 불필요하게 중단하지 않도록 실패 범위를 분리한다.
- job result에는 `job_id`, `started_at`, `finished_at`, `status`, `error`, `input_count`, `output_count`를 기록한다.
- 재시도는 장중 금지이며, 실패 사유와 수동 retry 이유를 기록한다.
- dry-run 모드를 지원할 수 있으면 초기 검증에 우선 적용한다.

권장 job result:

```json
{
  "job_id": "job_20260414_daily",
  "job_type": "analyze_daily_snapshot",
  "status": "succeeded",
  "started_at": "2026-04-14T06:00:00+09:00",
  "finished_at": "2026-04-14T06:07:30+09:00",
  "input_count": 240,
  "output_count": 1,
  "error": null
}
```

## 5. Scheduler Rules

초기 선택지:

- cron
- 앱 내부 scheduler

선택 기준:

- OCI 기존 운영 체계와 맞는 방식을 우선한다.
- 단순한 장외 배치만 필요하면 cron을 우선 검토한다.
- API runtime과 job 상태를 긴밀히 통합해야 하면 앱 내부 scheduler를 검토한다.

필수:

- scheduler 등록 단계와 runner 실행 단계 모두에서 장중 보호 가드를 둔다.
- timezone은 KST 기준으로 명시한다.
- job overlap 방지 정책을 둔다.

## 6. Local Development Runtime

목적:

- 기능 검증
- API 응답 확인
- DB 저장 확인
- 로그 구조 확인
- 점수화 품질 검증

구성:

- Python 3.11+
- FastAPI local server
- PostgreSQL local 또는 dev DB
- JSONL optional
- `.env.local` 또는 로컬 config

검증 순서:

1. 샘플 뉴스 ingest
2. normalize/deduplicate/score 실행
3. TrendSnapshot 생성
4. QTS/Generic/Workflow adapter payload 생성
5. API 조회 확인
6. batch dry-run 확인

## 7. OCI Batch Runtime

목적:

- QTS/Observer와 같은 OCI 서버 내 3번째 앱으로 초기 운영
- 장전/장후/야간 batch 실행

필수 조건:

- Docker container 기반 실행
- CPU/메모리 상한
- 장중 비구동 스케줄
- 로그와 job status 저장
- QTS/Observer 리소스 영향 점검

## 8. API Service Runtime

목적:

- QTS, n8n, 외부 자동화가 조회 가능한 read API 제공
- 장중 read-only 중심 운영

필수 endpoint:

- `/api/v1/health`
- `/api/v1/jobs/status`
- `/api/v1/config/version`
- `/api/v1/signals/*`
- `/api/v1/qts/*`

운영 전 확인:

- 인증 방식
- reverse proxy 여부
- CORS 필요 여부
- request logging
- rate limit 필요 여부

## 9. n8n Runtime

목적:

- n8n webhook inbound
- workflow payload 조회
- 후속 automation dispatch

초기 범위:

- inbound/outbound 최소 시나리오
- dispatch log 저장
- 대규모 dispatch 금지

필수 기록:

- `payload_id`
- `dispatch_mode`
- `target`
- `requested_by`
- `reason`
- `status`
- `error`
- `dispatched_at`

## 10. 운영 분리 판단 기준

다음 조건 중 2개 이상 충족 시 서버 분리 또는 별도 서비스화를 재검토한다.

- 장중 상시 구동이 필요해짐
- CPU/메모리 사용량이 QTS/Observer 안정성에 영향을 줌
- n8n 호출량이 증가함
- API 요청이 상시화됨
- 별도 보안/배포 주기가 필요해짐
