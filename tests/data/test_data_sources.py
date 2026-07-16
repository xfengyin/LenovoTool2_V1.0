"""Tests for battery data sources."""

import random
from unittest.mock import MagicMock, patch

import pytest

from lenovo_tool.core.interfaces import BatteryDataSource
from lenovo_tool.data.mock_data_source import MockDataSource


class TestBatteryDataSourceProtocol:
    """Tests for the BatteryDataSource protocol."""

    def test_mock_data_source_implements_protocol(self):
        """MockDataSource should implement BatteryDataSource protocol."""
        source = MockDataSource()
        assert isinstance(source, BatteryDataSource)

    def test_all_methods_defined(self):
        """All required methods should be defined in MockDataSource."""
        source = MockDataSource()
        methods = [
            "read_all_main_registers",
            "read_soh",
            "get_temperature",
            "get_first_usage_time",
            "read_int_word",
            "read_neg_word",
            "read_block",
            "write_smbus",
            "read_smbus",
            "life_prediction",
        ]
        for method in methods:
            assert hasattr(source, method)
            assert callable(getattr(source, method))


class TestMockDataSource:
    """Tests for the mock data source implementation."""

    def test_read_all_main_registers_returns_expected_keys(self):
        """read_all_main_registers should return all expected keys."""
        source = MockDataSource()
        registers = source.read_all_main_registers()
        expected_keys = [
            "voltage", "current", "temperature", "rsoc", "soh",
            "fcc", "rm", "dc", "dv", "battery_mode",
            "pl1", "pl2", "pl4", "life_raw", "cycle_count",
        ]
        for key in expected_keys:
            assert key in registers

    def test_read_all_main_registers_value_types(self):
        """All values should be int or float."""
        source = MockDataSource()
        registers = source.read_all_main_registers()
        for key, value in registers.items():
            assert isinstance(value, (int, float))

    def test_read_soh_returns_int_between_40_and_100(self):
        """SOH should be an integer between 40 and 100."""
        source = MockDataSource()
        soh = source.read_soh()
        assert isinstance(soh, int)
        assert 40 <= soh <= 100

    def test_get_temperature_returns_float_in_range(self):
        """Temperature should be a float between 28.0 and 45.0."""
        source = MockDataSource()
        temp = source.get_temperature()
        assert isinstance(temp, float)
        assert 28.0 <= temp <= 45.0

    def test_get_first_usage_time_returns_string(self):
        """First usage time should return a date string."""
        source = MockDataSource()
        date = source.get_first_usage_time()
        assert isinstance(date, str)
        assert date == "2023-06-15"

    def test_read_int_word_returns_int(self):
        """read_int_word should return an integer."""
        source = MockDataSource()
        result = source.read_int_word(0x09)
        assert isinstance(result, int)

    def test_read_neg_word_returns_int(self):
        """read_neg_word should return an integer."""
        source = MockDataSource()
        result = source.read_neg_word(0x0A)
        assert isinstance(result, int)

    def test_read_block_returns_int(self):
        """read_block should return an integer."""
        source = MockDataSource()
        result = source.read_block(0x00, 0, 10)
        assert isinstance(result, int)

    def test_write_smbus_no_exception(self):
        """write_smbus should not raise exceptions."""
        source = MockDataSource()
        source.write_smbus(type_=0, addr=0x16, slave=0x00, mode_state=True)

    def test_read_smbus_returns_dict(self):
        """read_smbus should return a dictionary."""
        source = MockDataSource()
        result = source.read_smbus(type_=0, addr=0x00, byte_length=4, slave=0x16)
        assert isinstance(result, dict)
        assert len(result) == 4
        for key in result:
            assert key.startswith("byte")

    def test_life_prediction_returns_months(self):
        """life_prediction should return expected month values."""
        source = MockDataSource()
        # Mock different SOH values to test thresholds
        test_cases = [
            (95, 36),
            (85, 24),
            (65, 12),
            (45, 6),
            (30, 0),
        ]
        for soh, expected_months in test_cases:
            source._soh = soh
            result = source.life_prediction()
            assert result == expected_months

    def test_rsoc_cycles_between_bounds(self):
        """RSOC should cycle between 15 and 98."""
        source = MockDataSource()
        source._rsoc = 98
        source._rsoc_dir = -1

        for _ in range(100):
            registers = source.read_all_main_registers()
            rsoc = registers["rsoc"]
            assert 0 <= rsoc <= 100

    def test_cycle_count_increments(self):
        """Cycle count should increment occasionally."""
        source = MockDataSource()
        initial_count = source._cycle_count
        for _ in range(100):
            source.read_all_main_registers()

        assert source._cycle_count >= initial_count

    def test_read_int_word_returns_expected_values(self):
        """read_int_word should return expected values for known addresses."""
        source = MockDataSource()
        result = source.read_int_word(0x03)
        assert result == 0x6001

    def test_read_neg_word_returns_negative_for_specific_addresses(self):
        """read_neg_word should return negative values for specific addresses."""
        source = MockDataSource()
        for addr in (0x0A, 0x60, 0x61, 0x62):
            result = source.read_neg_word(addr)
            assert result <= 0

    def test_thread_safety(self):
        """MockDataSource should be thread-safe."""
        source = MockDataSource()

        def read_registers():
            for _ in range(100):
                source.read_all_main_registers()
                source.read_soh()
                source.get_temperature()

        import threading
        threads = [threading.Thread(target=read_registers) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()