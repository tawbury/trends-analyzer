# PDCA Report: News Credibility Logic implementation (news-credibility-logic)

## 1. 개요 (Abstract)
본 보고서는 `news-credibility-logic` 계획에 따른 뉴스 신뢰도 평가 엔진 구현 결과를 요약합니다. 단순 Mock 점수 체계에서 벗어나, 소스 티어와 기사 품질을 결합한 정교한 7개 지표 기반 신뢰도 산출 체계를 구축하였습니다.

## 2. 구현 결과 (Implementation Results)

### 2.1 Contract & Model
*   `src/contracts/core.py`: `NewsCredibilityScore` 데이터 클래스 추가 및 `NormalizedNewsItem`에 `source` 필드 추가. `NewsEvaluation`과의 정합성을 확보하였습니다.

### 2.2 Credibility 엔진 구현
*   `src/core/credibility.py`: `NewsCredibilityEngine` 클래스 구현.
    *   **Source Tier Mapping**: 6단계 티어 시스템 및 가중치 적용.
    *   **Evidence Scoring**: URL, 공식 키워드, 수치 데이터 포함 여부 분석.
    *   **Quality & Rumor Analysis**: 본문 길이 기반 품질 및 루머성 키워드 기반 페널티 산출.
    *   **Formula**: 7가지 요소를 가중 합산하는 `credibility-v0.1` 산식 적용.

### 2.3 Scorer 연동
*   `src/core/score.py`: `MockNewsScorer`를 정식 `NewsScorer`로 전환. 엔진을 주입받아 평가 시점에 `credibility_breakdown`을 상세히 기록하도록 변경하였습니다.

## 3. 검증 결과 (Verification Results)
*   `tests/test_news_credibility.py`를 통해 다음 시나리오 검증 완료:
    *   **공식 뉴스**: DART 등 공식 소스 기반 고신뢰도(0.65 이상) 산출 확인.
    *   **루머 뉴스**: "소문" 등 키워드 포함 시 페널티 적용 및 저신뢰도(0.5 이하) 확인.
    *   **부실 뉴스**: 본문이 짧고 출처 불분명한 경우 최소 신뢰도(0.3 미만) 확인.

## 4. 학습 및 개선 (Lessons Learned & Act)
*   **교훈**: 단일 점수가 아닌 7가지 세부 지표(Breakdown)를 제공함으로써, 향후 오판 사례 발생 시 어떤 가중치나 페널티를 조정해야 할지 명확한 가이드라인을 확보하였습니다.
*   **차기 과제**: 중복 제거(Deduplication) 로직과 연동하여, 동일 기사가 여러 매체에서 보도될 경우 `corroboration_score`를 자동으로 올리는 기능을 추가할 예정입니다.
