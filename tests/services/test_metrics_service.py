"""Tests for metrics service."""

import pytest

from lenovo_tool.core.data_models import PerformanceMetrics
from lenovo_tool.services.metrics_service import MetricsService


def test_initial_state():
    """New service should have zeroed metrics."""
    svc = MetricsService()
    metrics = svc.get_metrics()

    assert metrics.sample_count == 0
    assert metrics.total_delay_ms == 0.0
    assert metrics.max_delay_ms == 0.0
    assert metrics.min_delay_ms == 0.0
    assert metrics.error_count == 0
    assert metrics.error_types == {}
    assert metrics.uptime_seconds > 0


def test_record_sample():
    """Recording samples should update metrics."""
    svc = MetricsService()
    svc.record_sample(100.0)
    svc.record_sample(200.0)
    svc.record_sample(150.0)

    metrics = svc.get_metrics()
    assert metrics.sample_count == 3
    assert metrics.total_delay_ms == 450.0
    assert metrics.max_delay_ms == 200.0
    assert metrics.min_delay_ms == 100.0
    assert svc.average_delay_ms == 150.0


def test_record_error():
    """Recording errors should update error counts."""
    svc = MetricsService()
    svc.record_error("DLLCommunicationError")
    svc.record_error("DLLCommunicationError")
    svc.record_error("SMBusError")

    metrics = svc.get_metrics()
    assert metrics.error_count == 3
    assert metrics.error_types["DLLCommunicationError"] == 2
    assert metrics.error_types["SMBusError"] == 1


def test_reset():
    """Reset should clear all metrics."""
    svc = MetricsService()
    svc.record_sample(100.0)
    svc.record_error("TestError")
    svc.reset()

    metrics = svc.get_metrics()
    assert metrics.sample_count == 0
    assert metrics.total_delay_ms == 0.0
    assert metrics.max_delay_ms == 0.0
    assert metrics.min_delay_ms == 0.0
    assert metrics.error_count == 0
    assert metrics.error_types == {}


def test_average_delay_empty():
    """Average delay should be 0 when no samples recorded."""
    svc = MetricsService()
    assert svc.average_delay_ms == 0.0


def test_get_metrics_returns_copy():
    """get_metrics should return a copy that doesn't reflect future changes."""
    svc = MetricsService()
    svc.record_sample(100.0)
    metrics = svc.get_metrics()

    svc.record_sample(200.0)
    new_metrics = svc.get_metrics()

    assert metrics.sample_count == 1
    assert new_metrics.sample_count == 2
