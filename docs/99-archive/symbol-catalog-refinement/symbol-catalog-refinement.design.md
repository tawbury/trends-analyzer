# PDCA Design: Symbol Catalog Refinement (symbol-catalog-refinement)

## 1. 개요 (Abstract)
본 설계 문서는 `symbol-catalog-refinement` 계획에 명시된 종목 분류 고도화, 별칭 및 검색어 생성 로직 개선, 그리고 유효성 검사 강화에 대한 상세 기술 명세를 정의합니다.

## 2. 기술 명세 (Technical Specification)

### 2.1 분류 마커 확장 (`src/ingestion/catalog/normalization.py`)
기존 마커 외에 특수 종목 판별을 위한 마커를 추가합니다.

| 분류 (Classification) | 추가 마커 / 정규식 |
| :--- | :--- |
| `infra` | `맥쿼리인프라`, `맵스인프라` 등 "인프라" 포함 |
| `ship` | `바다로선박`, `하이골드` 등 선박 투자 회사 패턴 |
| `preferred_stock` | `(\d*우[A-C]?$|우선주$|전환우선주$|상환우선주$)` |
| `holding_company` | `홀딩스`, `지주` 포함 여부 (별도 플래그 활용) |

### 2.2 별칭 및 검색어 생성 로직 개선
*   **`build_aliases`**:
    *   `홀딩스` -> `지주` (상호 치환 별칭 생성)
    *   `㈜`, `(주)` 제거는 기본, 영문명이 포함된 경우 괄호 제거 후 별칭 추가.
*   **`build_query_keywords`**:
    *   우선주의 경우 `[본주명] 우선주` 외에 `[본주명] 주가` 등 검색 노이즈가 적은 키워드 조합 추가.
    *   ETF/ETN의 경우 종목명에서 운용사(TIGER, KODEX 등)를 제외한 핵심 테마명 추출 시도.

### 2.3 유효성 검사 확장 (`src/ingestion/catalog/validation.py`)
*   **`validate_symbol_catalog`**:
    *   종목명의 길이가 2자 미만인 경우 `suspicious_name` 경고.
    *   종목 코드와 시장 정보의 불일치(예: KOSPI는 '0'으로 시작하지 않는 6자리 등, 단 우선주는 예외) 검사.
    *   `metadata` 내 `sector` 정보가 없는 경우 `missing_sector` 경고.

## 3. 구현 계획 (Implementation Plan)

### 3.1 Contract 수정 (`src/contracts/symbols.py`)
`SymbolRecord`에 `sector` 필드를 추가하거나, `metadata` 내의 표준 키(`sector`, `industry`, `english_name`) 사용을 규정합니다.

### 3.2 Normalization 업데이트
`classify_symbol`, `build_aliases`, `build_query_keywords` 함수를 위 명세에 맞춰 리팩토링합니다.

### 3.3 Validation 업데이트
`_record_issues` 함수에 신규 체크 로직을 추가합니다.

## 4. 테스트 전략 (Test Strategy)
*   **정교한 케이스 검증**:
    *   "LG화학우" -> `preferred_stock` 분류, 별칭에 "LG화학" 포함 여부 확인.
    *   "SK이노베이션홀딩스" -> 별칭에 "SK이노베이션지주" 생성 확인.
    *   "TIGER 미국나스닥100" -> 검색어에 "미국나스닥100" 포함 확인.
