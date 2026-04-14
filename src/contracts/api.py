from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeDailyResponse(BaseModel):
    snapshot_id: str
    qts_payload_id: str
    job_id: str
    correlation_id: str
    status: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
    correlation_id: str
