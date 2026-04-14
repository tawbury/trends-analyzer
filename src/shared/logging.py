from __future__ import annotations

import logging

from src.contracts.runtime import CorrelationContext


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def correlation_fields(correlation: CorrelationContext) -> dict[str, str]:
    return {
        "correlation_id": correlation.correlation_id,
        "job_id": correlation.job_id,
        "requested_by": correlation.requested_by,
    }


def log_with_context(logger: logging.Logger, message: str, correlation: CorrelationContext) -> None:
    fields = correlation_fields(correlation)
    logger.info(
        "%s correlation_id=%s job_id=%s requested_by=%s",
        message,
        fields["correlation_id"],
        fields["job_id"],
        fields["requested_by"],
        extra=fields,
    )
