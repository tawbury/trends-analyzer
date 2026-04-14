# 미결 의사결정 목록

## 1. 목적

이 문서는 Trend Intelligence Platform 구현 전에 추가로 확정해야 할 의사결정을 추적한다.

## 2. API 및 인증

- 운영 API 인증 방식을 선택해야 한다.
  - 후보: Bearer token, reverse proxy 인증, 내부망 제한, mTLS
- n8n webhook endpoint의 인증 방식을 결정해야 한다.
- QTS가 API polling을 사용할지, DB read model을 읽을지 결정해야 한다.
- public API와 internal API를 분리할지 결정해야 한다.

## 3. 데이터베이스 및 저장소

- PostgreSQL migration 도구를 선택해야 한다.
  - 후보: Alembic, raw SQL migration, lightweight custom migration
- JSONL 보조 저장소를 어느 단계까지 유지할지 결정해야 한다.
- `news_credibility_scores`를 별도 테이블로 정규화할지, `news_evaluations`의 JSONB 필드로 둘지 결정해야 한다.
- snapshot과 adapter payload의 retention 기간을 운영 비용 기준으로 재검토해야 한다.

## 4. 뉴스 신뢰도

- source tier 초기 설정 파일 위치를 결정해야 한다.
  - 후보: `config/source_tiers.yaml`, DB table, hybrid
- 신뢰도 산식의 weight를 수동 검증 샘플셋으로 조정해야 한다.
- LLM이 신뢰도 산정에 참여할 경우 어느 component까지 개입할지 결정해야 한다.
- corroboration 판단에 제목 유사도만 사용할지 embedding/semantic similarity를 사용할지 결정해야 한다.

## 5. n8n 연동

- n8n inbound payload schema를 확정해야 한다.
- outbound workflow dispatch의 idempotency key를 설계해야 한다.
- 낮은 confidence/high urgency signal의 manual review workflow를 정의해야 한다.
- dispatch 실패 시 retry 정책과 dead-letter 보관 방식을 결정해야 한다.

## 6. 런타임 및 배포

- OCI 초기 배포 방식을 결정해야 한다.
  - 후보: 단일 Docker container, docker compose, 기존 배포 체계 편입
- API service와 batch worker를 같은 container로 시작할지 분리할지 결정해야 한다.
- scheduler를 cron으로 둘지 앱 내부 scheduler로 둘지 결정해야 한다.
- CPU/메모리 상한과 batch concurrency limit를 정해야 한다.

## 7. QTS 통합

- QTS가 어떤 주기로 `QTSInputPayload`를 소비할지 결정해야 한다.
- 낮은 confidence signal을 QTS payload에서 어떻게 표현할지 확정해야 한다.
- QTS 내부 모듈화 재검토 시점과 판단 지표를 운영 지표로 구체화해야 한다.

## 8. 개발 워크플로우

- Codex, Claude Code, Gemini CLI가 공유할 문서 업데이트 규칙을 확정해야 한다.
- spec 변경 시 PR 또는 commit message convention을 정해야 한다.
- 테스트 fixture용 샘플 뉴스 세트를 어디에 둘지 결정해야 한다.
