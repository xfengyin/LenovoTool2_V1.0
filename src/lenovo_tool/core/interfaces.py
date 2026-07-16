"""Protocol interfaces for battery data sources and configuration providers.

This module defines abstract protocols that any battery data source or config provider
must implement, enabling dependency inversion and testability.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class ConfigProvider(Protocol[T_co]):
    """Protocol defining the interface for configuration providers."""

    @property
    def config(self) -> T_co:
        """Get the current configuration."""
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path."""
        ...

    def reload(self) -> None:
        """Reload configuration from source."""
        ...

    def watch(self, callback: Callable[[], None]) -> None:
        """Register a callback for configuration change events."""
        ...

    def unwatch(self, callback: Callable[[], None]) -> None:
        """Unregister a callback from configuration change events."""
        ...


class LoggerProvider(ABC):
    """Interface for logger providers."""

    @abstractmethod
    def get_logger(self, name: str) -> Any:
        """Get a named logger instance."""
        ...


@runtime_checkable
class BatteryDataSource(Protocol):
    """Protocol defining the interface for battery data sources.

    All data sources (DLL-based, mock, etc.) must implement these methods.
    """

    def read_all_main_registers(self) -> dict[str, int | float]:
        """Read all main data registers atomically."""
        ...

    def read_soh(self) -> int:
        """Calculate State of Health percentage (0-100)."""
        ...

    def get_temperature(self, addr: int = 0x08) -> float:
        """Read temperature in Celsius."""
        ...

    def get_first_usage_time(self, addr: int = 0x3F) -> str:
        """Get the first usage date of the battery."""
        ...

    def read_int_word(self, addr: int) -> int:
        """Read unsigned 16-bit value from register address."""
        ...

    def read_neg_word(self, addr: int) -> int:
        """Read signed 16-bit value from register address."""
        ...

    def read_block(self, addr: int, start: int, length: int) -> int:
        """Read a block of data from the EC."""
        ...

    def write_smbus(self, type_: int, addr: int, slave: int, mode_state: bool) -> None:
        """Write a command to the EC via SMBus."""
        ...

    def read_smbus(self, type_: int, addr: int, byte_length: int, slave: int) -> dict[str, str]:
        """Read data from the EC via SMBus."""
        ...

    def life_prediction(self, addr: int = 0x6A) -> int:
        """Predict remaining battery life in months."""
        ...
