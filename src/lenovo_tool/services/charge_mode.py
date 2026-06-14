"""Charge mode switching service.

Replaces the global mutable state in legacy Switchmode.py with
proper instance-based state management.

Registers:
  - 0x26: Fast charge mode (SmartCharge)
  - 0x50: Night charge mode (LightCharge)
  Slave address: 0x16, block type write
"""

from enum import Enum

from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.core.exceptions import ChargeModeError


class ChargeModeType(Enum):
    FAST_CHARGE = "fast_charge"
    NIGHT_CHARGE = "night_charge"


MODE_CONFIG: dict[ChargeModeType, dict] = {
    ChargeModeType.FAST_CHARGE: {
        "addr": 0x26,
        "name": "快充",
    },
    ChargeModeType.NIGHT_CHARGE: {
        "addr": 0x50,
        "name": "夜充",
    },
}

SLAVE_ADDR: int = 0x16


class ChargeModeService:
    """Manages charge mode switching with proper state encapsulation."""

    def __init__(self, dll: DLLInterface):
        self._dll = dll
        self._states: dict[ChargeModeType, bool] = {
            ChargeModeType.FAST_CHARGE: False,
            ChargeModeType.NIGHT_CHARGE: False,
        }

    def toggle(self, mode: ChargeModeType) -> bool:
        """Toggle a charge mode. Returns the new state."""
        if mode not in MODE_CONFIG:
            raise ChargeModeError(f"Unknown charge mode: {mode}")

        config = MODE_CONFIG[mode]
        current = self._states[mode]
        try:
            self._dll.write_smbus(0, config["addr"], SLAVE_ADDR, current)
        except Exception as e:
            raise ChargeModeError(f"Failed to toggle {config['name']}: {e}") from e

        self._states[mode] = not current
        return self._states[mode]

    @property
    def fast_charge_enabled(self) -> bool:
        return self._states[ChargeModeType.FAST_CHARGE]

    @property
    def night_charge_enabled(self) -> bool:
        return self._states[ChargeModeType.NIGHT_CHARGE]

    def is_enabled(self, mode: ChargeModeType) -> bool:
        return self._states[mode]

    def get_mode_name(self, mode: ChargeModeType) -> str:
        return MODE_CONFIG[mode]["name"]
