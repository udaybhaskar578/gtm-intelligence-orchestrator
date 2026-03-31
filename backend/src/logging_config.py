from __future__ import annotations

import logging
from typing import Optional


class DefaultRunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s [run_id=%(run_id)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(DefaultRunIdFilter())

    root.setLevel(level.upper())
    root.addHandler(handler)


def get_logger(name: str, run_id: Optional[str] = None) -> logging.LoggerAdapter:
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {"run_id": run_id or "-"})
