# PDCA Plan: Corroboration Logic Enhancement (corroboration-logic)

## 1. 개요 (Abstract)

`news_credibility_spec.md` 명세의 "교차 검증 규칙"을 구현하여 뉴스 신뢰도 평가를 고도화한다. 동일하거나 유사한 내용이 서로 다른 독립적인 뉴스 소스에서 공통적으로 발견될 경우 `corroboration_score`를 높여 최종 `confidence_score`를 상향 조정하는 로직을 구축한다.

## 2. 가치 제안 (Value Proposition)

- **신뢰성 극대화**: 단일 소스의 보도보다 여러 매체에서 교차 확인된 정보에 더 높은 가중치를 부여함으로써 분석의 정확도를 획기적으로 높인다.
- **오보/루머 필터링**: 특정 소스에서만 주장하는 독자적인 정보(Rumor 등)와 검증된 팩트를 정량적으로 구분할 수 있다.
- **분석 자동화**: 수작업 확인 없이 시스템이 자동으로 다중 소스 여부를 판단하여 인텔리전스 품질을 관리한다.

## 3. 기능 범위 (Scope)

### 3.1 Credibility 엔진 확장
- [ ] `src/core/credibility.py`: `calculate_corroboration_score` 함수 구현.
    - [ ] `NormalizedNewsItem`의 중복 제거 키(`dedup_key`) 또는 클러스터 정보를 활용하여 동일 클러스터 내의 고유 소스 개수 계산.
    - [ ] 소스 개수에 따른 점수 가산 로직 적용.

### 3.2 Aggregator 연동
- [ ] `src/core/aggregate.py`: 뉴스 평가 데이터 그룹화 시 클러스터 정보를 Scorer에게 전달하거나, 집계 단계에서 신뢰도를 재계산하는 구조 검토.

### 3.3 Scorer 고도화
- [ ] `src/core/score.py`: 개별 뉴스 평가 시 주변 뉴스(동일 클러스터)의 존재 여부를 고려하도록 로직 수정.

## 4. 구현 전략 (Implementation Strategy)

1.  **Cluster-based Scoring**: 분석 윈도우 내에서 동일한 `dedup_key`를 가진 뉴스들을 그룹핑하고, 이 그룹에 포함된 서로 다른 `source`의 개수를 확인한다.
2.  **Diminishing Returns**: 소스 개수가 늘어날수록 점수 가산폭을 조절하여 (예: 2개일 때 0.2, 5개일 때 0.5 등) 무한정 점수가 높아지는 것을 방지한다.
3.  **Cross-tier Validation**: `tier_0` 공식 소스와 일반 매체가 섞여 있을 때 더 높은 신뢰도를 부여하는 가중치 로직을 고려한다.

## 5. 검증 계획 (Verification Plan)

- **Corroboration Test**:
    - [ ] 동일한 뉴스가 1개 소스에서만 왔을 때와 3개 이상의 소스에서 왔을 때의 `confidence_score` 차이 비교.
    - [ ] 서로 다른 `dedup_key`를 가진 뉴스들은 상호 점수에 영향을 주지 않는지 확인.
