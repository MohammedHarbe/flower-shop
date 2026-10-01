"""Log failure locations without exception messages, SQL values or customer data."""

import logging
from pathlib import Path


def log_failure(logger: logging.Logger, message: str, error: Exception) -> None:
    # Exception strings (including driver/SMTP errors) can contain credentials
    # or customer data. Keep the error type and final code location only.
    trace = error.__traceback__
    while trace is not None and trace.tb_next is not None:
        trace = trace.tb_next
    location = (
        f"{Path(trace.tb_frame.f_code.co_filename).name}:{trace.tb_lineno}"
        if trace is not None else "unknown"
    )
    logger.error("%s (error_type=%s, location=%s)", message, type(error).__name__, location)
