# PDCA Design: n8n Webhook Verification (n8n-webhook-verification)

> v1.0.0 | PDCA Design Phase

## Context Anchor

| Dimension | Content |
|-----------|---------|
| WHY | 외부 노출된 수집 엔드포인트 보안을 강화하고 n8n으로부터의 데이터 신뢰성을 보장 |
| WHO | 시스템 관리자 및 n8n 워크플로우 개발자 |
| RISK | Secret 유출 시 허가되지 않은 데이터 주입 가능, 잘못된 설정으로 인한 정상 수집 차단 |
| SUCCESS | 유효한 헤더가 포함된 요청만 200 OK를 반환하고, 그 외에는 401/403 에러로 차단됨 |
| SCOPE | n8n 전용 웹훅 보안 디펜던시 구현 및 엔드포인트 적용 |

## 1. Overview
n8n에서 발송하는 `POST /api/v1/ingest/webhook/n8n` 요청에 대해 `X-N8N-Secret` 헤더를 검증하는 로직을 추가한다. 이는 `Shared Secret` 방식으로, 서버 환경 변수에 저장된 값과 요청 헤더 값을 비교한다.

## 2. Architecture Options

### Option A — Simple Header Check (Selected)
- FastAPI의 `Header` 디펜던시를 사용하여 특정 헤더 값을 서버의 `Settings` 값과 직접 비교한다.
- **장점**: 구현이 가장 간단하고 성능 부하가 거의 없다. n8n 워크플로우 설정도 용이하다.
- **단점**: 헤더 기반이므로 중간에 가로채질 위험이 있으나, HTTPS 환경에서는 충분히 안전하다.

### Option B — HMAC Signature Verification
- 페이로드 전체를 Secret 키로 해싱하여 서명을 만들고 이를 검증한다.
- **장점**: 데이터 위변조 방지까지 가능하다.
- **단점**: n8n 워크플로우에서 HMAC 생성 노드를 추가해야 하므로 설정 복잡도가 증가한다.

## 3. Implementation Details

### 3.1 Configuration (`src/shared/config.py`)
- `n8n_webhook_secret: str | None = None` 필드 추가.

### 3.2 Dependency (`src/api/dependencies.py`)
- `verify_n8n_token(x_n8n_secret: str = Header(..., alias="X-N8N-Secret"))` 함수 구현.
- `Settings.n8n_webhook_secret`이 설정되어 있지 않으면 경고를 남기고 통과(개발 편의성), 설정되어 있다면 반드시 일치해야 함.

### 3.3 Error Handling
- 검증 실패 시 `HTTPException(status_code=401, detail={"error": {"code": "WEBHOOK_AUTH_FAILED", ...}})` 반환.

### 3.4 Route 적용 (`src/api/routes/ingest.py`)
- `ingest_n8n_webhook` 엔드포인트의 `Depends` 리스트에 `verify_n8n_token` 추가.

## 4. Session Guide
- `src/shared/config.py` 수정: `n8n_webhook_secret` 추가.
- `src/api/dependencies.py` 수정: `verify_n8n_token` 구현.
- `src/api/routes/ingest.py` 수정: 엔드포인트에 적용.
- `tests/test_n8n_webhook_verification.py`를 통한 보안 테스트.
