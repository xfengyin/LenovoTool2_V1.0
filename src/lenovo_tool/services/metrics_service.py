"""Performance metrics service for tracking sampling latency, error counts, etc.

提供两类指标：
- PerformanceMetrics: 聚合指标，面向服务自检
- CommMetrics: 通信质量指标，面向 UI 通信诊断面板
"""

import time
from threading import RLock
from typing import Dict, Optional

from lenovo_tool.core.data_models import CommMetrics, PerformanceMetrics


class MetricsService:
    """Thread-safe service for collecting and reporting performance metrics.

    线程安全：所有公共方法均通过 ``RLock`` 保护。
    """

    def __init__(self) -> None:
        self._lock = RLock()
        # PerformanceMetrics 字段
        self._sample_count: int = 0
        self._total_delay_ms: float = 0.0
        self._max_delay_ms: float = 0.0
        self._min_delay_ms: float = float("inf")
        self._error_count: int = 0
        self._error_types: Dict[str, int] = {}
        self._start_time: float = time.time()
        # CommMetrics 扩展字段（通信诊断）
        self._success_count: int = 0
        self._consecutive_success: int = 0
        self._consecutive_failures: int = 0
        self._is_online: bool = True

    def record_sample(
        self,
        delay_ms: float,
        success: bool = True,
        error: Optional[BaseException] = None,
    ) -> None:
        """Record a sample with its latency.

        Args:
            delay_ms: 采样耗时（毫秒）。失败采样也记录（失败前等待时长）。
            success: 是否成功；向后兼容默认 True。
            error: 失败时附带异常，用于分类统计。
        """
        with self._lock:
            self._sample_count += 1
            self._total_delay_ms += delay_ms
            self._max_delay_ms = max(self._max_delay_ms, delay_ms)
            self._min_delay_ms = min(self._min_delay_ms, delay_ms)

            if success:
                self._success_count += 1
                self._consecutive_success += 1
                self._consecutive_failures = 0
                # 任一成功样本即视为在线
                self._is_online = True
            else:
                self._error_count += 1
                self._consecutive_failures += 1
                self._consecutive_success = 0
                self._is_online = False
                if error is not None:
                    err_type = type(error).__name__
                    self._error_types[err_type] = (
                        self._error_types.get(err_type, 0) + 1
                    )

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence (legacy API, 与 record_sample 互补)。

        仅更新错误计数与类型，不影响连续成功/失败等通信状态字段。
        """
        with self._lock:
            self._error_count += 1
            self._error_types[error_type] = self._error_types.get(error_type, 0) + 1

    def get_metrics(self) -> PerformanceMetrics:
        """Get a snapshot of current aggregated metrics."""
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

    def get_comm_metrics(self) -> CommMetrics:
        """Get a snapshot of communication metrics for the diagnostics panel."""
        with self._lock:
            avg = (
                self._total_delay_ms / self._sample_count
                if self._sample_count > 0
                else 0.0
            )
            return CommMetrics(
                sample_count=self._sample_count,
                success_count=self._success_count,
                error_count=self._error_count,
                avg_delay_ms=avg,
                max_delay_ms=self._max_delay_ms,
                min_delay_ms=(
                    self._min_delay_ms if self._sample_count > 0 else 0.0
                ),
                consecutive_success=self._consecutive_success,
                consecutive_failures=self._consecutive_failures,
                is_online=self._is_online,
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
            self._success_count = 0
            self._consecutive_success = 0
            self._consecutive_failures = 0
            self._is_online = True
