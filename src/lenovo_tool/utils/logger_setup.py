"""Structured logging setup for the application."""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", fmt: str | None = None, log_file: str | None = None) -> None:
    """Configure root logger for the application.

    Args:
        level: log level string (DEBUG, INFO, WARNING, ERROR)
        fmt: log format string
        log_file: optional path to log file
    """
    log_format = fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
