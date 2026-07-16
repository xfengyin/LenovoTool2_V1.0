"""Integration tests for service collaboration and DI container."""

import pytest

from lenovo_tool.core.di_container import DIContainer
from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.services.charge_mode import ChargeModeService, ChargeModeType
from lenovo_tool.services.data_acquisition import DataAcquisitionService
from lenovo_tool.services.life_prediction import LifePredictionService
from lenovo_tool.services.log_data_service import LogDataService


class TestDIContainerIntegration:
    """Integration tests for DI container functionality."""

    def test_container_resolves_all_core_services(self, di_container):
        """DI container should resolve all registered services."""
        charge_mode = di_container.resolve("ChargeModeService")
        data_acq = di_container.resolve("DataAcquisitionService")
        life_pred = di_container.resolve("LifePredictionService")
        log_data = di_container.resolve("LogDataService")

        assert isinstance(charge_mode, ChargeModeService)
        assert isinstance(data_acq, DataAcquisitionService)
        assert isinstance(life_pred, LifePredictionService)
        assert isinstance(log_data, LogDataService)

    def test_container_resolves_by_type(self, di_container):
        """DI container should resolve services by type."""
        service = di_container.resolve_type(ChargeModeService)
        assert isinstance(service, ChargeModeService)

    def test_container_is_singleton(self, di_container):
        """Resolving same service twice should return same instance."""
        service1 = di_container.resolve("ChargeModeService")
        service2 = di_container.resolve("ChargeModeService")
        assert service1 is service2

    def test_container_has_method(self, di_container):
        """Container should have correct has() behavior."""
        assert di_container.has("ChargeModeService")
        assert di_container.has("DataAcquisitionService")
        assert not di_container.has("NonExistentService")

    def test_container_config_access(self, di_container, app_config):
        """Container should provide access to config."""
        assert di_container.config is not None
        assert isinstance(di_container.config, AppConfig)
        assert di_container.config == app_config

    def test_container_data_source_access(self, di_container, mock_dll):
        """Container should provide access to data source."""
        assert di_container.data_source is not None
        assert di_container.data_source == mock_dll

    def test_container_is_demo_mode(self, di_container):
        """Container should correctly report demo mode."""
        assert di_container.is_demo_mode is True

    def test_container_reset_clears_instances(self, di_container):
        """Reset should clear all instances but keep factories."""
        service = di_container.resolve("ChargeModeService")
        di_container.reset()

        with pytest.raises(RuntimeError, match="Config not set"):
            _ = di_container.config
        with pytest.raises(RuntimeError, match="Data source not set"):
            _ = di_container.data_source

    def test_container_resolve_type_works(self, di_container):
        """resolve_type should work for all registered services."""
        charge_mode = di_container.resolve_type(ChargeModeService)
        data_acq = di_container.resolve_type(DataAcquisitionService)
        life_pred = di_container.resolve_type(LifePredictionService)
        log_data = di_container.resolve_type(LogDataService)

        assert isinstance(charge_mode, ChargeModeService)
        assert isinstance(data_acq, DataAcquisitionService)
        assert isinstance(life_pred, LifePredictionService)
        assert isinstance(log_data, LogDataService)


class TestServiceIntegration:
    """Integration tests for service collaboration."""

    def test_charge_mode_service_uses_data_source(self, di_container):
        """ChargeModeService should use container's data source."""
        service = di_container.resolve("ChargeModeService")
        assert service._datasource == di_container.data_source

    def test_data_acquisition_uses_data_source(self, di_container):
        """DataAcquisitionService should use container's data source."""
        service = di_container.resolve("DataAcquisitionService")
        assert service._datasource == di_container.data_source

    def test_log_data_service_uses_data_source(self, di_container):
        """LogDataService should use container's data source."""
        service = di_container.resolve("LogDataService")
        assert service._datasource == di_container.data_source

    def test_services_share_same_data_source(self, di_container):
        """All services should share the same data source instance."""
        charge_mode = di_container.resolve("ChargeModeService")
        data_acq = di_container.resolve("DataAcquisitionService")
        log_data = di_container.resolve("LogDataService")

        assert charge_mode._datasource is data_acq._datasource
        assert data_acq._datasource is log_data._datasource

    def test_data_acquisition_fetches_snapshot(self, di_container):
        """DataAcquisitionService should fetch valid snapshots."""
        service = di_container.resolve("DataAcquisitionService")
        snapshot = service.fetch_snapshot()

        assert snapshot.voltage == 12450
        assert snapshot.current == -1500
        assert snapshot.temperature == 35.0
        assert snapshot.rsoc == 75
        assert snapshot.soh == 95
        assert snapshot.predicted_life_months == 36

    def test_life_prediction_service_predict(self, di_container):
        """LifePredictionService should predict correctly."""
        service = di_container.resolve("LifePredictionService")
        assert service.predict(1792) == 36
        assert service.predict(1024) == 6
        assert service.predict(500) == 0

    def test_charge_mode_toggle(self, di_container, mock_dll):
        """ChargeModeService should toggle modes correctly."""
        service = di_container.resolve("ChargeModeService")
        result = service.toggle(ChargeModeType.FAST_CHARGE)
        assert result is True
        mock_dll.write_smbus.assert_called_once()


class TestDataSourceSwitching:
    """Integration tests for data source switching."""

    def test_demo_dll_interface_is_functional(self, demo_dll_interface):
        """DemoDLLInterface should provide realistic mock data."""
        data = demo_dll_interface.read_all_main_registers()

        assert "voltage" in data
        assert "current" in data
        assert "temperature" in data
        assert "rsoc" in data
        assert "soh" in data

        assert 12000 <= data["voltage"] <= 17000
        assert 28.0 <= data["temperature"] <= 45.0
        assert 0 <= data["rsoc"] <= 100
        assert 40 <= data["soh"] <= 100

    def test_demo_dll_interface_methods(self, demo_dll_interface):
        """DemoDLLInterface should implement all required methods."""
        assert demo_dll_interface.read_int_word(0x09) > 0
        assert demo_dll_interface.read_neg_word(0x0A) is not None
        assert demo_dll_interface.get_temperature(0x08) > 0
        assert demo_dll_interface.read_soh() > 0
        assert demo_dll_interface.life_prediction(0x6A) >= 0
        assert demo_dll_interface.get_first_usage_time(0x3F) == "2023-06-15"
        assert isinstance(demo_dll_interface.read_smbus(0, 0x26, 1, 0x16), dict)

    def test_di_container_with_demo_dll(self, di_container_demo):
        """DI container should work with DemoDLLInterface."""
        service = di_container_demo.resolve("DataAcquisitionService")
        snapshot = service.fetch_snapshot()

        assert snapshot is not None
        assert snapshot.voltage > 0
        assert snapshot.temperature > 0

    def test_demo_mode_is_correctly_set(self, di_container_demo):
        """Demo mode flag should be correctly set."""
        assert di_container_demo.is_demo_mode is True

    def test_demo_switch_between_mock_and_demo(self, app_config, mock_dll, demo_dll_interface):
        """Should be able to switch between mock and demo data sources."""
        container1 = DIContainer()
        container1.set_config(app_config)
        container1.set_data_source(mock_dll, is_demo=True)

        container2 = DIContainer()
        container2.set_config(app_config)
        container2.set_data_source(demo_dll_interface, is_demo=True)

        assert container1.data_source is mock_dll
        assert container2.data_source is demo_dll_interface


class TestConfigDynamicReload:
    """Integration tests for configuration dynamic reload."""

    def test_config_reload_updates_container(self, di_container):
        """Changing config should be reflected in container."""
        original_title = di_container.config.window_title

        new_config = AppConfig(window_title="Test Title")
        di_container.set_config(new_config)

        assert di_container.config.window_title == "Test Title"
        assert di_container.config.window_title != original_title

    def test_config_update_reflects_in_services(self, di_container):
        """Config updates should be available to services."""
        csv_service = di_container.resolve("CSVExportService")
        original_delimiter = di_container.config.csv_delimiter

        new_config = AppConfig(csv_delimiter=";")
        di_container.set_config(new_config)

        assert di_container.config.csv_delimiter == ";"
        assert di_container.config.csv_delimiter != original_delimiter