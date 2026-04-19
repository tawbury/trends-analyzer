# PDCA Design: News Credibility Logic implementation (news-credibility-logic)

## 1. 개요 (Abstract)
본 설계 문서는 뉴스 기사의 신뢰도를 정량화하기 위한 `src/core/credibility.py` 모듈의 상세 구조와 `NewsScorer`와의 연동 방식을 정의합니다. `news_credibility_spec.md`에 정의된 7가지 지표와 산식을 코드로 구현합니다.

## 2. 모듈 설계 (Module Design)

### 2.1 Source Tier 관리
뉴스 소스(Source)별 티어를 매핑합니다.

| Source ID (Pattern) | Tier | Source Weight |
| :--- | :--- | :--- |
| `official:*`, `dart:*` | `tier_0_official` | 0.95 |
| `kis:*`, `kiwoom:*` | `tier_1_primary_market` | 0.85 |
| `reuters:*`, `bloomberg:*` | `tier_2_market_media` | 0.75 |
| `rss:*` | `tier_3_general_media` | 0.60 |
| `n8n:*` | `tier_4_automation_inbound` | 0.45 |
| `*` (default) | `tier_5_unverified` | 0.25 |

### 2.2 Credibility 엔진 (`src/core/credibility.py`)
`NewsCredibilityEngine` 클래스를 구현합니다.

*   **`calculate_scores(item: NormalizedNewsItem) -> NewsCredibilityScore`**:
    *   **`source_weight`**: `item.source`를 기반으로 티어 매핑.
    *   **`evidence_score`**: 본문 내 URL 포함 여부, 숫자/통계 표현 밀도, "공시", "발표" 등 키워드 확인.
    *   **`content_quality_score`**: 본문 길이(너무 짧으면 감점), 특수문자 남발 여부 확인.
    *   **`rumor_penalty`**: "루머", "추측", "관계자에 따르면", "미확인" 등 키워드 포함 시 페널티 부여.
    *   **`freshness_score`**: `published_at`과 현재 시각의 차이 기반 산출.
    *   **`confidence_score`**: 명세에 정의된 가중 합산 산식 적용.

### 2.3 데이터 계약 확장 (`src/contracts/core.py`)
세부 지표를 담을 데이터 클래스를 추가합니다.

```python
@dataclass(frozen=True)
class NewsCredibilityScore:
    source_tier: str
    source_weight: float
    evidence_score: float
    corroboration_score: float
    content_quality_score: float
    freshness_score: float
    conflict_penalty: float
    rumor_penalty: float
    confidence_score: float
    method_version: str
```

## 3. 연동 설계 (Integration)

*   **`NewsScorer`**: `NewsCredibilityEngine`을 주입받아 `evaluate()` 호출 시 신뢰도 점수를 계산하고 `NewsEvaluation.credibility_breakdown`에 딕셔너리 형태로 저장합니다.

## 4. 테스트 케이스 (Test Cases)
1.  **공식 뉴스**: `source="kis"`, 본문에 수치와 링크 포함 -> `confidence_score` > 0.8 예상.
2.  **루머 뉴스**: 본문에 "소문에 따르면" 포함 -> `rumor_penalty` 적용, 점수 급락 예상.
3.  **부실 뉴스**: 본문이 매우 짧고 출처 불분명 -> `tier_5` 적용, 저점수 예상.
