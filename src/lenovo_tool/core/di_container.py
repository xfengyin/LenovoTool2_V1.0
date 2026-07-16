"""Dependency Injection container for managing service lifecycles.

Supports:
- Real/mock data source switching
- Singleton service instances
- Configuration injection
- Service lifecycle management
"""

from typing import Any, Callable, Dict, Type, TypeVar

from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.core.dll_interface import DLLInterface

T = TypeVar("T")


class DIContainer:
    """Simple but flexible DI container for the application."""

    def __init__(self) -> None:
        self._factories: Dict[str, Callable[..., Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._config: AppConfig | None = None
        self._data_source: DLLInterface | None = None
        self._is_demo_mode: bool = False

    def register_factory(self, key: str, factory: Callable[..., Any]) -> None:
        """Register a factory function for a service."""
        self._factories[key] = factory

    def register_instance(self, key: str, instance: Any) -> None:
        """Register a singleton instance."""
        self._instances[key] = instance

    def resolve(self, key: str, **kwargs: Any) -> Any:
        """Resolve a service by key.

        If an instance already exists, return it (singleton behavior).
        Otherwise, create a new instance using the registered factory.
        """
        if key in self._instances:
            return self._instances[key]

        if key in self._factories:
            instance = self._factories[key](self, **kwargs)
            self._instances[key] = instance
            return instance

        raise RuntimeError(f"No factory or instance registered for: {key}")

    def resolve_type(self, type_: Type[T]) -> T:
        """Resolve a service by type."""
        key = type_.__name__
        return self.resolve(key)  # type: ignore[return-value]

    def set_config(self, config: AppConfig) -> None:
        """Set the application configuration."""
        self._config = config
        self.register_instance("AppConfig", config)

    def set_data_source(self, dll: DLLInterface, is_demo: bool = False) -> None:
        """Set the data source (DLL interface)."""
        self._data_source = dll
        self._is_demo_mode = is_demo
        self.register_instance("DLLInterface", dll)

    @property
    def config(self) -> AppConfig:
        """Get the application configuration."""
        if self._config is None:
            raise RuntimeError("Config not set")
        return self._config

    @property
    def data_source(self) -> DLLInterface:
        """Get the data source."""
        if self._data_source is None:
            raise RuntimeError("Data source not set")
        return self._data_source

    @property
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self._is_demo_mode

    def reset(self) -> None:
        """Clear all registered instances (keeps factories)."""
        self._instances.clear()
        self._config = None
        self._data_source = None
        self._is_demo_mode = False

    def has(self, key: str) -> bool:
        """Check if a service is registered."""
        return key in self._factories or key in self._instances


def create_default_container(config: AppConfig, dll: DLLInterface, is_demo: bool = False) -> DIContainer:
    """Create a DI container with all default services registered."""
    container = DIContainer()
    container.set_config(config)
    container.set_data_source(dll, is_demo)

    from lenovo_tool.services.charge_mode import ChargeModeService
    from lenovo_tool.services.csv_export import CSVExportService
    from lenovo_tool.services.data_acquisition import DataAcquisitionService
    from lenovo_tool.services.life_prediction import LifePredictionService
    from lenovo_tool.services.log_data_service import LogDataService

    def charge_mode_factory(container: DIContainer) -> ChargeModeService:
        return ChargeModeService(container.data_source)

    def data_acquisition_factory(container: DIContainer) -> DataAcquisitionService:
        return DataAcquisitionService(container.data_source)

    def life_prediction_factory(_: DIContainer) -> LifePredictionService:
        return LifePredictionService()

    def log_data_factory(container: DIContainer) -> LogDataService:
        return LogDataService(container.data_source)

    def csv_export_factory(container: DIContainer) -> CSVExportService:
        import tempfile
        return CSVExportService(
            filepath=tempfile.mkstemp(suffix=".csv")[1],
            delimiter=container.config.csv_delimiter,
            encoding=container.config.csv_encoding,
        )

    container.register_factory("ChargeModeService", charge_mode_factory)
    container.register_factory("DataAcquisitionService", data_acquisition_factory)
    container.register_factory("LifePredictionService", life_prediction_factory)
    container.register_factory("LogDataService", log_data_factory)
    container.register_factory("CSVExportService", csv_export_factory)

    return container