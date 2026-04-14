# 예시 코드 부록

이 부록은 아키텍처 개념을 설명하기 위한 짧은 Python 3.11+ 예시를 제공한다. 운영 완성 코드가 아니라 구현 방향을 고정하기 위한 예시다.

## 1. 중립 Core Signal Model

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MarketSignal:
    market: str
    bias_hint: str
    impact_score: float
    confidence_score: float
    driver_themes: list[str]


@dataclass(frozen=True)
class ThemeSignal:
    theme: str
    sector: str
    momentum_score: float
    impact_score: float
    confidence_score: float


@dataclass(frozen=True)
class StockSignal:
    symbol: str
    themes: list[str]
    relevance_score: float
    sentiment_score: float
    impact_score: float
    confidence_score: float


@dataclass(frozen=True)
class TrendSnapshot:
    id: str
    as_of: datetime
    market_signals: list[MarketSignal]
    theme_signals: list[ThemeSignal]
    stock_signals: list[StockSignal]
    rules_version: str
```

## 2. Adapter Protocol

```python
from typing import Generic, Protocol, TypeVar

PayloadT = TypeVar("PayloadT")


class TrendAdapter(Protocol, Generic[PayloadT]):
    def convert(self, snapshot: TrendSnapshot) -> PayloadT:
        """Convert neutral TrendSnapshot into a consumer-specific payload."""
        ...
```

## 3. QTS Adapter 매핑 예시

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class QtsInputPayload:
    snapshot_id: str
    market_bias: str
    universe_adjustments: list[str]
    risk_overrides: list[str]


class QtsAdapter:
    def convert(self, snapshot: TrendSnapshot) -> QtsInputPayload:
        market = snapshot.market_signals[0]
        high_confidence_stocks = [
            signal.symbol
            for signal in snapshot.stock_signals
            if signal.confidence_score >= 0.65 and signal.impact_score >= 0.7
        ]
        risk_overrides = ["review_required"] if market.confidence_score < 0.6 else []
        return QtsInputPayload(
            snapshot_id=snapshot.id,
            market_bias=market.bias_hint,
            universe_adjustments=high_confidence_stocks,
            risk_overrides=risk_overrides,
        )
```

## 4. Workflow Adapter 매핑 예시

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowPayload:
    snapshot_id: str
    trigger_type: str
    priority: str
    recommended_actions: list[str]
    routing_conditions: dict[str, str]


class WorkflowAdapter:
    def convert(self, snapshot: TrendSnapshot) -> WorkflowPayload:
        urgent = [s for s in snapshot.stock_signals if s.impact_score >= 0.8]
        low_confidence = any(s.confidence_score < 0.6 for s in urgent)
        return WorkflowPayload(
            snapshot_id=snapshot.id,
            trigger_type="trend_snapshot_ready",
            priority="manual_review" if low_confidence else "normal",
            recommended_actions=["review_news_sources"] if low_confidence else ["publish_briefing"],
            routing_conditions={"target": "n8n", "confidence_gate": "required"},
        )
```

## 5. Use Case 계층 예시

```python
class AnalyzeDailyTrendsUseCase:
    def __init__(self, news_source, normalizer, scorer, aggregator, repository):
        self.news_source = news_source
        self.normalizer = normalizer
        self.scorer = scorer
        self.aggregator = aggregator
        self.repository = repository

    async def execute(self, as_of: datetime) -> TrendSnapshot:
        raw_items = await self.news_source.fetch_daily(as_of=as_of)
        normalized = [self.normalizer.normalize(item) for item in raw_items]
        evaluations = [self.scorer.evaluate(item) for item in normalized]
        snapshot = self.aggregator.aggregate(evaluations, as_of=as_of)
        await self.repository.save_snapshot(snapshot)
        return snapshot
```

UseCase는 API route나 batch runner가 Core/Adapter/Repository를 직접 조합하지 않도록 하는 경계다.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyzeDailyCommand:
    as_of: datetime
    requested_by: str
    correlation_id: str


class GenerateQtsPayloadUseCase:
    def __init__(self, snapshots, qts_adapter, payloads):
        self.snapshots = snapshots
        self.qts_adapter = qts_adapter
        self.payloads = payloads

    async def execute(self, snapshot_id: str, correlation_id: str) -> QtsInputPayload:
        snapshot = await self.snapshots.get(snapshot_id)
        payload = self.qts_adapter.convert(snapshot)
        await self.payloads.save_qts_payload(payload, correlation_id=correlation_id)
        return payload
```

## 5.1 계약 분리 예시

```python
from dataclasses import dataclass
from typing import Protocol


# src/contracts/core.py
@dataclass(frozen=True)
class CoreStockSignal:
    symbol: str
    impact_score: float
    confidence_score: float


# src/contracts/payloads.py
@dataclass(frozen=True)
class WorkflowTriggerPayload:
    trigger_type: str
    priority: str
    recommended_actions: list[str]


# src/contracts/ports.py
class SnapshotRepository(Protocol):
    async def get(self, snapshot_id: str) -> TrendSnapshot:
        ...
```

## 5.2 Workflow Payload와 Dispatch Runtime 분리 예시

```python
class WorkflowAdapter:
    def convert(self, snapshot: TrendSnapshot) -> WorkflowTriggerPayload:
        return WorkflowTriggerPayload(
            trigger_type="trend_snapshot_ready",
            priority="normal",
            recommended_actions=["publish_briefing"],
        )


class N8nDispatchGateway:
    def __init__(self, http_client):
        self.http_client = http_client

    async def dispatch(self, payload: WorkflowTriggerPayload, correlation_id: str) -> str:
        response = await self.http_client.post(
            "/webhook/trends",
            json={"payload": payload, "correlation_id": correlation_id},
        )
        return response.headers["X-Dispatch-Id"]
```

## 6. FastAPI Route 예시

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1")


@router.post("/analyze/daily")
async def analyze_daily(
    use_case: AnalyzeDailyTrendsUseCase = Depends(),
    _: None = Depends(assert_heavy_job_allowed_dependency),
):
    snapshot = await use_case.execute(as_of=current_kst_time())
    return {"snapshot_id": snapshot.id, "status": "created"}
```

## 6.1 Error Response Model 예시

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorBody:
    code: str
    message: str
    details: dict[str, str]


@dataclass(frozen=True)
class ErrorResponse:
    error: ErrorBody
    correlation_id: str
```

## 7. 스케줄링 정책 예시

```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


def is_korean_market_hours(now: datetime) -> bool:
    local_now = now.astimezone(KST)
    return MARKET_OPEN <= local_now.time() <= MARKET_CLOSE


def assert_heavy_job_allowed(now: datetime, job_type: str) -> None:
    if is_korean_market_hours(now):
        raise RuntimeError(f"{job_type} is blocked during KST market hours")
```

Batch runner에서는 guard를 UseCase 실행 직전에 적용한다.

```python
async def run_daily_job(use_case: AnalyzeDailyTrendsUseCase, command: AnalyzeDailyCommand) -> TrendSnapshot:
    assert_heavy_job_allowed(command.as_of, job_type="daily")
    return await use_case.execute(as_of=command.as_of)
```

## 7.1 Job / Correlation ID 구조 예시

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationContext:
    correlation_id: str
    job_id: str | None
    requested_by: str


def build_job_id(date_key: str, job_type: str, sequence: int) -> str:
    return f"job_{date_key}_{job_type}_{sequence:03d}"
```

## 8. Runtime Mode Enum 예시

```python
from enum import StrEnum


class RuntimeMode(StrEnum):
    DAILY = "daily"
    INCREMENTAL = "incremental"
    REBUILD = "rebuild"
    API_READONLY = "api_readonly"
    WEBHOOK_INBOUND = "webhook_inbound"
    WORKFLOW_DISPATCH = "workflow_dispatch"
```
