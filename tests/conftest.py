"""Shared pytest fixtures."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lenovo_tool.core.data_models import (
    AppConfig,
    BatterySnapshot,
    LogSnapshot,
)
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.core.dll_loader import DLLPaths


@pytest.fixture
def sample_dll_paths() -> DLLPaths:
    return DLLPaths(
        swd_ec_path=Path("/fake/SWD_EC.dll"),
        sunwoda_path=Path("/fake/Sunwoda.dll"),
    )


@pytest.fixture
def mock_dll() -> MagicMock:
    """Mock DLLInterface with typical battery data."""
    mock = MagicMock(spec=DLLInterface)
    mock._lock = MagicMock()
    mock._lock.__enter__ = MagicMock(return_value=None)
    mock._lock.__exit__ = MagicMock(return_value=None)

    mock.read_int_word.return_value = 12450
    mock.read_neg_word.return_value = -1500
    mock.get_temperature.return_value = 35.0
    mock.read_soh.return_value = 95
    mock.life_prediction.return_value = 36
    mock.read_block.return_value = 1234
    mock.read_smbus.return_value = {"byte0": "01"}
    mock.get_first_usage_time.return_value = "2023-06-15"

    mock.read_all_main_registers.return_value = {
        "voltage": 12450,
        "current": -1500,
        "temperature": 35.0,
        "rsoc": 75,
        "soh": 95,
        "fcc": 6000,
        "rm": 4500,
        "dc": 6200,
        "dv": 15500,
        "battery_mode": 0x6001,
        "pl1": 45,
        "pl2": 65,
        "pl4": 90,
        "life_raw": 1792,
    }

    return mock


@pytest.fixture
def sample_snapshot() -> BatterySnapshot:
    return BatterySnapshot(
        timestamp=datetime(2026, 5, 14, 12, 0, 0),
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
        predicted_life_months=36,
    )


@pytest.fixture
def sample_log_snapshot() -> LogSnapshot:
    return LogSnapshot(
        timestamp=datetime(2026, 5, 14, 12, 0, 0),
        values={
            "Voltage": 12450,
            "Current": -1500,
            "Temperature": 35.0,
        },
        units={
            "Voltage": "mV",
            "Current": "mA",
            "Temperature": "\u2103",
        },
    )


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig()