# [Plan] API Security and Redistribution Risk Mitigation

## Executive Summary
This feature addresses the critical security and legal risks associated with using third-party brokerage/financial APIs in a distributed mobile application. We will implement a **Backend-for-Frontend (BFF)** proxy layer to shield internal API keys, consolidate requests to manage rate limits, and ensure compliance with data redistribution licenses.

### Value Delivered
| Problem | Solution | Function UX Effect | Core Value |
|---------|----------|-------------------|------------|
| API Key Exposure | Implement BFF Proxy Layer | Internal keys are never sent to clients | Security & Fraud Prevention |
| Rate Limit Exhaustion | Request Caching & Consolidation | App remains responsive under high load | Service Stability |
| License Violation | Data Transformation & Filtering | Only processed/allowed data is redistributed | Legal Compliance |
| Direct API Dependency | API Abstraction Layer | Easier to switch providers in the future | Technical Agility |

## Context Anchor
| Dimension | Content |
|-----------|---------|
| WHY | Prevent security breaches and legal issues when using sensitive brokerage APIs in a public app |
| WHO | Developers, Security Auditors, and App Users |
| RISK | 1. Credential theft, 2. Legal lawsuits for redistribution, 3. Sudden API service termination |
| SUCCESS | 1. Zero internal keys in client code, 2. Successful request caching, 3. 429 errors minimized |
| SCOPE | BFF Proxy implementation, Secret management, Data filtering, Caching logic |

## 1. Requirements

### 1.1 Functional Requirements
- **API Masking**: The Android/Web client must only communicate with `trends-analyzer` endpoints, never directly with brokerage APIs.
- **Secret Management**: Store all brokerage API keys in server-side environment variables or a Secret Manager.
- **Response Caching**: Implement short-term caching (e.g., 5-30 seconds) for common data requests to reduce upstream API calls.
- **Data Sanitization**: Strip sensitive metadata from upstream API responses before passing them to the client.

### 1.2 Non-Functional Requirements
- **Latency**: BFF proxy overhead should be < 50ms.
- **Security**: Mandatory use of HTTPS for all client-to-BFF communication.
- **Observability**: Log all upstream API call durations and status codes for monitoring.

## 2. Risk Assessment & Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|----------------------|
| BFF Bottleneck | Medium | Implement horizontal scaling for the API layer and efficient caching. |
| Stale Data | Low | Use TTL-based caching and provide a "Last Updated" timestamp to the user. |
| Proxy Bypass | High | Ensure no brokerage API endpoints are accessible via public internet except through the BFF. |
| Legal Audit | High | Maintain logs of what data is redistributed to prove compliance if audited. |

## 3. Scope & Schedule

### 3.1 In-Scope
- Creating an `Adapter` layer for Brokerage APIs in `src/adapters/`.
- Implementing a Caching middleware in the FastAPI application.
- Secure environment variable configuration.
- Unit tests for the Proxy/BFF logic.

### 3.2 Out-of-Scope
- Implementing multiple brokerage providers (focus on the primary one first).
- Complex real-time streaming (WebSocket) proxying (deferred).

## 4. Success Criteria
- [ ] Automated scan confirms no API keys are present in the client-side build artifacts.
- [ ] Upstream API rate limit remains healthy even with multiple concurrent client simulations.
- [ ] Legal review confirms the data redistribution model is compliant with the API provider's TOS.
