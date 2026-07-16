"""Tests for state manager."""

import pytest

from lenovo_tool.core.data_models import BatterySnapshot, ChargeMode, LogSnapshot
from lenovo_tool.services.state_manager import StateManager


def test_initial_state():
    """New state manager should have no observers and no state."""
    sm = StateManager()
    assert sm.get_state("battery") is None
    assert sm.get_subscriber_count("battery") == 0


def test_update_state():
    """Updating state should store the data."""
    sm = StateManager()
    sample_data = {"voltage": 12450, "current": -1500}
    sm.update("battery", sample_data)

    assert sm.get_state("battery") == sample_data


def test_subscribe_and_update():
    """Subscribers should receive notifications on state updates."""
    sm = StateManager()
    callback_data = []

    def callback(state_type, data):
        callback_data.append((state_type, data))

    sm.subscribe("battery", callback)
    sm.update("battery", {"voltage": 12450})

    assert len(callback_data) == 1
    assert callback_data[0][0] == "battery"
    assert callback_data[0][1] == {"voltage": 12450}


def test_multiple_subscribers():
    """Multiple subscribers should all receive notifications."""
    sm = StateManager()
    callback1_data = []
    callback2_data = []

    def callback1(state_type, data):
        callback1_data.append(data)

    def callback2(state_type, data):
        callback2_data.append(data)

    sm.subscribe("battery", callback1)
    sm.subscribe("battery", callback2)
    sm.update("battery", {"voltage": 12450})

    assert len(callback1_data) == 1
    assert len(callback2_data) == 1


def test_unsubscribe():
    """Unsubscribed observers should not receive notifications."""
    sm = StateManager()
    callback_data = []

    def callback(state_type, data):
        callback_data.append(data)

    sm.subscribe("battery", callback)
    sm.update("battery", {"voltage": 12450})
    sm.unsubscribe("battery", callback)
    sm.update("battery", {"voltage": 12500})

    assert len(callback_data) == 1


def test_different_state_types():
    """Observers should only receive updates for subscribed state types."""
    sm = StateManager()
    battery_data = []
    charge_data = []

    def battery_callback(state_type, data):
        battery_data.append(data)

    def charge_callback(state_type, data):
        charge_data.append(data)

    sm.subscribe("battery", battery_callback)
    sm.subscribe("charge_mode", charge_callback)

    sm.update("battery", {"voltage": 12450})
    sm.update("charge_mode", {"fast_charge": True})

    assert len(battery_data) == 1
    assert len(charge_data) == 1


def test_get_battery_snapshot():
    """Convenience method should return battery snapshot."""
    sm = StateManager()
    snapshot = BatterySnapshot(
        timestamp=None,
        voltage=12450,
        current=-1500,
        temperature=35.0,
        rsoc=75,
        soh=95,
        fcc=6000,
        rm=4500,
        dc=6200,
        dv=15500,
        battery_mode=0x6001,
        pl1=45,
        pl2=65,
        pl4=90,
    )
    sm.update("battery", snapshot)

    result = sm.get_battery_snapshot()
    assert result is snapshot
    assert isinstance(result, BatterySnapshot)


def test_get_charge_mode():
    """Convenience method should return charge mode."""
    sm = StateManager()
    charge_mode = ChargeMode(fast_charge_enabled=True)
    sm.update("charge_mode", charge_mode)

    result = sm.get_charge_mode()
    assert result is charge_mode
    assert isinstance(result, ChargeMode)


def test_clear_state():
    """clear_state should remove specific state."""
    sm = StateManager()
    sm.update("battery", {"voltage": 12450})
    sm.update("charge_mode", {"fast_charge": True})

    sm.clear_state("battery")
    assert sm.get_state("battery") is None
    assert sm.get_state("charge_mode") is not None


def test_clear_all():
    """clear_all should remove all states and observers."""
    sm = StateManager()

    def callback(state_type, data):
        pass

    sm.subscribe("battery", callback)
    sm.update("battery", {"voltage": 12450})

    sm.clear_all()
    assert sm.get_state("battery") is None
    assert sm.get_subscriber_count("battery") == 0


def test_get_subscriber_count():
    """get_subscriber_count should return correct count."""
    sm = StateManager()

    def callback1(state_type, data):
        pass

    def callback2(state_type, data):
        pass

    sm.subscribe("battery", callback1)
    sm.subscribe("battery", callback2)
    sm.subscribe("charge_mode", callback1)

    assert sm.get_subscriber_count("battery") == 2
    assert sm.get_subscriber_count("charge_mode") == 1
    assert sm.get_subscriber_count("unknown") == 0
