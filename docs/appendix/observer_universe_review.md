# Observer Universe 코드 검토 노트

## 1. 문서 메타데이터

- 문서 유형: 비권위 구현 검토 노트
- 상태: Draft v0.1
- 권위 범위: Observer universe 코드 분석과 trends-analyzer symbol catalog 방향 결정 근거
- 상위 문서: `../architecture/module_design.md`, `../architecture/environment_config.md`
- 관련 문서: `source_extension_notes.md`, `../meta/implementation_traceability.md`
- 최종 수정일: 2026-04-15

## 2. 검토 대상

로컬 경로 `/home/tawbu/projects/observer`에서 다음 파일을 검토했다.

| 파일 | 역할 |
|------|------|
| `src/universe/symbol_api.py` | KIS API, KIS master file, local backup, emergency fallback 기반 4-step symbol collection |
| `src/universe/symbol_generator.py` | symbol artifact 생성, 상태 파일, health 파일, backup/cache 저장 |
| `src/universe/universe_manager.py` | QTS/Observer용 daily universe snapshot 생성 |
| `src/universe/universe_scheduler.py` | AM/PM universe generation scheduler |
| `src/provider/kis/kis_rest_provider.py` | KRX/CSV/cache 기반 symbol list 수집 구현 |
| `scripts/dev/collect_stock_symbols.py` | pykrx 기반 전체 상장 종목 수집 개발 스크립트 |

## 3. 핵심 발견

Observer는 두 단계가 분리되어 있다.

1. `SymbolGenerator`: 전체 symbol 후보를 수집해 `data/symbols/{YYYYMMDD}_kr_stocks.json` 형태로 저장한다.
2. `UniverseManager`: symbol 후보에 가격 필터를 적용해 `data/universe/{YYYYMMDD}_kr_stocks.json` snapshot을 만든다.

가격 필터는 `src/universe/universe_manager.py`에 있다.

```python
if close is not None and close >= self.min_price:
    selected.append(sym)
```

기본값은 다음과 같다.

```python
min_price: int = 4000
```

이 필터는 QTS 매매 유니버스에는 적절할 수 있으나 뉴스/트렌드 분석용 symbol catalog에는 부적절하다. 저가주, 관리종목, 우선주, 신규 상장 종목이 뉴스에는 중요할 수 있기 때문이다.

## 4. 재사용 판단

직접 import 재사용은 권장하지 않는다.

- Observer path resolver와 runtime directory 정책에 결합되어 있다.
- scheduler, health file, backup/cache, log directory 정책이 함께 들어 있다.
- `UniverseManager`는 4000원 가격 필터와 `min_count` 등 QTS 유니버스 정책을 포함한다.
- provider engine interface가 Observer 내부 구조에 묶여 있다.

재사용 가능한 것은 아이디어와 artifact shape다.

- KIS stock master 파일을 symbol source로 사용하는 방식
- JSON artifact shape: `metadata`, `symbols`
- fallback source 전략
- snapshot/latest artifact 저장 방식

## 5. trends-analyzer 결정

trends-analyzer는 독립 symbol catalog를 소유한다.

- 기본 source: KIS official stock master MST ZIP
- 임시 bridge: Observer symbol artifact JSON 읽기
- 사용하지 않을 것: Observer filtered universe artifact를 영구 source로 사용
- 제거할 것: 전일종가 4000원 미만 제외 필터

`data/universe` artifact는 QTS 매매 정책이 섞인 filtered universe이므로 trends-analyzer의 full catalog source로 쓰면 안 된다. 필요하면 `data/symbols` artifact만 임시 bridge로 사용한다.
