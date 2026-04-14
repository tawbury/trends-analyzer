# News Credibility Spec

## 1. 범위

이 문서는 뉴스 신뢰도 평가 기준과 `confidence_score` 산정 방식을 정의한다.

신뢰도 평가는 Core 계층의 책임이며, 권장 구현 위치는 `src/core/credibility.py`다.

목표:

- source 자체의 신뢰도와 기사 내용의 신뢰도를 분리한다.
- 단일 LLM 판단값이 아니라 설명 가능한 breakdown 기반으로 `confidence_score`를 만든다.
- QTS Adapter가 낮은 신뢰도 signal을 과도하게 매매 보조 payload에 반영하지 않도록 한다.
- 추후 source별 튜닝과 사후 검증이 가능하도록 산정 근거를 저장한다.

## 2. 핵심 원칙

- `confidence_score`는 `0.0 <= confidence_score <= 1.0` 범위를 기본으로 한다.
- 높은 source tier라도 기사 내용이 빈약하면 낮은 confidence를 허용한다.
- 낮은 source tier라도 공식 원문 링크나 다중 검증이 있으면 confidence를 보정할 수 있다.
- n8n 유입 데이터는 upstream provenance가 없으면 낮은 source tier로 시작한다.
- 루머, 추측, 익명 출처, 과장된 단정 표현은 penalty를 적용한다.
- Core는 최종 점수뿐 아니라 breakdown을 저장한다.

## 3. Source Tier

초기 tier 제안:

| Tier | 예시 | 기본 weight |
|------|------|-------------|
| `tier_0_official` | 거래소, 공시, 기업 IR, 정부/중앙은행 공식 발표 | 0.95 |
| `tier_1_primary_market` | KIS, Kiwoom 원문 뉴스, 증권사 리서치 원문 | 0.85 |
| `tier_2_market_media` | 주요 경제지, 주요 외신, 검증된 전문 매체 | 0.75 |
| `tier_3_general_media` | 일반 언론, RSS aggregation | 0.60 |
| `tier_4_automation_inbound` | n8n 유입 데이터, 외부 자동화 수집 데이터 | 0.45 |
| `tier_5_unverified` | 출처 불명, 커뮤니티성, 검증 전 제보 | 0.25 |

규칙:

- source tier는 설정 파일 또는 DB로 관리 가능해야 한다.
- source tier 변경은 `source_weight` 변화로 이어지므로 사후 분석 가능해야 한다.
- source tier는 신뢰도의 출발점일 뿐 최종 점수가 아니다.

## 4. Credibility Components

| 구성 요소 | 범위 | 설명 |
|-----------|------|------|
| `source_weight` | 0.0~1.0 | source tier 기반 기본 가중치 |
| `evidence_score` | 0.0~1.0 | 원문 링크, 공식 인용, 수치, 문서 근거 포함 정도 |
| `corroboration_score` | 0.0~1.0 | 독립 source에서 같은 내용이 확인되는 정도 |
| `content_quality_score` | 0.0~1.0 | 제목/본문 완성도, 광고성/스팸성/과장 표현 여부 |
| `freshness_score` | 0.0~1.0 | 분석 window 기준 시의성 |
| `conflict_penalty` | 0.0~1.0 | 기존 고신뢰 source와 충돌하는 정도 |
| `rumor_penalty` | 0.0~1.0 | 루머/추측/익명 출처 표현 강도 |

## 5. Scoring Formula

초기 산식:

```text
base_score =
  source_weight * 0.35
  + evidence_score * 0.20
  + corroboration_score * 0.20
  + content_quality_score * 0.15
  + freshness_score * 0.10

penalty =
  conflict_penalty * 0.20
  + rumor_penalty * 0.15

confidence_score = clamp(base_score - penalty, 0.0, 1.0)
```

주의:

- 이 산식은 MVP 기준이며, 실제 샘플 검증 후 조정한다.
- weight 조정 시 `method_version`을 반드시 올린다.
- LLM을 사용하더라도 LLM 결과는 `content_quality_score`, `evidence_score` 보조 입력으로만 사용하고 최종 산식은 코드로 결정한다.

## 6. Corroboration Rules

독립 source 판정 기준:

- 같은 URL 재게시나 동일 press release 복붙은 독립 source로 보지 않는다.
- 서로 다른 매체라도 본문이 거의 같으면 낮은 corroboration을 부여한다.
- 공식 원문과 주요 매체 보도가 함께 있으면 높은 corroboration을 부여한다.
- n8n inbound와 RSS aggregation만 있는 경우 corroboration을 낮게 둔다.

권장 구현:

- deduplication 결과의 cluster id를 활용한다.
- `content_hash`, `canonical_url`, 제목 유사도, source group을 함께 본다.

## 7. Penalty Rules

`rumor_penalty` 후보:

- "rumor", "unconfirmed", "소문", "추정", "가능성", "관계자에 따르면" 같은 표현이 강함
- 원문 링크가 없거나 source provenance가 없음
- 제목만 있고 본문이 매우 짧음
- 과도한 clickbait 표현

`conflict_penalty` 후보:

- 같은 symbol/theme에 대해 고신뢰 source가 반대 내용을 보도함
- 공식 발표와 상충함
- 이전 snapshot의 확정 signal과 강하게 충돌하지만 corroboration이 낮음

## 8. Data Contract

`NewsEvaluation`은 다음 필드를 포함한다.

```json
{
  "confidence_score": 0.68,
  "source_weight": 0.75,
  "credibility_breakdown": {
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
}
```

## 9. Persistence

저장 방식:

- `news_evaluations.confidence_score`: 최종 점수
- `news_evaluations.source_weight`: source tier 기반 가중치
- `news_credibility_scores`: breakdown 저장

`news_credibility_scores` 권장 필드:

| 필드 | 설명 |
|------|------|
| `id` | credibility score id |
| `news_evaluation_id` | 평가 결과 참조 |
| `source_tier` | source tier |
| `source_weight` | source 기본 가중치 |
| `evidence_score` | 근거성 점수 |
| `corroboration_score` | 다중 source 검증 점수 |
| `content_quality_score` | 내용 품질 점수 |
| `freshness_score` | 시의성 점수 |
| `conflict_penalty` | 충돌 penalty |
| `rumor_penalty` | 루머 penalty |
| `method_version` | 산정 방식 버전 |
| `created_at` | 생성 시각 |

## 10. Adapter Usage

QTS Adapter:

- 낮은 `confidence_score`의 signal은 risk override와 universe adjustment에 강하게 반영하지 않는다.
- 권장 threshold는 MVP에서 `0.65` 이상으로 시작하고 샘플 검증 후 조정한다.
- 낮은 신뢰도지만 high impact인 경우 `watch` 또는 `review_required`로 분리한다.

Generic Adapter:

- briefing에는 confidence label을 함께 제공할 수 있다.
- 낮은 신뢰도 뉴스는 "확인 필요"로 표시한다.

Workflow Adapter:

- 낮은 confidence와 높은 urgency가 동시에 있으면 자동 dispatch 대신 manual review action을 추천한다.

## 11. 운영 검증

수동 검증 샘플셋:

- official source confirmed
- major media single-source
- multi-source corroborated
- rumor/unverified
- conflicting reports
- n8n inbound without provenance

각 샘플에 대해 다음을 기록한다.

- expected tier
- expected confidence range
- actual confidence score
- false positive/false negative 여부
- 조정 필요 component
