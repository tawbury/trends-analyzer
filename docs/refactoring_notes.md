# 리팩터링 노트 및 설계 보정 사항

## 1. 목적

이 문서는 기존 초안에서 개념적으로 모호했던 부분과 이번 개정에서 보정한 내용을 기록한다.

## 2. 기존 문서의 모호점

### 2.1 시스템 정체성이 QTS 중심으로 읽힐 수 있음

기존 초안은 QTS 연계를 강조하다 보니 플랫폼 자체가 QTS 내부 기능처럼 해석될 여지가 있었다.

보정:

- 문서 전반에서 시스템을 독립 Trend Intelligence Platform으로 정의했다.
- QTS는 하나의 consumer로 격리했다.
- QTS 관련 정책은 QTS Adapter 책임으로 제한했다.

### 2.2 Core와 QTS 정책 경계가 더 명확해야 했음

기존 문서에는 QTS payload 예시가 있었지만 Core가 어디까지 알아야 하는지 명확하지 않았다.

보정:

- Core는 neutral signal만 만든다고 명시했다.
- `market_bias`, `risk_overrides`, `universe_adjustments`는 QTS Adapter output으로 분리했다.

### 2.3 Generic payload와 Workflow payload가 섞일 위험

브리핑/랭킹 payload와 n8n automation control payload는 목적이 다르다.

보정:

- Generic Adapter와 Workflow Adapter를 별도 concern으로 문서화했다.
- Workflow Adapter는 `trigger_type`, `priority`, `recommended_actions`, `routing_conditions`를 책임진다고 명시했다.

### 2.4 API Layer가 부가 기능처럼 보일 수 있음

기존 초안은 API 목록은 있었지만 API Layer가 구조적으로 왜 중요한지 더 설명이 필요했다.

보정:

- API-first를 공식 아키텍처 원칙으로 승격했다.
- API를 QTS, Generic, n8n, ops의 안정적 계약으로 정의했다.

### 2.5 Runtime boundary가 부족했음

초안에는 batch/API/scheduler가 언급되었지만 runtime 분리 기준이 부족했다.

보정:

- API Service, Batch Worker, Scheduler, Webhook Runtime, future Embedded Runtime을 분리했다.

### 2.6 스케줄링 정책이 구현 기준으로 부족했음

장중 비구동 원칙은 있었지만 route, batch runner, scheduler에 어떻게 반영할지가 부족했다.

보정:

- KST 09:00~15:30 제한을 명시했다.
- 허용/금지 작업을 분리했다.
- scheduler와 runner 양쪽에서 guard를 적용하도록 문서화했다.

### 2.7 뉴스 신뢰도 산정 기준이 얕았음

기존 문서에는 `confidence_score`와 `source_weight`만 있었고 breakdown 기준이 부족했다.

보정:

- `news_credibility_spec.md`를 추가했다.
- source tier, evidence, corroboration, content quality, freshness, penalty 기반 산식을 제안했다.

### 2.8 UseCase 계층이 구조적으로 고정되지 않았음

API, Batch, Scheduler가 Core/Adapter를 직접 조합할 수 있는 여지가 있었다.

보정:

- `application/use_cases`를 orchestration boundary로 명시했다.
- API route, batch runner, scheduler는 UseCase를 호출하고 Core/Adapter 직접 조합을 피하도록 문서화했다.

### 2.9 Contracts 계층이 추상적으로만 언급되었음

계약이라는 용어는 있었지만 core signal, payload, API DTO, runtime/job 계약이 어디에 위치해야 하는지 불명확했다.

보정:

- `src/contracts/`를 전용 계층으로 추가했다.
- `core.py`, `payloads.py`, `api.py`, `runtime.py`, `ports.py`로 분리했다.

### 2.10 Workflow 명칭이 과부하되어 있었음

Workflow Adapter, n8n gateway, dispatch runtime이 모두 workflow로 뭉쳐 보일 수 있었다.

보정:

- Workflow Adapter는 payload mapping만 담당한다고 명시했다.
- n8n HTTP/webhook/dispatch는 `integration/n8n` 책임으로 분리했다.
- runtime dispatch는 UseCase와 integration port를 통해 수행하도록 정리했다.

### 2.11 운영/관측성과 배포 토폴로지가 약했음

초기 OCI 단일 서버 운영에서 필요한 로그, job id, health/readiness, entrypoint가 부족했다.

보정:

- `observability_ops.md`를 추가했다.
- `deployment_topology.md`를 추가했다.
- `docs_index.md`로 문서 권위 기준을 정리했다.

### 2.12 v0.3에서도 실제 소스 구조의 UseCase/Contracts 고정이 더 필요했음

v0.2 문서는 UseCase와 contracts를 개념적으로 설명했지만, 구현 에이전트가 실제 `src/` 구조를 만들 때 API나 Batch가 Core/Adapter를 직접 조합할 여지가 남아 있었다.

보정:

- `src/application/use_cases/`를 공식 orchestration boundary로 다시 명시했다.
- `src/contracts/`를 first-class 계층으로 고정했다.
- `src/contracts/core.py`, `payloads.py`, `api.py`, `runtime.py`, `ports.py` 분리를 문서화했다.
- API route, Batch runner, Scheduler는 UseCase를 호출하고 Core/Adapter/Repository 직접 조합을 하지 않도록 dependency direction을 보강했다.

### 2.13 Workflow 명칭이 여전히 과부하될 수 있었음

Workflow Adapter, n8n gateway, dispatch runtime이 모두 workflow라는 이름으로 묶이면 구현 위치가 흐려질 수 있었다.

보정:

- `src/adapters/workflow/`: neutral signal을 workflow payload로 변환하는 mapping 책임
- `src/integration/n8n/`: inbound webhook, signature verification, outbound HTTP gateway 책임
- `src/runtime/dispatch/`: dispatch 실행 정책, idempotency, retry, dispatch status 책임
- generic `src/workflow/` 같은 모호한 구조를 만들지 않도록 source module spec을 보정했다.

### 2.14 Neutral signal DTO와 Adapter payload DTO가 섞일 위험이 있었음

Signal API 예시가 QTS adapter 용어와 섞이면 Core가 QTS 정책을 아는 구조로 구현될 수 있다.

보정:

- Signal API는 neutral DTO만 반환한다고 명시했다.
- Core 방향성 힌트는 `bias_hint`로 표현한다.
- `market_bias`, `risk_overrides`, `universe_adjustments`는 QTS Adapter payload에서만 사용한다고 정리했다.

### 2.15 API 공통 계약과 환경 설정 기준이 구현 안전 수준까지 부족했음

API 인증, idempotency, webhook signature, error model, pagination/sort 규칙과 환경별 runtime flag가 더 구체화되어야 했다.

보정:

- `api_draft.md`와 `docs/spec/api_spec.md`에 auth mode, idempotency conflict, standard error response, async job response, pagination/filter/sort 기준을 보강했다.
- `environment_config.md`를 추가해 local/laptop/OCI 설정 차이, scheduler flag, market-hours guard flag, n8n secret/auth, source tier config path, runtime mode를 문서화했다.

### 2.16 문서 header 기준이 없어 drift 방지가 약했음

문서 인덱스는 있었지만 문서별 권위 범위, 상위 문서, 상태/version을 문서 본문에 표시하는 기준이 없었다.

보정:

- `document_metadata_standard.md`를 추가했다.
- 신규 문서와 크게 수정되는 문서에는 문서 유형, 상태, 권위 범위, 상위 문서, 관련 문서, 최종 수정일을 표시하도록 정리했다.

### 2.17 최종 정합성 패스에서 남은 경계 표현을 보정함

v0.3 이후에도 구현자가 읽을 때 Ingestion이 Application보다 위의 독립 orchestration layer처럼 보이거나, UseCase와 Runtime Dispatch의 최종 책임이 일부 겹쳐 보일 수 있었다.

보정:

- 아키텍처 다이어그램을 UseCase 중심으로 조정했다.
- Ingestion port/source client는 UseCase가 호출하는 하위 의존성이라고 명시했다.
- UseCase는 업무 흐름상 dispatch 요청과 correlation context 전달을 담당한다고 정리했다.
- Runtime Dispatch는 idempotency, retryability, 장중 정책, 실제 dispatch 실행 여부의 최종 execution-policy gate라고 명시했다.
- `api_draft.md`는 API 제품/개요 초안, `docs/spec/api_spec.md`는 구현 계약의 source of truth로 분리했다.
- `contracts/api.py`는 transport DTO 전용이며, 규모가 커지면 `api_requests.py`와 `api_responses.py`로 분리한다고 문서화했다.
- 핵심 권위 문서에 `document_metadata_standard.md` 형식의 metadata header를 추가했다.

### 2.18 구현 close-out에서 doc-to-code 추적성을 추가함

문서가 구현 가능한 상태가 되었지만, 구현 에이전트가 어떤 문서 섹션을 어떤 source file로 옮겨야 하는지 한 번 더 명시할 필요가 있었다.

보정:

- `implementation_traceability.md`를 추가했다.
- architecture concept, module/layer, contract, use case, API group, runtime concern을 권장 source directory/file로 매핑했다.
- 로컬 WSL2 검증용 MVP 구현 slice를 정의했다.
- 새 contract, UseCase, endpoint, runtime mode, env var가 생길 때 함께 갱신할 문서 규칙을 추가했다.
- API transport DTO는 MVP에서 `src/contracts/api.py`로 시작하고, 규모가 커질 때만 `api_requests.py`와 `api_responses.py`로 분리하도록 권장안을 명확히 했다.

## 3. 이번 개정에서 변경한 구조

신규/개정 문서:

- `master_planning.md`
- `architecture_specification.md`
- `module_design.md`
- `api_draft.md`
- `data_contract_draft.md`
- `runtime_scheduling_policy.md`
- `refactoring_notes.md`
- `example_code_appendix.md`
- `open_decisions.md`
- `observability_ops.md`
- `deployment_topology.md`
- `docs_index.md`
- `environment_config.md`
- `document_metadata_standard.md`
- `implementation_traceability.md`
- `docs/spec/*`

## 4. 아직 남은 구현 의사결정

상세 목록은 `open_decisions.md`에서 추적한다.
