from __future__ import annotations

from datetime import datetime, time

from src.shared.clock import KST

MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


class MarketHoursBlockedError(RuntimeError):
    def __init__(self, job_type: str) -> None:
        super().__init__(f"{job_type} is blocked during KST market hours")
        self.job_type = job_type
        self.blocked_window = "09:00-15:30 KST"


def is_korean_market_hours(now: datetime) -> bool:
    local_now = now.astimezone(KST)
    return MARKET_OPEN <= local_now.time() <= MARKET_CLOSE


def assert_heavy_job_allowed(now: datetime, job_type: str) -> None:
    if is_korean_market_hours(now):
        raise MarketHoursBlockedError(job_type=job_type)
