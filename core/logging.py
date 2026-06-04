"""Project logging helpers."""

from __future__ import annotations

import logging
import sys
from typing import TextIO


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logger(
    name: str = "tm_trading_v555",
    *,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Return an idempotently configured project logger."""

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    return logger
