# PDCA Report: Workspace Alignment & Core Enhancement (workspace-alignment-v1)

## 1. 개요 (Abstract)
본 보고서는 `workspace-alignment-v1` 계획에 따른 구현 결과를 요약합니다. 핵심 데이터 계약 보완, Adapter 확장, API Route 및 장중 보호 정책(Market Hours Guard) 구현을 성공적으로 완료하였습니다.

## 2. 구현 결과 (Implementation Results)

### 2.1 Contract & Model
*   `src/contracts/core.py`: `NewsEvaluation`에 신규 점수 필드(`urgency`, `actionability`, `content_value`) 및 `credibility_breakdown` 반영.
*   `src/contracts/payloads.py`: `GenericInsightPayload`, `WorkflowTriggerPayload` 추가.

### 2.2 Core Logic
*   `src/core/score.py`: `MockNewsScorer`를 확장하여 신규 필드 데이터 생성 (Mock 수준 유지).

### 2.3 Adapter Implementation
*   `src/adapters/generic/adapter.py`: Generic 소비자용 어댑터 구현.
*   `src/adapters/workflow/adapter.py`: n8n/Workflow 소비자용 어댑터 구현.

### 2.4 API Layer & Policy
*   `src/api/routes/`: `ingest`, `signals`, `qts`, `generic`, `workflow`, `ops` 라우트 구축 및 `/api/v1` 네임스페이스 등록.
*   `src/api/dependencies.py`: `verify_market_hours` 가드 구현.
*   `src/api/routes/ingest.py`: 장중 heavy job 차단 정책 적용.

## 3. 검증 결과 (Verification Results)
*   `tests/test_workspace_alignment_v1.py`를 통해 다음 사항을 검증 완료:
    *   **장중 차단**: KST 10:00 AM 요청 시 `409 Conflict` (MARKET_HOURS_GUARD) 발생 확인.
    *   **경량 허용**: 동일 시간에 n8n webhook 등 lightweight 요청 정상 처리 확인.
*   `PYTHONPATH=. pytest`를 통한 전체 테스트 통과 확인.

## 4. 학습 및 개선 (Lessons Learned & Act)
*   **교훈**: Contract를 먼저 확정함으로써 다수의 Adapter와 API Route를 일관성 있게 빠르게 구축할 수 있었습니다.
*   **차기 과제**: 현재 Mock 수준인 `NewsScorer`를 실제 `docs/specification/data/news_credibility_spec.md` 명세에 따른 로직으로 정교화하고, n8n 실제 연동 테스트를 진행할 예정입니다.
