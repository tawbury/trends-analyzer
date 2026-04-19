# PDCA Design: Corroboration Logic Enhancement (corroboration-logic)

> v1.0.0 | PDCA Design Phase

## Context Anchor

| Dimension | Content |
|-----------|---------|
| WHY | 단일 소스 보도보다 다중 소스 교차 확인된 정보에 높은 가중치를 부여하여 분석 신뢰도 향상 |
| WHO | 트렌드 분석가 및 시스템 자동 의사결정 모듈 |
| RISK | 과도한 점수 인플레이션, 클러스터링 오류로 인한 잘못된 신뢰도 상향 |
| SUCCESS | 동일 이슈에 대해 소스 개수가 늘어날수록 confidence_score가 합리적으로 상승 (Diminishing returns 적용) |
| SCOPE | Credibility 엔진 로직 확장 및 Aggregator 연동 구조 설계 |

## 1. Overview
`news_credibility_spec.md`의 교차 검증 규칙을 구현한다. 핵심은 `dedup_key`가 동일한 뉴스 그룹(클러스터) 내에서 서로 다른 `source`의 개수를 파악하여 `corroboration_score`를 산출하는 것이다.

## 2. Architecture Options

### Option A — Minimal Changes (Credibility 엔진 내부 처리)
- `calculate_scores` 메서드에 `related_items: list[NormalizedNewsItem]` 인자를 추가한다.
- 엔진 내부에서 `related_items`의 고유 소스 개수를 직접 계산한다.
- **장점**: 변경 범위가 좁고 로직이 직관적이다.
- **단점**: 점수 계산 시마다 주변 데이터를 넘겨줘야 하므로 호출부(UseCase)의 부담이 커진다.

### Option B — Clean Architecture (Pre-calculation Strategy)
- `CorroborationCalculator`라는 별도의 도메인 서비스를 만든다.
- UseCase는 먼저 모든 뉴스를 가져와서 Calculator를 통해 클러스터별 `corroboration_score` 맵을 생성한다.
- 그 후 각 뉴스의 `calculate_scores`를 호출할 때 계산된 점수를 주입한다.
- **장점**: 책임 분리가 명확하고, 대량 처리 시 최적화가 용이하다.
- **단점**: 새로운 클래스 및 인터페이스 추가로 구조가 복잡해진다.

### Option C — Pragmatic Balance (Aggregator 기반 사후 보정)
- 초기 `calculate_scores`에서는 기본 점수(0.2)만 부여한다.
- `TrendAggregator`에서 뉴스들을 그룹화할 때, 그룹 내 소스 다양성을 체크하여 최종 `confidence_score`를 보정(Boost)한다.
- **장점**: 기존 엔진 로직을 건드리지 않고 집계 단계에서 효율적으로 처리할 수 있다.
- **단점**: 개별 뉴스 자체의 `NewsEvaluation` 객체에는 최종 점수가 반영되지 않고 Aggregator 결과(Snapshot)에만 반영될 위험이 있다.

## 3. Selection & Rationale
**Option B (Clean Architecture)**를 선택한다.
- **이유**: 신뢰도 계산은 `core/credibility.py`의 고유 책임이다. 하지만 교차 검증은 "다른 뉴스들과의 관계"를 알아야 하므로, 개별 뉴스 객체 하나만으로는 계산할 수 없는 상태(Stateful/Contextual) 정보를 필요로 한다. 이를 별도의 도메인 서비스로 분리하여 UseCase에서 조정하는 것이 가장 깔끔한 경계를 유지한다.

## 4. Implementation Details

### 4.1 Corroboration Scoring Logic
- 소스 개수($N$)에 따른 점수 산식 (Diminishing Returns):
    - $N=1$: 0.2 (기본)
    - $N=2$: 0.5
    - $N=3$: 0.7
    - $N=4$: 0.85
    - $N \ge 5$: 1.0 (최대)

### 4.2 Module Changes
- `src/core/credibility.py`: `calculate_corroboration_score(items: list[NormalizedNewsItem]) -> float` 메서드 추가 및 `calculate_scores` 파라미터 업데이트.
- `src/application/use_cases/ingest_news.py` (또는 관련 UseCase): 신뢰도 계산 전 클러스터 그룹핑 및 점수 산출 로직 추가.

## 5. Session Guide
- `src/core/credibility.py` 수정: `calculate_corroboration_score` 구현 및 `calculate_scores`에 `corroboration_score` 주입 가능하도록 수정.
- `tests/test_news_credibility.py`에 교차 검증 테스트 케이스 추가.
