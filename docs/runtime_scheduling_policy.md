# 런타임 및 스케줄링 정책

## 1. 목적

이 문서는 Trend Intelligence Platform의 runtime mode, market-hours restriction, batch window, retry/rebuild 규칙, local/OCI validation 단계를 정의한다.

## 2. 런타임 모드

- `DAILY`: 장전 또는 야간 일일 snapshot 생성
- `INCREMENTAL`: 신규 수집분 기반 증분 분석
- `REBUILD`: 특정 기간 재분석
- `API_READONLY`: signal/payload/status 조회
- `WEBHOOK_INBOUND`: n8n inbound 수신
- `WORKFLOW_DISPATCH`: downstream workflow trigger

런타임 실행 원칙:

- API route는 UseCase를 호출한다.
- Batch Worker는 UseCase를 호출한다.
- Scheduler는 Batch Worker 또는 UseCase trigger만 호출한다.
- Core와 Adapter 직접 조합은 `application/use_cases`에서만 수행한다.

## 3. 한국 장중 제한

장중 기준:

- KST 09:00~15:30

장중 허용:

- health check
- read-only API
- job status
- config version
- 로그 확인
- lightweight 상태 점검

장중 금지:

- 대량 뉴스 수집
- daily/incremental/rebuild analysis
- LLM 기반 대량 분석
- DB 전체 재처리
- 대규모 n8n dispatch
- job retry

## 4. Batch Window

| 시간대 KST | 목적 |
|------------|------|
| 06:00~08:00 | 장전 뉴스 정리, daily snapshot |
| 16:00~18:00 | 장후 집계, QTS payload, risk review |
| 20:00~23:00 | 외신 반영, generic briefing, workflow payload, n8n 후속 작업 |

## 5. Retry/Rebuild 규칙

- 장중 retry 금지.
- rebuild는 반드시 `from`, `to`, `reason`, `requested_by`, `dry_run`을 기록한다.
- rebuild는 기본적으로 dry-run 후 실제 실행한다.
- source별 수집 실패는 전체 batch 실패와 분리해 기록한다.
- workflow dispatch retry는 payload id와 downstream target을 기준으로 idempotency를 고려한다.

## 6. 로컬 검증 단계

로컬 Windows 11 + WSL2에서 다음을 검증한다.

1. sample ingest
2. normalize/deduplicate
3. score and credibility breakdown
4. aggregate TrendSnapshot
5. QTS/Generic/Workflow payload generation
6. FastAPI local route
7. batch dry-run
8. persistence write/read

## 7. 임시 노트북 테스트 노드

예비 Windows 11 + WSL2 노트북은 다음 목적으로 사용할 수 있다.

- 장시간 API 구동 테스트
- batch scheduler dry-run
- n8n webhook 연동 테스트
- 운영 서버 투입 전 resource profile 확인

운영과 동일한 보안/네트워크 환경은 아니므로 최종 운영 검증을 대체하지 않는다.

## 8. OCI 초기 배포

초기 OCI 배포 가정:

- 기존 OCI 서버 내 3번째 앱
- Docker 기반 runtime
- API service와 batch worker는 같은 앱으로 시작 가능
- CPU/메모리 상한 적용
- 장중 heavy job 비활성화
- QTS/Observer 리소스 영향 모니터링

초기 topology:

- 단일 Docker image를 우선한다.
- 동일 image에서 `api`, `worker`, `scheduler` entrypoint를 분리한다.
- 운영 복잡도를 낮추기 위해 단일 서버/단일 이미지로 시작하되, runtime process는 분리 가능한 구조를 유지한다.

권장 entrypoint:

- `python -m src.api.app`
- `python -m src.batch.runner --mode daily`
- `python -m src.scheduler.main`

## 9. 서버 분리 또는 QTS 내장 재검토 기준

서버 분리 재검토 조건:

- 장중 상시 API/write 작업 필요
- n8n 호출량 증가
- CPU/메모리 사용량이 QTS/Observer에 영향
- 별도 보안 정책 필요
- 별도 배포 주기 필요

QTS 내부 모듈화 재검토 조건:

- QTS 의사결정 루프와 동기 실행이 필요
- QTS가 API polling보다 낮은 지연이나 강한 일관성을 요구
- QTS 내부 config/risk 정책과 밀접한 결합이 불가피

현재 단계에서는 QTS 내부 모듈화가 기본안이 아니다.
