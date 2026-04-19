# PDCA Design: Ingest Persistence Implementation (ingest-persistence)

> v1.0.0 | PDCA Design Phase

## Context Anchor

| Dimension | Content |
|-----------|---------|
| WHY | 수집된 뉴스 데이터의 유실을 방지하고 분석 이력 추적성을 확보하기 위해 실제 영속성 계층 구현 |
| WHO | 시스템 운영자 및 사후 데이터 분석가 |
| RISK | 저장 속도 저하로 인한 수집 병목, 중복 데이터 저장으로 인한 저장소 낭비 |
| SUCCESS | API를 통해 들어온 뉴스가 JSONL에 올바르게 기록되고, 동일 뉴스 재전송 시 중복 저장되지 않음 |
| SCOPE | RawNewsRepository 인터페이스 및 JSONL 구현, IngestNewsUseCase 연동 |

## 1. Overview
`IngestNewsUseCase`가 호출될 때 `RawNewsItem`을 영구 저장소에 기록하도록 변경한다. 초기 저장소는 `docs/01-plan`의 전략에 따라 Append-only 방식의 JSONL을 사용한다.

## 2. Architecture Options

### Option A — Simple List Repository
- 단순히 수집된 순서대로 리스트에 추가하고 파일에 쓴다.
- **장점**: 구현이 가장 간단하다.
- **단점**: 중복 확인을 위해 파일 전체를 읽어야 하므로 성능상 불리하다.

### Option B — Indexed JSONL (Selected)
- `_find_latest_by_id`와 같은 인덱스 성격의 검색 기능을 활용하여 저장 전 중복 여부를 체크한다.
- **장점**: 멱등성을 보장하며, 기존 `JsonlSnapshotRepository` 패턴을 재사용하여 일관성을 유지한다.
- **단점**: 수집량이 수만 건 이상으로 늘어나면 파일 기반 검색의 성능 한계가 올 수 있다 (추후 DB 전환 필요).

## 3. Implementation Details

### 3.1 Data Contract & Ports
- `src/contracts/ports.py`에 `RawNewsRepository` 프로토콜 추가.
    - `save(item: RawNewsItem) -> None`
    - `get(raw_news_id: str) -> RawNewsItem | None`
    - `exists(raw_news_id: str) -> bool`

### 3.2 ID Generation Strategy
- `RawNewsItem.id`는 수집기에서 생성되어 들어오지만, 수집 레이어에서 `f"{source}:{source_id}"` 조합으로 다시 한번 검증하여 멱등성 있는 식별자로 활용한다.

### 3.3 Module Changes
- `src/db/repositories/jsonl.py`: `JsonlRawNewsRepository` 구현.
- `src/application/use_cases/ingest_news.py`: `RawNewsRepository` 의존성 주입 및 `execute` 로직 구현.
- `src/bootstrap/container.py`: 신규 컴포넌트 등록.

## 4. Session Guide
- `src/contracts/ports.py` 수정: `RawNewsRepository` 추가.
- `src/db/repositories/jsonl.py` 수정: `JsonlRawNewsRepository` 구현.
- `src/application/use_cases/ingest_news.py` 수정: 저장 로직 추가.
- `tests/test_news_ingestion.py` (또는 신규)를 통한 검증.
