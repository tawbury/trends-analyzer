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
| `TRENDS_DATA_DIR` | `.local/trends-analyzer` | MVP JSONL 저장소 루트. API와 Batch가 같은 값을 사용해야 함 |
| `JSONL_STORAGE_DIR` | `/var/lib/trends-analyzer/jsonl` | 임시/보조 JSONL 저장소 |
| `SOURCE_TIER_CONFIG_PATH` | `config/source_tiers.yaml` | 뉴스 source tier 설정 파일 |
| `RULES_VERSION` | `rules_2026_04_14` | 분석/스코어링 규칙 버전 |
| `PAYLOAD_RETENTION_DAYS` | `90` | adapter payload 보관 기간 |

`SOURCE_TIER_CONFIG_PATH`는 뉴스 신뢰도 구현의 핵심 입력이다. 운영 중 변경 시 rules/config version을 함께 기록해야 한다.

## 12. 외부 소스 연동 설정

Phase 1 실데이터 검증에서는 fixture, KIS, Kiwoom을 설정으로 조합한다. Source Provider의 인증/HTTP 세부사항은 `src/ingestion/clients/`에 격리하고, loader는 provider 응답을 `RawNewsItem`으로 변환한다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRENDS_ACTIVE_SOURCES` | `fixture` | 활성 소스 목록. 예: `fixture`, `kis`, `kiwoom`, `naver_news`, `kis,kiwoom,naver_news` |
| `TRENDS_SOURCE_SYMBOLS` | `005930,000660` | KIS/Kiwoom 검증 대상 종목 코드 |
| `TRENDS_SOURCE_SYMBOL_POLICY` | `explicit` | source 실행 종목 선택 정책. `explicit`, `catalog_all`, `catalog_filtered` |
| `TRENDS_SOURCE_SYMBOL_MARKETS` | `KOSPI,KOSDAQ` | `catalog_filtered` 사용 시 포함할 시장 |
| `TRENDS_SOURCE_SYMBOL_CLASSIFICATIONS` | `stock` | `catalog_filtered` 사용 시 포함할 분류. 예: `stock,preferred_stock,etf` |
| `TRENDS_SOURCE_SYMBOL_LIMIT` | `0` | catalog 기반 선택 시 최대 종목 수. `0`은 제한 없음 |
| `TRENDS_SOURCE_SYMBOL_VALID_CODE_ONLY` | `true` | KIS/Kiwoom source 실행용 선택에서 6자리 숫자 종목코드만 허용 |
| `TRENDS_SOURCE_TIMEOUT_SECONDS` | `10` | provider HTTP 요청 timeout |
| `TRENDS_SOURCE_PARTIAL_SUCCESS` | `true` | 일부 소스 실패 시 나머지 소스 결과로 분석 지속 |
| `TRENDS_SYMBOL_CATALOG_SOURCE` | `kis_master` | symbol catalog 갱신 원천. `kis_master` 또는 임시 bridge용 `json_artifact` |
| `TRENDS_SYMBOL_CATALOG_PATH` | path | `json_artifact` 사용 시 읽을 Observer/외부 symbol artifact 경로 |
| `TRENDS_SYMBOL_CATALOG_MARKETS` | `KOSPI,KOSDAQ,KONEX` | catalog에 포함할 시장 구분 |
| `TRENDS_SYMBOL_CATALOG_URL` | empty | 예약 필드. 기본 `kis_master` 모드는 KIS 공식 MST ZIP 경로를 시장별로 사용 |
| `KIS_APP_KEY` | secret | KIS Open API app key |
| `KIS_APP_SECRET` | secret | KIS Open API app secret |
| `KIS_BASE_URL` | `https://openapi.koreainvestment.com:9443` | KIS 운영/모의투자 base URL |
| `KIS_MARKET_DIVISION_CODE` | `J` | KIS 국내주식 시장 구분 코드 |
| `KIS_TR_ID_QUOTE` | `FHKST01010100` | KIS 국내주식 현재가 조회 TR ID |
| `KIS_TR_ID_INVEST_OPINION` | `FHKST663300C0` | KIS 국내주식 종목투자의견 조회 TR ID |
| `KIS_INVEST_OPINION_LOOKBACK_DAYS` | `180` | 종목투자의견 조회 기간 |
| `KIS_INVEST_OPINION_LIMIT_PER_SYMBOL` | `5` | 종목별 RawNewsItem 변환 최대 건수 |
| `KIWOOM_APP_KEY` | secret | Kiwoom REST API app key |
| `KIWOOM_APP_SECRET` | secret | Kiwoom REST API secret key |
| `KIWOOM_MODE` | `KIWOOM_REAL` | Kiwoom 실행 모드. `KIWOOM_REAL`은 운영, `KIWOOM_MOCK`은 모의투자 |
| `KIWOOM_APP_ACCOUNT_NO` | secret | Kiwoom 실계좌/모의계좌 번호. 토큰 발급에는 사용하지 않지만 계좌성 endpoint 검증에 필요 |
| `KIWOOM_APP_ACNT_PRDT_CD` | secret | Kiwoom 계좌 상품 코드. 토큰 발급에는 사용하지 않지만 계좌성 endpoint 검증에 필요 |
| `KIWOOM_BASE_URL` | `https://api.kiwoom.com` | Kiwoom 운영/모의투자 base URL |
| `KIWOOM_STOCK_INFO_PATH` | `/api/dostk/stkinfo` | Kiwoom 주식기본정보 요청 path |
| `NAVER_CLIENT_ID` | secret | Naver News Search API client id |
| `NAVER_CLIENT_SECRET` | secret | Naver News Search API client secret |
| `NAVER_NEWS_BASE_URL` | `https://openapi.naver.com` | Naver Open API base URL |
| `TRENDS_NAVER_NEWS_ENABLED` | `false` | `naver_news` source 사용 허용 flag |
| `TRENDS_NAVER_QUERY_LIMIT_PER_SYMBOL` | `2` | symbol당 query 최대 수 |
| `TRENDS_NAVER_RESULT_LIMIT_PER_QUERY` | `5` | query당 결과 요청 수 |
| `TRENDS_NAVER_INCLUDE_ALIASES` | `false` | alias를 query 후보에 포함할지 여부 |
| `TRENDS_NAVER_INCLUDE_QUERY_KEYWORDS` | `true` | catalog query_keywords를 query 후보에 포함할지 여부 |
| `TRENDS_DISCOVERY_REVIEW_ENABLED` | `true` | query discovery review/calibration artifact 저장 여부 |

KIS와 Kiwoom은 현재 Trend Core가 요구하는 완전한 뉴스 원천이 아니라 시세/종목 정보 성격이 강하다. KIS는 종목코드 기반 `invest-opinion` 응답을 우선 사용하고, 응답이 없으면 현재가 quote를 fallback으로 사용한다. 따라서 Phase 1에서는 “research/market-data-derived raw item”으로 `RawNewsItem`에 매핑하고 provider 원문은 `metadata.provider_payload`에 보존한다. 뉴스 본문이 없는 경우 투자 의견, 목표가, 가격, 등락률, 거래량을 조합해 `body` fallback을 만든다.

Symbol catalog는 QTS/Observer의 universe snapshot을 직접 재사용하지 않는다. Observer universe는 전일종가 4000원 미만 제외 등 QTS 매매 유니버스 정책을 포함할 수 있으므로 뉴스/트렌드 분석용 전체 종목 catalog에는 부적합하다. trends-analyzer는 기본적으로 KIS official stock master MST ZIP을 독립 catalog 원천으로 사용하고, `json_artifact`는 운영 전환 전 임시 bridge로만 사용한다.

`TRENDS_SOURCE_SYMBOL_POLICY`가 `catalog_all` 또는 `catalog_filtered`이면 runtime은 latest symbol catalog를 읽어 KIS/Kiwoom/Naver News source 생성 시 사용할 symbol을 선택한다. 선택 결과는 `latest_source_symbol_selection.json`에 저장해 catalog id, 선택 정책, 선택 종목 수, invalid-code 제외 수, 선택 record의 name/alias/query keyword를 확인할 수 있게 한다.

`TRENDS_SOURCE_SYMBOL_POLICY=explicit`에서도 latest catalog가 존재하면 explicit code 목록을 catalog record로 보강해 name, alias, query keyword를 유지한다. catalog에 없는 explicit code는 코드 자체를 name으로 사용하는 fallback record로 남긴다.

Naver News source는 selected `SymbolRecord`의 `korean_name`, `normalized_name`, `aliases`, `query_keywords`에서 query를 생성한다. 각 query에는 `korean_name`, `normalized_name`, `alias`, `query_keyword` origin이 기록되며, review artifact에서 query origin별 품질을 확인한다. Google News/RSS는 아직 구현하지 않고, 이후 같은 query strategy 계층을 재사용해 확장한다.

`TRENDS_DISCOVERY_REVIEW_ENABLED=true`이면 runtime은 Naver discovery 실행 후 `.local/trends-analyzer/discovery_reviews/latest_naver_news_review.json`에 review/calibration artifact를 저장한다. 이 artifact는 Core 결과가 아니라 query tuning을 위한 운영 검토 자료다.

## 13. 예시 `.env.local`

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

TRENDS_ACTIVE_SOURCES=fixture
TRENDS_SOURCE_SYMBOLS=005930,000660
TRENDS_SOURCE_PARTIAL_SUCCESS=true
```

## 14. 예시 `.env.oci`

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

TRENDS_ACTIVE_SOURCES=kis,kiwoom
TRENDS_SOURCE_SYMBOLS=005930,000660
TRENDS_SOURCE_SYMBOL_POLICY=explicit
TRENDS_SOURCE_SYMBOL_MARKETS=KOSPI,KOSDAQ
TRENDS_SOURCE_SYMBOL_CLASSIFICATIONS=stock
TRENDS_SOURCE_SYMBOL_LIMIT=20
TRENDS_SOURCE_SYMBOL_VALID_CODE_ONLY=true
TRENDS_SOURCE_PARTIAL_SUCCESS=true
TRENDS_SYMBOL_CATALOG_SOURCE=kis_master
TRENDS_SYMBOL_CATALOG_MARKETS=KOSPI,KOSDAQ,KONEX
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_TR_ID_INVEST_OPINION=FHKST663300C0
KIS_INVEST_OPINION_LOOKBACK_DAYS=180
KIS_INVEST_OPINION_LIMIT_PER_SYMBOL=5
KIWOOM_MODE=KIWOOM_REAL
KIWOOM_BASE_URL=https://api.kiwoom.com
TRENDS_NAVER_NEWS_ENABLED=false
TRENDS_NAVER_QUERY_LIMIT_PER_SYMBOL=2
TRENDS_NAVER_RESULT_LIMIT_PER_QUERY=5
TRENDS_NAVER_INCLUDE_ALIASES=false
TRENDS_NAVER_INCLUDE_QUERY_KEYWORDS=true
TRENDS_DISCOVERY_REVIEW_ENABLED=true
```

## 15. 구현 시 주의사항

- 설정 로더는 `src/shared/config.py` 또는 equivalent에 둔다.
- UseCase는 이미 파싱된 settings 객체를 주입받아야 하며, 환경 변수를 직접 읽지 않는다.
- secret 값은 로그에 남기지 않는다.
- 장중 override는 MVP에서 비활성화한다.
- OCI 단일 서버에서는 worker concurrency를 보수적으로 유지한다.
- 로컬과 예비 노트북에서 통과한 설정 조합만 OCI에 반영한다.
- KIS/Kiwoom provider 응답 필드는 Core contract로 직접 누수하지 않고 `RawNewsItem.metadata`에 보존한다.
