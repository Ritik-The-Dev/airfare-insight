from __future__ import annotations

import logging
import sys

from app.models.config import settings


def get_logger(name: str = "farelens") -> logging.Logger:
    """Return a configured logger for FareLens."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  %(levelname)-8s  %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger


def log_scraper_success(
    logger: logging.Logger,
    search_id: str,
    source: str,
    duration: float,
    count: int,
) -> None:
    """Emit: [search {id}] {source} completed in {t:.1f}s — {n} results"""
    logger.info("[search %s] %s completed in %.1fs — %d results", search_id, source, duration, count)


def log_scraper_failure(
    logger: logging.Logger,
    search_id: str,
    source: str,
    status: str,
    duration: float,
    error: str = "",
) -> None:
    """Emit: [search {id}] {source} {status} after {t:.1f}s"""
    msg = "[search %s] %s %s after %.1fs"
    args: tuple = (search_id, source, status, duration)
    if error:
        msg += " — %s"
        args = (*args, error)
    logger.warning(msg, *args)
