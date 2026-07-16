"""Performance metrics service for tracking sampling latency, error counts, etc."""

import time
from threading import RLock
from typing import Dict, Optional

from lenovo_tool.core.data_models import PerformanceMetrics


class MetricsService:
    """Thread-safe service for collecting and reporting performance metrics."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sample_count: int = 0
        self._total_delay_ms: float = 0.0
        self._max_delay_ms: float = 0.0
        self._min_delay_ms: float = float("inf")
        self._error_count: int = 0
        self._error_types: Dict[str, int] = {}
        self._start_time: float = time.time()

    def record_sample(self, delay_ms: float) -> None:
        """Record a successful sample with its latency."""
        with self._lock:
            self._sample_count += 1
            self._total_delay_ms += delay_ms
            self._max_delay_ms = max(self._max_delay_ms, delay_ms)
            self._min_delay_ms = min(self._min_delay_ms, delay_ms)

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence."""
        with self._lock:
            self._error_count += 1
            self._error_types[error_type] = self._error_types.get(error_type, 0) + 1

    def get_metrics(self) -> PerformanceMetrics:
        """Get a snapshot of current metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            return PerformanceMetrics(
                sample_count=self._sample_count,
                total_delay_ms=self._total_delay_ms,
                max_delay_ms=self._max_delay_ms,
                min_delay_ms=self._min_delay_ms if self._sample_count > 0 else 0.0,
                error_count=self._error_count,
                error_types=self._error_types.copy(),
                uptime_seconds=uptime,
            )

    @property
    def average_delay_ms(self) -> float:
        """Calculate average latency across all samples."""
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            return self._total_delay_ms / self._sample_count

    def reset(self) -> None:
        """Reset all metrics to their initial state."""
        with self._lock:
            self._sample_count = 0
            self._total_delay_ms = 0.0
            self._max_delay_ms = 0.0
            self._min_delay_ms = float("inf")
            self._error_count = 0
            self._error_types = {}
            self._start_time = time.time()
