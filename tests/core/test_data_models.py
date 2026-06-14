"""Tests for immutable data models."""

from datetime import datetime

import pytest

from lenovo_tool.core.data_models import BatterySnapshot, AppConfig, ChargeMode


def test_battery_snapshot_is_frozen():
    """BatterySnapshot should be immutable."""
    snap = BatterySnapshot(
        timestamp=datetime.now(),
        voltage=12000, current=-1000, temperature=30.0,
        rsoc=50, soh=90, fcc=5000, rm=2500,
        dc=5500, dv=15000, battery_mode=0x6001,
        pl1=45, pl2=65, pl4=90,
    )
    with pytest.raises(Exception):
        snap.voltage = 13000  # type: ignore


def test_battery_snapshot_equality(sample_snapshot):
    """Two snapshots with same fields should be equal."""
    s2 = BatterySnapshot(
        timestamp=sample_snapshot.timestamp,
        voltage=sample_snapshot.voltage,
        current=sample_snapshot.current,
        temperature=sample_snapshot.temperature,
        rsoc=sample_snapshot.rsoc,
        soh=sample_snapshot.soh,
        fcc=sample_snapshot.fcc,
        rm=sample_snapshot.rm,
        dc=sample_snapshot.dc,
        dv=sample_snapshot.dv,
        battery_mode=sample_snapshot.battery_mode,
        pl1=sample_snapshot.pl1,
        pl2=sample_snapshot.pl2,
        pl4=sample_snapshot.pl4,
        predicted_life_months=36,
    )
    assert sample_snapshot == s2


def test_charge_mode_defaults():
    """ChargeMode should default to all False."""
    cm = ChargeMode()
    assert cm.fast_charge_enabled is False
    assert cm.night_charge_enabled is False


def test_app_config_defaults():
    """AppConfig should have sensible defaults."""
    cfg = AppConfig()
    assert cfg.poll_interval_ms == 4000
    assert cfg.chart_history_seconds == 60
    assert cfg.window_title == "Lenovo Battery Tool"
    assert cfg.temperature_warning_threshold == 60.0
