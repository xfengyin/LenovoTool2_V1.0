"""Tests for data acquisition service."""

from unittest.mock import MagicMock

import pytest

from lenovo_tool.core.data_models import BatterySnapshot
from lenovo_tool.services.data_acquisition import DataAcquisitionService


def test_fetch_snapshot_returns_battery_snapshot(mock_dll):
    """fetch_snapshot() should return a BatterySnapshot with all fields."""
    svc = DataAcquisitionService(mock_dll)
    snapshot = svc.fetch_snapshot()

    assert isinstance(snapshot, BatterySnapshot)
    # Values come from mock_dll.read_all_main_registers()
    assert snapshot.voltage == 12450
    assert snapshot.current == -1500
    assert snapshot.temperature == 35.0
    assert snapshot.rsoc == 75
    assert snapshot.soh == 95
    assert snapshot.fcc == 6000
    assert snapshot.rm == 4500
    assert snapshot.dc == 6200
    assert snapshot.dv == 15500
    assert snapshot.battery_mode == 0x6001
    assert snapshot.pl1 == 45
    assert snapshot.pl2 == 65
    assert snapshot.pl4 == 90
    assert snapshot.predicted_life_months == 36


def test_fetch_snapshot_has_timestamp(mock_dll):
    """Snapshot should include a timestamp."""
    svc = DataAcquisitionService(mock_dll)
    snapshot = svc.fetch_snapshot()
    assert snapshot.timestamp is not None


def test_fetch_snapshot_calls_read_all_main_registers(mock_dll):
    """Should call read_all_main_registers() for atomic snapshot."""
    svc = DataAcquisitionService(mock_dll)
    svc.fetch_snapshot()

    mock_dll.read_all_main_registers.assert_called_once()