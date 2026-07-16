"""Thread-safe data acquisition service."""

from datetime import datetime

from lenovo_tool.core.data_models import BatterySnapshot
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
        )