# 환경 및 런타임 설정 문서

## 1. 문서 메타데이터

- 문서 유형: 운영/환경 설정 기준
- 상태: Draft v0.3
- 권위 범위: local/laptop/OCI 설정 차이, 환경 변수 그룹, feature flag, runtime mode 설정
- 상위 문서: `docs/architecture/deployment_topology.md`, `docs/architecture/runtime_scheduling_policy.md`
- 관련 문서: `docs/architecture/architecture_specification.md`, `docs/architecture/observability_ops.md`, `docs/specification/source/source_module_spec.md`
- 최종 수정일: 2026-04-14

## 2. 목적

이 문서는 Trend Intelligence Platform의 실행 환경별 설정 경계를 정의한다.

목표는 환경별 차이를 코드에 흩뿌리지 않고 설정으로 통제하는 것이다. 로컬 개발, 예비 WSL2 노트북 테스트, OCI 초기 운영 배포는 같은 애플리케이션 구조를 사용하되, runtime mode, scheduler, n8n 인증, source tier 설정, 장중 보호 정책을 환경 설정으로 분리한다.

## 3. 환경별 기본 원칙

| 환경 | 목적 | 기본 설정 방향 |
|------|------|----------------|
| `local` | 개발, 단위 검증, API dry-run | scheduler 기본 비활성화, auth 완화 가능, 외부 dispatch dry-run 권장 |
| `laptop_test_node` | 임시 상시 테스트, n8n 연동 리허설 | scheduler 제한적 활성화, dispatch test endpoint 사용, 장중 보호 활성화 |
| `oci_single_server` | 초기 운영 배포 | auth 필수, scheduler/batch guard 필수, 구조화 로그 필수, dispatch 실제 endpoint 사용 |

모든 환경에서 다음 원칙은 유지한다.

- Trend Core는 환경 설정을 직접 읽지 않는다.
- API, Batch, Scheduler entrypoint에서 설정을 로드하고 UseCase factory에 주입한다.
- 장중 heavy workload 차단은 로컬을 제외한 모든 장기 실행 환경에서 기본 활성화한다.
- n8n secret과 token은 코드나 문서 예시에 평문으로 고정하지 않는다.

## 4. 설정 파일과 환경 변수의 역할

권장 방식:

- `.env.local`: 로컬 개발 전용, git 추적 금지
- `.env.laptop`: 예비 WSL2 노트북 테스트 전용, git 추적 금지
- `.env.oci`: OCI 운영 배포용, 서버 secret 관리 체계에서 관리
- `config/source_tiers.yaml`: source tier 초기 기준 후보
- `config/runtime.local.yaml`: 로컬 feature flag 후보

MVP에서는 환경 변수 중심으로 시작해도 된다. 다만 source tier처럼 사람이 검토해야 하는 정책성 데이터는 별도 config 파일로 분리하는 편이 안전하다.

## 5. 환경 변수 그룹

### 5.1 공통 서비스 설정

| 변수 | 예시 | 설명 |
|------|------|------|
| `TRENDS_ENV` | `local`, `laptop_test_node`, `oci_single_server` | 실행 환경 |
| `SERVICE_NAME` | `trends-analyzer` | 로그/관측성 서비스명 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LOG_FORMAT` | `json` | 운영에서는 `json` 권장 |
| `TIMEZONE` | `Asia/Seoul` | 장중 정책 기준 timezone |

### 5.2 Runtime mode 설정

| 변수 | 예시 | 설명 |
|------|------|------|
| `RUNTIME_ROLE` | `api`, `worker`, `scheduler` | 동일 이미지의 실행 역할 |
| `RUNTIME_MODE` | `daily`, `incremental`, `rebuild`, `api_readonly`, `workflow_dispatch` | 실행 모드 |
| `ENABLE_EMBEDDED_QTS_MODE` | `false` | 향후 QTS 내부 임베딩 검토용 flag. 현재 기본값은 `false` |

`RUNTIME_ROLE`은 프로세스 역할이고, `RUNTIME_MODE`는 해당 역할 안에서 수행하는 작업 모드다.

## 6. Feature Flags

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `FEATURE_QTS_ADAPTER_ENABLED` | `true` | QTS payload 생성 활성화 |
| `FEATURE_GENERIC_ADAPTER_ENABLED` | `true` | generic briefing/watchlist payload 생성 활성화 |
| `FEATURE_WORKFLOW_ADAPTER_ENABLED` | `true` | workflow payload mapping 활성화 |
| `FEATURE_N8N_INBOUND_ENABLED` | `false` in local, `true` in OCI | n8n inbound webhook 활성화 |
| `FEATURE_N8N_OUTBOUND_DISPATCH_ENABLED` | `false` in local, `true` in OCI | n8n outbound dispatch 활성화 |
| `FEATURE_DISPATCH_DRY_RUN` | `true` in local | 실제 webhook 호출 대신 dispatch record만 남김 |

Feature flag는 Core 알고리즘 분기를 만들기 위한 용도가 아니다. Adapter, integration, runtime 실행 여부를 제어하는 용도로 제한한다.

## 7. 장중 보호 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MARKET_HOURS_GUARD_ENABLED` | `true` | KST 장중 heavy job 차단 |
| `MARKET_TIMEZONE` | `Asia/Seoul` | 장중 판정 timezone |
| `KR_MARKET_OPEN` | `09:00` | 한국 시장 시작 |
| `KR_MARKET_CLOSE` | `15:30` | 한국 시장 종료 |
| `ALLOW_LIGHTWEIGHT_INBOUND_DURING_MARKET` | `false` | 장중 소량 inbound webhook 예외 허용 여부 |
| `ALLOW_MANUAL_OVERRIDE_DURING_MARKET` | `false` | 운영자 override 허용 여부. MVP 기본 비활성화 |

장중 보호 flag가 꺼진 환경에서도 Batch Worker와 Scheduler는 실행 로그에 해당 사실을 남겨야 한다.

## 8. Scheduler 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SCHEDULER_ENABLED` | `false` in local, `true` in OCI | scheduler 프로세스 활성화 |
| `SCHEDULER_BACKEND` | `cron` 또는 `app` | cron 기반 또는 앱 내부 scheduler |
| `DAILY_ANALYSIS_CRON_KST` | `30 16 * * 1-5` | 장마감 후 일일 분석 후보 |
| `INCREMENTAL_ANALYSIS_ENABLED` | `false` | 증분 분석 활성화 여부 |
| `MAX_CONCURRENT_BATCH_JOBS` | `1` | 초기 OCI 단일 서버 리소스 보호 |
| `JOB_LOCK_TTL_SECONDS` | `7200` | 중복 실행 방지 lock TTL |

Scheduler는 Core/Adapter를 직접 호출하지 않는다. Scheduler는 Batch Runner 또는 Application UseCase trigger를 호출한다.

## 9. API / 인증 설정

| 변수 | 예시 | 설명 |
|------|------|------|
| `API_AUTH_MODE` | `local_dev_disabled`, `bearer_token`, `reverse_proxy_auth` | API 인증 모드 |
| `API_BEARER_TOKEN` | secret | `bearer_token` 모드에서 사용 |
| `API_IDEMPOTENCY_TTL_SECONDS` | `86400` | `Idempotency-Key` 보관 시간 |
| `API_DEFAULT_PAGE_LIMIT` | `50` | 기본 pagination limit |
| `API_MAX_PAGE_LIMIT` | `500` | 최대 pagination limit |

운영 배포에서는 `local_dev_disabled`를 사용할 수 없다.

## 10. n8n 설정

| 변수 | 예시 | 설명 |
|------|------|------|
| `N8N_INBOUND_AUTH_MODE` | `shared_secret`, `hmac` | inbound webhook 검증 방식 |
| `N8N_WEBHOOK_SECRET` | secret | shared secret 또는 HMAC secret |
| `N8N_SIGNATURE_HEADER` | `X-N8N-Signature` | HMAC signature header |
| `N8N_OUTBOUND_WEBHOOK_URL` | `https://...` | outbound dispatch 대상 |
| `N8N_OUTBOUND_TIMEOUT_SECONDS` | `10` | dispatch timeout |
| `N8N_OUTBOUND_MAX_RETRIES` | `3` | dispatch retry 횟수 |

`src/adapters/workflow/`는 n8n URL이나 secret을 알면 안 된다. n8n 인증과 HTTP 호출은 `src/integration/n8n/` 및 `src/runtime/dispatch/` 책임이다.

## 11. 데이터/저장소 설정

| 변수 | 예시 | 설명 |
|------|------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | 운영 DB 연결 |
| `JSONL_STORAGE_DIR` | `/var/lib/trends-analyzer/jsonl` | 임시/보조 JSONL 저장소 |
| `SOURCE_TIER_CONFIG_PATH` | `config/source_tiers.yaml` | 뉴스 source tier 설정 파일 |
| `RULES_VERSION` | `rules_2026_04_14` | 분석/스코어링 규칙 버전 |
| `PAYLOAD_RETENTION_DAYS` | `90` | adapter payload 보관 기간 |

`SOURCE_TIER_CONFIG_PATH`는 뉴스 신뢰도 구현의 핵심 입력이다. 운영 중 변경 시 rules/config version을 함께 기록해야 한다.

## 12. 예시 `.env.local`

```text
TRENDS_ENV=local
SERVICE_NAME=trends-analyzer
LOG_LEVEL=DEBUG
LOG_FORMAT=plain
TIMEZONE=Asia/Seoul

RUNTIME_ROLE=api
RUNTIME_MODE=api_readonly
SCHEDULER_ENABLED=false

MARKET_HOURS_GUARD_ENABLED=true
FEATURE_DISPATCH_DRY_RUN=true
FEATURE_N8N_OUTBOUND_DISPATCH_ENABLED=false

API_AUTH_MODE=local_dev_disabled
API_IDEMPOTENCY_TTL_SECONDS=86400

SOURCE_TIER_CONFIG_PATH=config/source_tiers.yaml
```

## 13. 예시 `.env.oci`

```text
TRENDS_ENV=oci_single_server
SERVICE_NAME=trends-analyzer
LOG_LEVEL=INFO
LOG_FORMAT=json
TIMEZONE=Asia/Seoul

RUNTIME_ROLE=api
RUNTIME_MODE=api_readonly
SCHEDULER_ENABLED=true
SCHEDULER_BACKEND=cron
DAILY_ANALYSIS_CRON_KST=30 16 * * 1-5
MAX_CONCURRENT_BATCH_JOBS=1

MARKET_HOURS_GUARD_ENABLED=true
KR_MARKET_OPEN=09:00
KR_MARKET_CLOSE=15:30

API_AUTH_MODE=bearer_token
API_IDEMPOTENCY_TTL_SECONDS=86400

FEATURE_N8N_INBOUND_ENABLED=true
FEATURE_N8N_OUTBOUND_DISPATCH_ENABLED=true
FEATURE_DISPATCH_DRY_RUN=false
N8N_INBOUND_AUTH_MODE=hmac
N8N_SIGNATURE_HEADER=X-N8N-Signature

SOURCE_TIER_CONFIG_PATH=config/source_tiers.yaml
```

## 14. 구현 시 주의사항

- 설정 로더는 `src/shared/config.py` 또는 equivalent에 둔다.
- UseCase는 이미 파싱된 settings 객체를 주입받아야 하며, 환경 변수를 직접 읽지 않는다.
- secret 값은 로그에 남기지 않는다.
- 장중 override는 MVP에서 비활성화한다.
- OCI 단일 서버에서는 worker concurrency를 보수적으로 유지한다.
- 로컬과 예비 노트북에서 통과한 설정 조합만 OCI에 반영한다.
