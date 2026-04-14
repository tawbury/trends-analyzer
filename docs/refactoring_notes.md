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
- `docs/spec/*`

## 4. 아직 남은 구현 의사결정

상세 목록은 `open_decisions.md`에서 추적한다.
