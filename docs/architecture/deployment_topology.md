# 배포 토폴로지 문서

## 1. 목적

이 문서는 Trend Intelligence Platform의 로컬, 임시 노트북, OCI 초기 배포 토폴로지를 정의한다.

현재 기본 전략은 단순하게 시작하되 분리 가능성을 보존하는 것이다.

## 2. 환경별 역할

| 환경 | 역할 |
|------|------|
| Windows 11 + WSL2 local | 개발, 단위 검증, API local test, batch dry-run |
| 예비 Windows 11 + WSL2 노트북 | 임시 상시 테스트 노드, 장시간 API/batch/n8n 연동 검증 |
| OCI 기존 서버 | 초기 운영 배포 대상, QTS/Observer와 같은 서버의 3번째 앱 |
| 별도 서버 | 트래픽/리소스/보안 요구 증가 시 재검토 |

## 3. 초기 OCI Topology

권장 초기안:

```text
OCI Server
  ├─ QTS
  ├─ Observer
  └─ trends-analyzer
      ├─ API Service
      ├─ Batch Worker
      └─ Scheduler
```

초기에는 단일 Docker image를 우선한다.

이유:

- 배포 복잡도를 낮춘다.
- 문서/계약이 안정화되기 전 운영 표면을 줄인다.
- API, worker, scheduler가 같은 코드 버전을 사용하게 한다.

단, runtime entrypoint는 분리한다.

## 4. 단일 이미지 / 다중 런타임

단일 image:

- `trends-analyzer:{version}`

권장 entrypoint:

```text
python -m src.api.app
python -m src.batch.runner --mode daily
python -m src.scheduler.main
```

운영 방식 후보:

- 하나의 container에서 scheduler가 worker를 호출
- 같은 image를 사용해 api/worker/scheduler container를 분리
- cron이 worker entrypoint를 실행

초기에는 가장 단순한 방식을 선택하되, code boundary는 분리된 container로 이동 가능해야 한다.

## 5. Scheduler 배포 전략

선택지:

- cron 기반
- 앱 내부 scheduler

초기 권장:

- OCI 기존 운영 체계가 cron에 익숙하면 cron 우선
- job 상태와 API 통합이 중요해지면 앱 내부 scheduler 검토

필수:

- scheduler와 batch runner 양쪽 모두 KST market-hours guard를 적용한다.
- job overlap 방지 lock을 둔다.
- retry/rebuild는 장중 금지한다.

## 6. 분리 재검토 기준

별도 서버 또는 container 분리 기준:

- API 요청이 상시화됨
- n8n dispatch 호출량이 증가함
- batch가 QTS/Observer 리소스에 영향을 줌
- 독립 보안 정책이 필요함
- 배포 주기가 QTS/Observer와 달라짐
- 장중 read/write 요구가 커짐

## 7. 운영 가드

- CPU/메모리 상한을 설정한다.
- 장중 heavy job을 비활성화한다.
- logs/job status를 남긴다.
- QTS/Observer와 batch window가 충돌하지 않게 한다.

## 8. 환경 설정 연결

환경별 runtime flag와 secret/config 경계는 `docs/architecture/environment_config.md`를 따른다.

배포 토폴로지가 바뀌어도 다음 설정 경계는 유지한다.

- `RUNTIME_ROLE`로 api/worker/scheduler 실행 역할을 구분한다.
- `RUNTIME_MODE`로 daily/incremental/rebuild/api_readonly/workflow_dispatch 작업 모드를 구분한다.
- `SCHEDULER_ENABLED`와 `SCHEDULER_BACKEND`로 scheduler 배포 방식을 통제한다.
- `MARKET_HOURS_GUARD_ENABLED`는 OCI와 예비 노트북 테스트 노드에서 기본 활성화한다.
- n8n secret, outbound webhook URL, idempotency TTL은 코드가 아니라 환경 설정으로 주입한다.
