# PDCA Plan: Symbol Catalog Refinement (symbol-catalog-refinement)

## 1. 개요 (Abstract)

종목 카탈로그(`SymbolCatalog`)의 데이터 품질을 고도화하고, 뉴스 검색(Discovery)에 최적화된 심볼 정보를 구축한다. 현재의 단순한 종목명 정규화와 분류 로직을 확장하여 다양한 증권 종류(ETF, ETN, 리츠, 스팩, 우선주 등)를 정확히 판별하고, 검색 노이즈를 줄이면서도 누락 없는 뉴스 수집이 가능하도록 별칭(Alias)과 검색어(Query Keyword) 생성 로직을 개선한다.

## 2. 가치 제안 (Value Proposition)

- **검색 정확도 향상**: 종목명 외에도 약어, 영문명, 시장 구분 등을 활용한 정교한 검색어 생성으로 관련 뉴스 수집율을 높인다.
- **노이즈 필터링**: 일반 주식과 성격이 다른 ETF, ETN 등을 명확히 분류하여 분석 목적에 맞는 종목군만 선별할 수 있게 한다.
- **데이터 무결성**: 더욱 강화된 유효성 검사(Validation)를 통해 잘못된 종목 코드나 이름이 분석 파이프라인에 진입하는 것을 방지한다.

## 3. 기능 범위 (Scope)

### 3.1 Contract 보완
- [ ] `src/contracts/symbols.py`: `SymbolRecord`에 `classification`과 `sector` 필드를 명시적 필드로 승격 또는 metadata 활용 가이드 확립.

### 3.2 분류(Classification) 로직 고도화
- [ ] `src/ingestion/catalog/normalization.py`: `classify_symbol` 함수 확장.
    - [ ] 인프라 펀드, 선박 투자회사 등 특수 형태 종목 추가 분류.
    - [ ] 섹터 정보(KOSPI/KOSDAQ 업종 코드) 연동 기반 마련.

### 3.3 별칭(Alias) 및 검색어(Query Keyword) 생성 개선
- [ ] `build_aliases` 및 `build_query_keywords` 로직 강화.
    - [ ] 지주사(홀딩스), 우선주(우, 우B 등)의 다양한 표기법 대응.
    - [ ] 공통 접두어/접미어 제거를 통한 핵심 키워드 추출.
    - [ ] 영문명이 가용한 경우 영문 별칭 추가.

### 3.4 유효성 검사(Validation) 강화
- [ ] `src/ingestion/catalog/validation.py`: `validate_symbol_catalog` 확장.
    - [ ] 업종 정보 누락 검사.
    - [ ] 비정상적으로 짧거나 긴 종목명 검사.
    - [ ] 시장 구분과 종목 코드 체계의 일치 여부 확인.

## 4. 구현 전략 (Implementation Strategy)

1.  **Normalization Refactoring**: `normalization.py` 내의 정규식과 마커 리스트를 최신 시장 데이터에 맞춰 업데이트한다.
2.  **Rich Metadata Extraction**: KIS 마스터 파일 등 소스 데이터에서 더 많은 속성(업종, 영문명)을 추출하여 `SymbolRecord`를 풍부하게 만든다.
3.  **Heuristic Alias Generation**: 종목명 패턴 분석을 통해 사람이 검색할 법한 다양한 변이형(Variation)을 자동 생성하는 규칙을 추가한다.
4.  **Reporting**: 유효성 검사 결과 리포트를 더 상세화하여 데이터 품질 이슈를 시각화한다.

## 5. 검증 계획 (Verification Plan)

- **Unit Test**: 다양한 종목명(예: "삼성전자우", "TIGER 차이나전기차SOLACTIVE", "맥쿼리인프라")에 대해 올바른 `classification`, `aliases`, `query_keywords`가 생성되는지 확인.
- **Data Quality Report**: 전체 KOSPI/KOSDAQ 종목 대상 validation 실행 후 비정상 레코드 수 감소 확인.
- **Discovery Trace**: 생성된 검색어로 실제 뉴스 검색 API 호출 시 관련성 높은 결과가 반환되는지 샘플링 검증.

## 6. 일정 및 우선순위 (Timeline & Priority)

1.  **P0 (Critical)**: `classification` 로직 확장 및 `aliases` 생성 규칙 강화.
2.  **P1 (High)**: KIS 마스터 파일에서 영문명 및 섹터 정보 추가 추출.
3.  **P2 (Normal)**: 유효성 검사 상세 리포팅 및 노이즈 필터링 고도화.
