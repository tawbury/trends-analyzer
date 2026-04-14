# 데이터 모델 명세

## 1. 범위

이 문서는 Trend Intelligence Platform의 핵심 엔티티, 점수 모델, adapter payload 계약을 정의한다.

데이터 모델은 다음 원칙을 따른다.

- Core entity와 Adapter payload를 분리한다.
- Adapter payload는 `TrendSnapshot` 또는 signal을 기준으로 재생성 가능해야 한다.
- 점수화 기준과 rules/prompt version을 추적할 수 있어야 한다.

## 2. Core 엔티티

### 2.1 RawNewsItem

원본 source에서 수집한 뉴스.

필드:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | yes | 내부 raw news id |
| `source` | string | yes | kis, kiwoom, rss, n8n 등 |
| `source_id` | string | no | source 원본 id |
| `title` | string | yes | 원문 제목 |
| `body` | string | no | 원문 본문 또는 summary |
| `url` | string | no | 원문 URL |
| `published_at` | datetime | no | 원문 게시 시각 |
| `collected_at` | datetime | yes | 수집 시각 |
| `language` | string | no | ko, en 등 |
| `symbols` | list[string] | no | source가 제공한 symbol 힌트 |
| `metadata` | object | no | source별 부가 정보 |

### 2.2 NormalizedNewsItem

정규화가 끝난 뉴스.

필드:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | yes | normalized news id |
| `raw_news_id` | string | yes | 원본 RawNewsItem id |
| `normalized_title` | string | yes | 정규화된 제목 |
| `normalized_body` | string | no | 정규화된 본문 |
| `canonical_url` | string | no | 정규화 URL |
| `published_at` | datetime | no | timezone 보정된 게시 시각 |
| `language` | string | yes | 정규화된 언어 코드 |
| `dedup_key` | string | yes | 중복 제거 키 |
| `content_hash` | string | yes | 제목/본문 기반 hash |

### 2.3 NewsEvaluation

뉴스별 평가 결과.

필드:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | yes | evaluation id |
| `normalized_news_id` | string | yes | 평가 대상 |
| `relevance_score` | float | yes | 관련성 |
| `sentiment_score` | float | yes | 감성 |
| `impact_score` | float | yes | 영향도 |
| `confidence_score` | float | yes | 신뢰도 |
| `novelty_score` | float | yes | 새로움 |
| `source_weight` | float | yes | source 가중치 |
| `actionability_score` | float | yes | 후속 행동 가능성 |
| `urgency_score` | float | yes | 긴급도 |
| `content_value_score` | float | yes | 콘텐츠 가치 |
| `credibility_breakdown` | object | yes | 신뢰도 산정 세부 요소 |
| `themes` | list[string] | no | 매핑된 테마 |
| `sectors` | list[string] | no | 매핑된 섹터 |
| `symbols` | list[string] | no | 매핑된 종목 |
| `rules_version` | string | yes | 점수화 룰 버전 |
| `evaluated_at` | datetime | yes | 평가 시각 |

점수 범위:

- 기본 범위는 `0.0 <= score <= 1.0`이다.
- `sentiment_score`는 필요 시 `-1.0 <= sentiment_score <= 1.0`를 허용할 수 있으나, API와 DB schema에 명시해야 한다.
- `confidence_score`는 `credibility_breakdown`의 구성 요소를 결합한 최종값이어야 한다.
- 신뢰도 세부 기준은 `docs/specification/data/news_credibility_spec.md`를 따른다.

`credibility_breakdown` 예시:

```json
{
  "source_tier": "tier_2_market_media",
  "source_weight": 0.75,
  "evidence_score": 0.7,
  "corroboration_score": 0.4,
  "content_quality_score": 0.8,
  "freshness_score": 0.9,
  "conflict_penalty": 0.0,
  "rumor_penalty": 0.0,
  "method_version": "credibility-v0.1"
}
```

### 2.4 MarketSignal

시장 단위 signal.

필드:

- `id`
- `snapshot_id`
- `market`
- `market_bias`
- `impact_score`
- `confidence_score`
- `driver_themes`
- `driver_news_ids`
- `generated_at`

### 2.5 ThemeSignal

테마 단위 signal.

필드:

- `id`
- `snapshot_id`
- `theme`
- `sector`
- `rank`
- `momentum_score`
- `impact_score`
- `confidence_score`
- `news_count`
- `driver_news_ids`
- `generated_at`

### 2.6 StockSignal

종목 단위 signal.

필드:

- `id`
- `snapshot_id`
- `symbol`
- `name`
- `themes`
- `relevance_score`
- `sentiment_score`
- `impact_score`
- `confidence_score`
- `urgency_score`
- `driver_news_ids`
- `generated_at`

### 2.7 TrendSnapshot

특정 분석 시점의 signal 묶음.

필드:

- `id`
- `as_of`
- `window_start`
- `window_end`
- `market_signals`
- `theme_signals`
- `stock_signals`
- `evaluation_count`
- `rules_version`
- `created_at`

## 3. Adapter Payload

### 3.1 QTSInputPayload

QTS용 의사결정 보조 payload.

필드:

- `id`
- `snapshot_id`
- `market_bias`
- `universe_adjustments`
- `risk_overrides`
- `sector_weights`
- `strategy_activation_hints`
- `confidence_score`
- `generated_at`
- `expires_at`
- `rules_version`

규칙:

- 실제 매매 명령을 포함하지 않는다.
- risk override는 QTS Adapter에서만 생성한다.
- Core score 원본을 수정하지 않는다.

### 3.2 GenericInsightPayload

브리핑/랭킹/관심 후보/알림용 payload.

필드:

- `id`
- `snapshot_id`
- `daily_briefing`
- `theme_ranking`
- `watchlist_candidates`
- `alert_summary`
- `report_seed`
- `generated_at`

### 3.3 WorkflowTriggerPayload

n8n 및 자동화 시스템용 payload.

필드:

- `id`
- `snapshot_id`
- `trigger_type`
- `priority`
- `recommended_actions`
- `routing_conditions`
- `downstream_payload`
- `dispatch_policy`
- `generated_at`

규칙:

- dispatch 실행 결과는 payload와 별도 로그로 저장한다.
- 장중 대규모 자동화 트리거는 금지한다.

## 4. 버전 관리

추적 대상:

- `rules_version`
- `prompt_version`
- `model_version`
- `mapping_version`
- `adapter_version`

권장:

- Core evaluation에는 `rules_version`을 필수로 둔다.
- LLM 또는 외부 모델을 사용하면 `model_version`과 `prompt_version`을 기록한다.
- Adapter payload에는 `adapter_version`을 둔다.
- 신뢰도 산정 방식이 바뀌면 `credibility_method_version` 또는 `credibility_breakdown.method_version`을 갱신한다.

## 5. Nullability 원칙

- source가 제공하지 않는 원문 정보는 nullable로 둔다.
- Core 산출물의 점수 필드는 nullable로 두지 않는다.
- 알 수 없는 값은 `null`과 빈 배열을 구분한다.
- 빈 배열은 "확인했지만 없음"을 의미한다.
- `null`은 "아직 평가하지 않았거나 source가 제공하지 않음"을 의미한다.
