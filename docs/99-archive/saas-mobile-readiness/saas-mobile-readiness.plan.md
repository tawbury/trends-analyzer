# [Plan] SaaS and Mobile App Readiness Enhancement (Login-less Model)

## Executive Summary
This feature aims to transform the current local-first `trends-analyzer` into a SaaS-ready backend supporting multi-tenant web and Android applications, starting with a **login-less public access model**. The focus shifts from user authentication to robust device-based identification, public API stability, and operational safety.

### Value Delivered
| Problem | Solution | Function UX Effect | Core Value |
|---------|----------|-------------------|------------|
| Local-only Access | Public REST API Deployment | Users access trends without app install | Accessibility & Viral Growth |
| No Identification | Device-based (UUID) tracking | Personalized settings without login | Frictionless UX |
| Resource Abuse | Global & IP-based Rate Limiting | System stays stable for all users | Service Continuity |
| Manual Operations | Automated Guards & Monitoring | Stable performance during market hours | System Trust |

## Context Anchor
| Dimension | Content |
|-----------|---------|
| WHY | Establish a scalable backend for public mobile/web access without login friction |
| WHO | Casual trend followers and early adopters |
| RISK | 1. API scraping/abuse, 2. Backend saturation, 3. Anonymous data collision |
| SUCCESS | 1. Stable public API, 2. Device-based rate limiting, 3. Market hours guard active |
| SCOPE | API Publicizing, Device tracking, Rate limiting, Operational guards |

## 1. Requirements

### 1.1 Functional Requirements
- **Anonymous Identification**: Support `X-Device-ID` header for tracking anonymous preferences.
- **Data Access**: Public read-only access to trends and signals.
- **Database Migration**: Move to PostgreSQL for concurrent public access handling.
- **Mobile Hook**: Anonymous FCM token registration for push notifications.
- **Rate Limiting**: Tiered limiting based on IP and Device ID.

### 1.2 Non-Functional Requirements
- **Security**: Prevent data scraping via aggressive rate limiting and WAF rules.
- **Scalability**: Handle up to 1,000 concurrent anonymous users.
- **Market Protection**: Heavy tasks (batch ingestion) strictly blocked during KST market hours.

## 2. Risk Assessment & Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|----------------------|
| API Scraping | High | Implement Redis-based rate limiting and Cloudflare WAF. |
| Data Collision | Low | Use UUID v4 for Device IDs with validation middleware. |
| Infrastructure Cost | Medium | Implement caching (CDN/Redis) for high-traffic trend endpoints. |
| Market Interference | High | Global FastAPI middleware for `MarketHoursGuard`. |

## 3. Scope & Schedule

### 3.1 In-Scope
- Implementation of `DeviceID` middleware in FastAPI.
- Refactoring `src/db/repositories/` for PostgreSQL and public read access.
- Adding `/api/v1/notifications/tokens/anonymous` endpoint.
- Global `MarketHoursGuard` implementation.

### 3.2 Out-of-Scope
- User signup/login (deferred to Phase 2).
- User-specific private trend creation.
- Complex payment integration.

## 4. Success Criteria
- [ ] API successfully responds to requests with `X-Device-ID`.
- [ ] Rate limiting kicks in after exceeding threshold (e.g., 60 req/min).
- [ ] Database handles concurrent public reads without performance lag.
- [ ] Push notifications sent successfully to anonymous device tokens.
