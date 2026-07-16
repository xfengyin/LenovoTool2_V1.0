"""Structured logging setup with traceId support for the application."""

import logging
import sys
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Any

from lenovo_tool.core.interfaces import LoggerProvider

_trace_id: ContextVar[str | None] = ContextVar(
    "trace_id", default=None
)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with traceId support."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        trace_id = _trace_id.get()
        if trace_id:
            record.trace_id = trace_id

        record.asctime = self.formatTime(record, self.datefmt)

        log_entry: dict[str, Any] = {
            "timestamp": record.asctime,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)

        trace_id_str = f"traceId={log_entry['trace_id']} " if log_entry.get("trace_id") else ""
        return (
            f"{log_entry['timestamp']} [{log_entry['level']}] "
            f"{trace_id_str}"
            f"{log_entry['logger']}: {log_entry['message']}"
        )


class TraceLogger:
    """Logger wrapper with traceId support."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal log method."""
        if kwargs:
            record = logging.LogRecord(
                name=self._logger.name,
                level=level,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )
            record.__dict__["extra"] = kwargs
            self._logger.handle(record)
        else:
            self._logger.log(level, message)


class LoggerManager(LoggerProvider):
    """Logger provider with structured logging and traceId support."""

    def __init__(self) -> None:
        self._loggers: dict[str, TraceLogger] = {}

    def get_logger(self, name: str) -> TraceLogger:
        """Get a named logger instance with traceId support.

        Args:
            name: Logger name

        Returns:
            TraceLogger instance
        """
        if name not in self._loggers:
            underlying = logging.getLogger(name)
            self._loggers[name] = TraceLogger(underlying)
        return self._loggers[name]


def setup_logging(
    level: str = "INFO",
    fmt: str | None = None,
    log_file: str | None = None,
    enable_structured: bool = True,
) -> None:
    """Configure root logger for the application.

    Args:
        level: log level string (DEBUG, INFO, WARNING, ERROR)
        fmt: log format string
        log_file: optional path to log file
        enable_structured: enable structured logging with traceId
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    formatter: logging.Formatter
    if enable_structured:
        formatter = StructuredFormatter(fmt)
    else:
        formatter = logging.Formatter(
            fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
    )


def get_logger(name: str) -> TraceLogger:
    """Get a named logger with traceId support.

    Args:
        name: Logger name

    Returns:
        TraceLogger instance
    """
    manager = LoggerManager()
    return manager.get_logger(name)


def generate_trace_id() -> str:
    """Generate a new trace ID.

    Returns:
        UUID-based trace ID string
    """
    return str(uuid.uuid4())


def set_trace_id(trace_id: str | None) -> None:
    """Set the current trace ID in context.

    Args:
        trace_id: Trace ID to set, or None to clear
    """
    _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    """Get the current trace ID from context.

    Returns:
        Current trace ID or None
    """
    return _trace_id.get()


def with_trace_id(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to automatically set a trace ID for a function."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        try:
            return func(*args, **kwargs)
        finally:
            set_trace_id(None)

    return wrapper
