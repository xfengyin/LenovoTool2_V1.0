"""Comprehensive register data fetching service for the log window.

Consolidates the logic spread across LogWord.py, LogBlock.py, and
the log worker thread. Returns structured LogSnapshot objects.
"""

from datetime import datetime

from lenovo_tool.core.data_models import LogSnapshot
from lenovo_tool.core.interfaces import BatteryDataSource
from lenovo_tool.core.register_definitions import REGISTER_CATALOG, RegisterCategory, RegisterInfo


class LogDataService:
    """Reads ALL SMBus registers for the log window display."""

    def __init__(self, datasource: BatteryDataSource) -> None:
        self._datasource = datasource

    def fetch_log_snapshot(self) -> LogSnapshot:
        """Read all word and block registers in one pass."""
        values: dict[str, int | float | str] = {}
        units: dict[str, str] = {}

        for name, info in REGISTER_CATALOG.items():
            value = self._read_register(info)
            values[name] = value
            units[name] = info.unit

        return LogSnapshot(timestamp=datetime.now(), values=values, units=units)

    def _read_register(self, info: RegisterInfo) -> int | float | str:
        """Dispatch to the correct datasource read method based on register category."""
        match info.category:
            case RegisterCategory.WORD_INT:
                return self._datasource.read_int_word(info.address)
            case RegisterCategory.WORD_NEG:
                return self._datasource.read_neg_word(info.address)
            case RegisterCategory.WORD_HEX:
                raw = self._datasource.read_neg_word(info.address)
                return f"{raw & 0xFFFF:04x}"
            case RegisterCategory.TEMPERATURE:
                return round(self._datasource.get_temperature(info.address), 1)
            case RegisterCategory.MODE_BIT:
                result = self._datasource.read_smbus(0, info.address, 1, 0x16)
                return result.get("byte0", "00")
            case RegisterCategory.SMBUS_MESSAGE:
                return self._datasource.get_first_usage_time(info.address)
            case RegisterCategory.SOH_CALCULATED:
                return self._datasource.read_soh()
            case RegisterCategory.PREDICTED_HEX:
                return self._datasource.read_int_word(info.address)
            case RegisterCategory.BLOCK_SUBFIELD:
                return self._datasource.read_block(info.address, info.block_offset, info.block_length)
            case _:
                return self._datasource.read_int_word(info.address)
