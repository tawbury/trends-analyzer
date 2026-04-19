# PDCA Plan: Ingest Persistence Implementation (ingest-persistence)

## 1. 개요 (Abstract)

`IngestNewsUseCase`에 실제 뉴스 수집 및 저장 로직을 구현한다. 수집된 `RawNewsItem`을 영구 저장소(JSONL 또는 DB)에 기록하고, 중복 수집 방지를 위한 식별 로직을 강화하여 분석 파이프라인의 입구(Ingestion Layer)를 완성한다.

## 2. 가치 제안 (Value Proposition)

- **데이터 보존**: API나 웹훅을 통해 들어온 모든 뉴스를 휘발시키지 않고 저장하여 사후 재분석 및 품질 검증의 토대로 활용한다.
- **추적성 확보**: `raw_news_id`를 기반으로 특정 뉴스가 어떤 분석 과정을 거쳐 최종 Signal에 영향을 주었는지 엔드투엔드 추적이 가능해진다.
- **안정적 수집**: 수집과 분석 단계를 저장소를 통해 분리함으로써, 대량 유입 시에도 시스템 부하를 안정적으로 관리할 수 있다.

## 3. 기능 범위 (Scope)

### 3.1 Port & Repository 구현
- [ ] `src/contracts/ports.py`: `RawNewsRepository` 추가.
- [ ] `src/db/repositories/jsonl.py`: `JsonlRawNewsRepository` 구현.

### 3.2 UseCase 실구현
- [ ] `src/application/use_cases/ingest_news.py`:
    - [ ] `RawNewsRepository`를 통한 영속성 로직 추가.
    - [ ] 수집 시각(`collected_at`) 자동 생성 및 ID 부여 로직 정교화.

### 3.3 Bootstrap & API 연동
- [ ] `src/bootstrap/container.py`: `RawNewsRepository` 및 `IngestNewsUseCase` 등록.
- [ ] `src/api/routes/ingest.py`: 실제 UseCase 호출을 통한 결과 반환.

## 4. 구현 전략 (Implementation Strategy)

1.  **Append-only Storage**: 초기에는 수정 없이 추가만 가능한 JSONL 기반 저장소를 구축하여 구현 속도와 데이터 무결성을 동시에 잡는다.
2.  **ID Generation**: `source:source_id` 조합을 해싱하거나 고유 패턴을 사용하여 멱등성(Idempotency) 있는 ID 체계를 구축한다.
3.  **Validation**: 저장 전 필수 필드(Title, Source 등) 유무를 검증하는 최소한의 가드를 둔다.

## 5. 검증 계획 (Verification Plan)

- **Persistence Test**: API 호출 후 지정된 경로의 `.jsonl` 파일에 데이터가 올바른 스키마로 기록되는지 확인.
- **Duplicate Test**: 동일한 `source_id`를 가진 뉴스를 재전송했을 때 중복 저장되지 않고 기존 ID를 반환하는지 확인.
