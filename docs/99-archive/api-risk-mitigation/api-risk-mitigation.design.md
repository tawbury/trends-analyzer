# [Design] API Security and Redistribution Risk Mitigation

## Context Anchor
| Dimension | Content |
|-----------|---------|
| WHY | Prevent security breaches and legal issues when using sensitive brokerage APIs in a public app |
| WHO | Developers, Security Auditors, and App Users |
| RISK | 1. Credential theft, 2. Legal lawsuits for redistribution, 3. Sudden API service termination |
| SUCCESS | 1. Zero internal keys in client code, 2. Successful request caching, 3. 429 errors minimized |
| SCOPE | BFF Proxy implementation, Secret management, Data filtering, Caching logic |

## 1. Overview
This design implements a secure **Backend-for-Frontend (BFF)** layer to mitigate risks associated with third-party financial APIs. It shields internal keys, manages rate limits via caching, and ensures data compliance through filtering.

## 2. Selected Architecture: Option B (Adapter Pattern)
- **Pattern**: Abstract Brokerage Interface + Provider-specific Adapters.
- **Location**: `src/adapters/` for logic, `src/shared/config.py` for secrets.
- **Caching**: Memory-based caching (expandable to Redis) in the adapter layer.
- **Key Injection**: Centralized in the adapter, never exposed to the API layer or clients.

## 3. Detailed Design

### 3.1 Interface Definition
```python
class BrokerageAdapter(Protocol):
    async def get_market_data(self, symbol: str) -> MarketData: ...
    async def get_signals(self, symbol: str) -> list[Signal]: ...
```

### 3.2 Implementation Strategy
- **BaseAdapter**: Handles common caching and rate-limiting logic.
- **SpecificAdapters** (e.g., Naver, QTS): Implement the actual HTTP calls using keys from `Settings`.
- **Filtering**: Each adapter must implement a `sanitize_response` method to strip sensitive fields.

### 3.3 Security & Secret Management
- **Environment Variables**: All API keys stored in `.env` (not committed).
- **Settings Object**: `src/shared/config.py` reads from `.env` and provides typed access.
- **No Client Keys**: The frontend receives data from `/api/v1/...` which already has keys injected server-side.

## 4. Session Guide
- **Phase 1**: Update `src/shared/config.py` to include third-party API keys.
- **Phase 2**: Create `src/adapters/base.py` for the interface and caching.
- **Phase 3**: Refactor `src/adapters/qts/adapter.py` and `src/adapters/generic/adapter.py` to follow the new pattern.
- **Phase 4**: Implement response sanitization in each adapter.

## 5. Security Considerations
- **Log Masking**: Ensure API keys are never printed to logs during request/response debugging.
- **Cache TTL**: Balance data freshness with rate-limit safety (default 10s for price data).
