from __future__ import annotations

import logging

from src.contracts.runtime import CorrelationContext


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_with_context(logger: logging.Logger, message: str, correlation: CorrelationContext) -> None:
    logger.info(
        "%s correlation_id=%s job_id=%s requested_by=%s",
        message,
        correlation.correlation_id,
        correlation.job_id,
        correlation.requested_by,
    )
