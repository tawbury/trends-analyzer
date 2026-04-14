from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyzeDailyResponse:
    snapshot_id: str
    qts_payload_id: str
    job_id: str
    correlation_id: str
    status: str


@dataclass(frozen=True)
class ErrorBody:
    code: str
    message: str
    details: dict[str, str]


@dataclass(frozen=True)
class ErrorResponse:
    error: ErrorBody
    correlation_id: str
