"""Tests for charge mode service."""

from unittest.mock import MagicMock

import pytest

from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.core.exceptions import ChargeModeError
from lenovo_tool.services.charge_mode import ChargeModeService, ChargeModeType


@pytest.fixture
def charge_service(mock_dll):
    return ChargeModeService(mock_dll)


def test_default_state(charge_service):
    """New service should have both modes disabled."""
    assert charge_service.fast_charge_enabled is False
    assert charge_service.night_charge_enabled is False


def test_toggle_fast_charge(charge_service, mock_dll):
    """Toggle should flip state and call DLL write."""
    result = charge_service.toggle(ChargeModeType.FAST_CHARGE)
    assert result is True
    assert charge_service.fast_charge_enabled is True
    mock_dll.write_smbus.assert_called_once_with(0, 0x26, 0x16, False)


def test_toggle_twice(charge_service, mock_dll):
    """Double toggle should return to original state."""
    charge_service.toggle(ChargeModeType.FAST_CHARGE)
    result = charge_service.toggle(ChargeModeType.FAST_CHARGE)
    assert result is False
    assert charge_service.fast_charge_enabled is False
    assert mock_dll.write_smbus.call_count == 2


def test_toggle_night_charge(charge_service, mock_dll):
    result = charge_service.toggle(ChargeModeType.NIGHT_CHARGE)
    assert result is True
    mock_dll.write_smbus.assert_called_once_with(0, 0x50, 0x16, False)


def test_toggle_independent(charge_service):
    """Toggling one mode should not affect the other."""
    charge_service.toggle(ChargeModeType.FAST_CHARGE)
    assert charge_service.fast_charge_enabled is True
    assert charge_service.night_charge_enabled is False


def test_is_enabled(charge_service):
    assert charge_service.is_enabled(ChargeModeType.FAST_CHARGE) is False
    charge_service.toggle(ChargeModeType.FAST_CHARGE)
    assert charge_service.is_enabled(ChargeModeType.FAST_CHARGE) is True
