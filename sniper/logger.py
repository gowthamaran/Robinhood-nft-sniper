from __future__ import annotations

import logging
from pathlib import Path

from sniper.config import app_home, ensure_layout
from sniper.security.redaction import RedactingFilter


def configure_logging(verbose: bool = False, root: Path | None = None) -> logging.Logger:
    root = ensure_layout(root or app_home())
    logger = logging.getLogger("robinhood_sniper")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    redactor = RedactingFilter()

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    stream.addFilter(redactor)
    logger.addHandler(stream)

    file_handler = logging.FileHandler(root / "logs" / "sniper.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redactor)
    logger.addHandler(file_handler)
    return logger
