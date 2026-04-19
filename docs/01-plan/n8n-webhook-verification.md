# PDCA Plan: n8n Webhook Verification (n8n-webhook-verification)

## 1. 개요 (Abstract)

`api_spec.md` 명세에 따라 n8n에서 유입되는 인바운드 웹훅(`POST /api/v1/ingest/webhook/n8n`)에 대한 보안 검증 로직을 구현한다. Shared Secret 헤더 검증 또는 HMAC 서명 검증을 통해 허가되지 않은 요청으로부터 뉴스 수집 엔드포인트를 보호한다.

## 2. 가치 제안 (Value Proposition)

- **보안 강화**: 외부로 노출된 수집 엔드포인트에 대한 인증 체계를 구축하여 악의적인 데이터 주입 공격(Data Poisoning)을 방지한다.
- **신뢰도 확보**: 검증된 소스(n8n)로부터 온 데이터만 수집함으로써, `NewsEvaluation` 단계에서의 `source_tier` 판별에 신뢰를 더한다.
- **운영 안정성**: 비정상적인 대량 요청을 사전에 차단하여 분석 서버의 리소스를 보호한다.

## 3. 기능 범위 (Scope)

### 3.1 Security Dependency 구현
- [ ] `src/api/dependencies.py`: `verify_n8n_signature` 함수 추가.
    - [ ] `X-N8N-Signature` 또는 `X-Shared-Secret` 헤더 처리 로직.
    - [ ] 환경 변수에 저장된 Secret과 비교 검증.

### 3.2 Error Handling
- [ ] 검증 실패 시 `401 Unauthorized` 또는 `403 Forbidden` 응답과 함께 표준 에러 코드(`WEBHOOK_SIGNATURE_INVALID`) 반환.

### 3.3 API Route 적용
- [ ] `src/api/routes/ingest.py`: `ingest_n8n_webhook` 엔드포인트에 검증 의존성(`Depends`) 주입.

## 4. 구현 전략 (Implementation Strategy)

1.  **Shared Secret First**: 초기에는 단순하고 강력한 Shared Secret 방식을 우선 적용하고, 필요 시 HMAC 기반의 페이로드 서명 검증으로 확장한다.
2.  **Environment Configuration**: Secret 값은 `.env` 및 `Settings` 클래스를 통해 안전하게 관리한다.
3.  **Logging**: 검증 실패 사례를 `correlation_id`와 함께 상세 로깅하여 이상 징후를 모니터링한다.

## 5. 검증 계획 (Verification Plan)

- **Security Test**:
    - [ ] 올바른 Secret을 포함한 요청이 정상적으로 `200 OK`를 받는지 확인.
    - [ ] 잘못된 Secret이나 헤더가 없는 요청이 `401/403` 에러로 차단되는지 확인.
