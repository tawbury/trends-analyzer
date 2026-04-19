# [Design] SaaS and Mobile App Readiness Enhancement (Login-less Model)

## Context Anchor
| Dimension | Content |
|-----------|---------|
| WHY | Establish a scalable backend for public mobile/web access without login friction |
| WHO | Casual trend followers and early adopters |
| RISK | 1. API scraping/abuse, 2. Backend saturation, 3. Anonymous data collision |
| SUCCESS | 1. Stable public API, 2. Device-based rate limiting, 3. Market hours guard active |
| SCOPE | API Publicizing, Device tracking, Rate limiting, Operational guards |

## 1. Overview
This design implements a pragmatic, login-less SaaS backend. It uses **Device-ID identification** via HTTP headers, **PostgreSQL** for persistence, and a **Global Middleware** for operational guards (Rate Limiting & Market Hours).

## 2. Selected Architecture: Option C (Pragmatic Balance)
- **Identification**: `X-Device-ID` (UUID v4) extracted in middleware.
- **Persistence**: PostgreSQL for device settings and history.
- **Guard Layer**: Global FastAPI Middleware for `MarketHoursGuard` and `RateLimit`.
- **API Strategy**: RESTful endpoints with standardized JSON responses.

## 3. Detailed Design

### 3.1 Data Model (PostgreSQL)
```sql
CREATE TABLE anonymous_devices (
    device_id UUID PRIMARY KEY,
    fcm_token TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    settings JSONB DEFAULT '{}'
);

CREATE TABLE anonymous_interactions (
    id SERIAL PRIMARY KEY,
    device_id UUID REFERENCES anonymous_devices(device_id),
    endpoint TEXT,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Middleware Design
- **DeviceIDMiddleware**: Ensures `X-Device-ID` is present. If not, rejects with 400 or generates a temporary one for the session.
- **MarketHoursGuardMiddleware**: Checks `src/shared/market_hours.py`. If `is_korean_market_hours()` is true and request is "heavy" (POST/PUT/DELETE), returns 403.
- **RateLimitMiddleware**: Uses an in-memory or Redis-based counter to limit requests per `X-Device-ID`.

### 3.3 API Endpoints
- `GET /api/v1/trends`: Public access to trends.
- `POST /api/v1/notifications/tokens/anonymous`: Register `fcm_token` for a `device_id`.
- `GET /api/v1/ops/health`: Public health check.

## 4. Session Guide
- **Phase 1**: Implement `src/shared/middlewares.py` with `DeviceIDMiddleware` and `MarketHoursMiddleware`.
- **Phase 2**: Refactor `src/db/repositories/` to use a generic SQL repository (simulated for now with `Jsonl` sharding if SQL is not yet setup, but targeting SQL structure).
- **Phase 3**: Update `src/api/app.py` to register middlewares.
- **Phase 4**: Add the notification token endpoint.

## 5. Security Considerations
- **Rate Limiting**: Essential to prevent scraping.
- **Input Validation**: Strict UUID validation for `X-Device-ID`.
- **Market Hours**: Ensuring no batch jobs are triggered via public API during market hours.
