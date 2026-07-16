"""Unit tests for MainViewModel."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from lenovo_tool.core.data_models import BatterySnapshot, AppConfig
from lenovo_tool.ui.view_models.main_view_model import MainViewModel


@pytest.fixture
def mock_dll():
    return MagicMock()


@pytest.fixture
def config():
    return AppConfig(
        poll_interval_ms=4000,
        chart_history_seconds=60,
    )


@pytest.fixture
def view_model(mock_dll, config):
    with patch('lenovo_tool.ui.view_models.main_view_model.DataAcquisitionService'):
        with patch('lenovo_tool.ui.view_models.main_view_model.ChargeModeService'):
            return MainViewModel(mock_dll, config)


@pytest.fixture
def sample_snapshot():
    return BatterySnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        voltage=15000,
        current=1000,
        temperature=25.0,
        rsoc=80,
        soh=95,
        fcc=5000,
        rm=4000,
        dc=5000,
        dv=16800,
        battery_mode=0x01,
        pl1=30,
        pl2=60,
        pl4=90,
        predicted_life_months=24,
        cycle_count=100,
        first_usage_time="2023-06-15",
        charge_state="charging",
        max_temperature=35.0,
        min_voltage=14000,
        max_voltage=15500,
    )


class TestMainViewModel:
    def test_initial_state(self, view_model):
        assert view_model.sample_count == 0
        assert view_model.runtime == 0.0
        assert not view_model.fast_charge_enabled
        assert not view_model.night_charge_enabled

    def test_start_session(self, view_model):
        view_model.start_session()
        assert view_model.sample_count == 0
        assert view_model.runtime >= 0.0

    def test_process_snapshot(self, view_model, sample_snapshot):
        view_model.start_session()
        view_model.process_snapshot(sample_snapshot)

        assert view_model.sample_count == 1
        assert view_model.fast_charge_enabled is True
        assert view_model.night_charge_enabled is False

    def test_process_multiple_snapshots(self, view_model, sample_snapshot):
        view_model.start_session()
        for _ in range(5):
            view_model.process_snapshot(sample_snapshot)

        assert view_model.sample_count == 5

    def test_calculate_capacity_percentages(self, view_model, sample_snapshot):
        fcc_pct, rm_pct = view_model.calculate_capacity_percentages(sample_snapshot)

        assert fcc_pct == 100.0
        assert rm_pct == 80.0

    def test_calculate_capacity_percentages_zero_dc(self, view_model):
        snapshot = BatterySnapshot(
            timestamp=datetime.now(),
            voltage=0,
            current=0,
            temperature=0.0,
            rsoc=0,
            soh=0,
            fcc=5000,
            rm=4000,
            dc=0,
            dv=0,
            battery_mode=0,
            pl1=0,
            pl2=0,
            pl4=0,
        )
        fcc_pct, rm_pct = view_model.calculate_capacity_percentages(snapshot)

        assert fcc_pct == 0.0
        assert rm_pct == 0.0

    def test_format_charge_state(self, view_model):
        assert view_model.format_charge_state("charging") == ("充电中", "#00e676")
        assert view_model.format_charge_state("discharging") == ("放电中", "#ffab40")
        assert view_model.format_charge_state("idle") == ("待机", "#7a8fa3")
        assert view_model.format_charge_state("full") == ("已满", "#448aff")
        assert view_model.format_charge_state("unknown") == ("未知", "#7a8fa3")

    def test_format_temperature_color(self, view_model):
        assert view_model.format_temperature_color(65.0) == "#ff5252"
        assert view_model.format_temperature_color(50.0) == "#ffab40"
        assert view_model.format_temperature_color(40.0) == "#e0e8f0"

    def test_get_voltage_range_text(self, view_model, sample_snapshot):
        result = view_model.get_voltage_range_text(sample_snapshot)
        assert result == "14000-15500"

    def test_format_runtime(self, view_model):
        view_model.start_session()
        runtime = view_model.format_runtime()
        assert isinstance(runtime, str)
        assert len(runtime) == 8
        assert runtime.count(":") == 2

    def test_get_status_bar_text(self, view_model, sample_snapshot):
        view_model.start_session()
        view_model.process_snapshot(sample_snapshot)
        text = view_model.get_status_bar_text(sample_snapshot)

        assert "采样 #1" in text
        assert "12:00:00" in text
        assert "15000mV" in text
        assert "1000mA" in text
        assert "25.0" in text
        assert "RSOC=80%" in text

    def test_toggle_fast_charge_success(self, view_model):
        view_model._charge_service.toggle.return_value = True
        result = view_model.toggle_fast_charge()

        assert result is True
        assert view_model.fast_charge_enabled is True
        view_model._charge_service.toggle.assert_called_once()

    def test_toggle_fast_charge_failure(self, view_model):
        view_model._charge_service.toggle.side_effect = Exception("toggle failed")

        with pytest.raises(Exception):
            view_model.toggle_fast_charge()

    def test_toggle_night_charge_success(self, view_model):
        view_model._charge_service.toggle.return_value = True
        result = view_model.toggle_night_charge()

        assert result is True
        assert view_model.night_charge_enabled is True
        view_model._charge_service.toggle.assert_called_once()

    def test_update_charge_mode_state(self, view_model):
        view_model._update_charge_mode_state(0x03)
        assert view_model.fast_charge_enabled is True
        assert view_model.night_charge_enabled is True

        view_model._update_charge_mode_state(0x00)
        assert view_model.fast_charge_enabled is False
        assert view_model.night_charge_enabled is False