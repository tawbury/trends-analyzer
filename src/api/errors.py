from __future__ import annotations

from typing import Any, NoReturn

from fastapi import Request
from fastapi.responses import JSONResponse

from src.contracts.api import ErrorBody, ErrorResponse


def model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class ApiError(Exception):
    def __init__(self, *, status_code: int, response: ErrorResponse) -> None:
        self.status_code = status_code
        self.response = response


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=model_to_dict(exc.response),
    )


def raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: dict[str, str] | None = None,
) -> NoReturn:
    response = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
        correlation_id=correlation_id,
    )
    raise ApiError(status_code=status_code, response=response)
