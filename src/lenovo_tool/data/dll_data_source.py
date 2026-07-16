"""DLL-based battery data source implementation.

Wraps the low-level DLLInterface to provide a clean, protocol-compliant
data source for production use.
"""

from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.core.dll_loader import DLLLoader, DLLPaths
from lenovo_tool.core.interfaces import BatteryDataSource
from lenovo_tool.core.exceptions import (
    DLLCommunicationError,
    DLLNotFoundError,
    SMBusError,
)


class DLLDataSource(BatteryDataSource):
    """Battery data source backed by real SWD_EC.dll and Sunwoda.dll."""

    def __init__(self, dll_paths: DLLPaths | None = None) -> None:
        """Initialize the DLL data source.

        Args:
            dll_paths: Pre-configured DLL paths. If None, auto-detects paths.
        """
        if dll_paths is None:
            loader = DLLLoader()
            dll_paths = loader.find_dlls()

        self._dll = DLLInterface(dll_paths)

    @classmethod
    def from_search_paths(cls, search_paths: list[str]) -> "DLLDataSource":
        """Create a data source from custom DLL search paths."""
        loader = DLLLoader(search_paths=search_paths)
        dll_paths = loader.find_dlls()
        return cls(dll_paths)

    def read_all_main_registers(self) -> dict[str, int | float]:
        return self._dll.read_all_main_registers()

    def read_soh(self) -> int:
        return self._dll.read_soh()

    def get_temperature(self, addr: int = 0x08) -> float:
        return self._dll.get_temperature(addr)

    def get_first_usage_time(self, addr: int = 0x3F) -> str:
        return self._dll.get_first_usage_time(addr)

    def read_int_word(self, addr: int) -> int:
        return self._dll.read_int_word(addr)

    def read_neg_word(self, addr: int) -> int:
        return self._dll.read_neg_word(addr)

    def read_block(self, addr: int, start: int, length: int) -> int:
        return self._dll.read_block(addr, start, length)

    def write_smbus(self, type_: int, addr: int, slave: int, mode_state: bool) -> None:
        self._dll.write_smbus(type_, addr, slave, mode_state)

    def read_smbus(self, type_: int, addr: int, byte_length: int, slave: int) -> dict[str, str]:
        return self._dll.read_smbus(type_, addr, byte_length, slave)

    def life_prediction(self, addr: int = 0x6A) -> int:
        return self._dll.life_prediction(addr)