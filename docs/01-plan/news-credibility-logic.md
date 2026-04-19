# PDCA Plan: News Credibility Logic implementation (news-credibility-logic)

## 1. 개요 (Abstract)

`docs/specification/data/news_credibility_spec.md` 명세에 따라 단순 Mock 수준이었던 뉴스 신뢰도 평가 로직을 정교화한다. 뉴스 소스의 등급(Tier)과 기사 본문의 품질, 근거 유무, 교차 검증 여부 등을 종합하여 `confidence_score`와 세부 `credibility_breakdown`을 산출하는 독립 모듈을 구축한다.

## 2. 가치 제안 (Value Proposition)

- **정밀한 필터링**: 저신뢰 루머나 출처 불분명한 정보가 QTS의 매매 의사결정에 미치는 영향을 최소화한다.
- **설명 가능성**: 단순 점수가 아닌 7가지 구성 요소(Source Weight, Evidence, Corroboration 등)를 제공하여 분석 결과의 근거를 명확히 한다.
- **리스크 관리**: 신뢰도가 낮은 고영향도(High Impact) 뉴스에 대해 수동 검토나 주의(Watch) 단계를 유도하여 안정적인 운영을 돕는다.

## 3. 기능 범위 (Scope)

### 3.1 Contract & Model 확장
- [ ] `src/contracts/core.py`: `NewsCredibilityScore` 데이터 클래스 추가 (breakdown 상세 필드 포함).

### 3.2 Credibility 엔진 구현
- [ ] `src/core/credibility.py`: 신규 모듈 생성.
    - [ ] `SourceTier` 정의 및 티어별 `source_weight` 관리.
    - [ ] 기사 텍스트 기반 `evidence_score`, `content_quality_score`, `rumor_penalty` 산출 엔진(Rule-based/LLM-assisted).
    - [ ] 최종 `confidence_score` 산식 구현 및 `method_version` 관리.

### 3.3 Scorer 연동
- [ ] `src/core/score.py`: `MockNewsScorer`를 실제 `NewsScorer`로 전환하고 `credibility.py`의 로직을 호출하도록 수정.
- [ ] 기사 정규화 정보(URL 유무, 본문 길이 등)를 신뢰도 평가의 입력값으로 활용.

### 3.4 API 및 Adapter 대응
- [ ] `src/api/routes/signals.py`: `NewsEvaluation` 조회 시 확장된 `credibility_breakdown`이 정상 노출되는지 확인.
- [ ] `src/adapters/qts/adapter.py`: `confidence_score` 임계치 기반 필터링 정책 강화.

## 4. 구현 전략 (Implementation Strategy)

1.  **Rule-based Engine First**: 초기에는 정규 표현식과 특정 키워드, 뉴스 출처 정보를 활용한 코드 기반 엔진을 우선 구축한다.
2.  **Breakdown Component Isolation**: 각 평가 지표(Evidence, Corroboration 등)를 계산하는 함수를 독립적으로 분리하여 테스트 가능성을 높인다.
3.  **Method Versioning**: 점수 산식이 변경될 때마다 버전을 명시하여 과거 평가 데이터와의 호환성을 관리한다.
4.  **Integration into Core Pipeline**: 기존의 `NewsScorer`가 이 엔진을 "평가 파이프라인의 핵심 단계"로 사용하게 만든다.

## 5. 검증 계획 (Verification Plan)

- **Unit Test**: 다양한 시나리오(공식 공시, 주요 외신, 루머성 기사, 출처 불명 데이터)에 대해 예상 점수 범위 내에 들어오는지 검증.
- **Breakdown Accuracy**: 각 페널티와 가중치가 의도한 대로 `confidence_score`를 깎거나 올리는지 개별 컴포넌트 테스트.
- **Contract Integrity**: API 응답에서 `credibility_breakdown`의 모든 필드가 누락 없이 반환되는지 확인.

## 6. 일정 및 우선순위 (Timeline & Priority)

1.  **P0 (Critical)**: `src/core/credibility.py` 기본 산식 구현, `NewsEvaluation` contract 연동.
2.  **P1 (High)**: 루머 및 품질 평가용 Rule-based 로직 고도화.
3.  **P2 (Normal)**: 교차 검증(Corroboration) 로직 연동 (Deduplication 정보 활용).
