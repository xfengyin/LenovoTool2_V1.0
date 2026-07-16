"""Thread-safe data acquisition service."""

from datetime import datetime
from typing import Any

from lenovo_tool.core.data_models import BatterySnapshot, CellVoltage
from lenovo_tool.core.interfaces import BatteryDataSource
from lenovo_tool.services.life_prediction import (
    predict_life_months,
)


class DataAcquisitionService:
    """Service that fetches battery data from hardware.

    Stateless — each call to fetch_snapshot() is independent.
    Tracks session-level statistics (peak temp, voltage range).
    """

    def __init__(self, datasource: BatteryDataSource) -> None:
        self._datasource = datasource
        self._session_max_temp: float = 0.0
        self._session_min_v: int = 99999
        self._session_max_v: int = 0

    @staticmethod
    def _parse_cell_voltages(raw: Any) -> CellVoltage | None:
        """将数据源中多种形态的 cell_voltages 统一为 CellVoltage 或 None。

        支持：
        - None / 缺失 → None
        - CellVoltage 实例 → 原样返回
        - 4 元 tuple/list → CellVoltage(...)
        - dict（含 cell1~cell4 键） → CellVoltage(...)
        其他形态返回 None，避免污染主流程。
        """
        if raw is None:
            return None
        if isinstance(raw, CellVoltage):
            return raw
        if isinstance(raw, (tuple, list)) and len(raw) >= 3:
            return CellVoltage(
                cell1=int(raw[0]),
                cell2=int(raw[1]),
                cell3=int(raw[2]),
                cell4=int(raw[3]) if len(raw) >= 4 else 0,
            )
        if isinstance(raw, dict):
            try:
                return CellVoltage(
                    cell1=int(raw.get("cell1", 0)),
                    cell2=int(raw.get("cell2", 0)),
                    cell3=int(raw.get("cell3", 0)),
                    cell4=int(raw.get("cell4", 0)),
                )
            except (TypeError, ValueError):
                return None
        return None

    def fetch_snapshot(self) -> BatterySnapshot:
        """Fetch all data and build an immutable snapshot."""
        data = self._datasource.read_all_main_registers()

        temp = round(data["temperature"], 1)
        voltage = data["voltage"]

        self._session_max_temp = max(
            self._session_max_temp, temp
        )
        self._session_min_v = min(self._session_min_v, voltage)
        self._session_max_v = max(self._session_max_v, voltage)

        # Determine charge state from current
        current = data["current"]
        if abs(current) < 100:
            charge_state = "idle"
        elif current < 0:
            charge_state = "discharging"
        else:
            charge_state = "charging"

        # === V3.0 扩展字段：向后兼容，老数据源不返回时退化为 None ===
        cell_voltages = self._parse_cell_voltages(
            data.get("cell_voltages")
        )
        fet_temperature_raw = data.get("fet_temperature")
        if fet_temperature_raw is None:
            fet_temperature: float | None = None
        else:
            try:
                fet_temperature = float(fet_temperature_raw)
            except (TypeError, ValueError):
                fet_temperature = None

        return BatterySnapshot(
            timestamp=datetime.now(),
            voltage=voltage,
            current=current,
            temperature=temp,
            rsoc=data["rsoc"],
            soh=data["soh"],
            fcc=data["fcc"],
            rm=data["rm"],
            dc=data["dc"],
            dv=data["dv"],
            battery_mode=data["battery_mode"],
            pl1=data["pl1"],
            pl2=data["pl2"],
            pl4=data["pl4"],
            predicted_life_months=predict_life_months(
                data["life_raw"]
            ),
            cycle_count=int(data.get("cycle_count", 0)),
            first_usage_time=str(
                self._datasource.get_first_usage_time()
            ),
            charge_state=charge_state,
            max_temperature=self._session_max_temp,
            min_voltage=self._session_min_v,
            max_voltage=self._session_max_v,
            cell_voltages=cell_voltages,
            fet_temperature=fet_temperature,
        )