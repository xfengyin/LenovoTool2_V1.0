"""MainWindow ViewModel — 处理数据转换和状态管理。

负责：
- 会话统计数据的聚合与计算
- 电池数据的格式化与转换
- 充电模式状态管理
- 运行时状态追踪
"""

import logging
import time as _time
from typing import Optional

from PySide6.QtCore import QObject, Signal

from lenovo_tool.core.data_models import BatterySnapshot, AppConfig
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.services.data_acquisition import DataAcquisitionService
from lenovo_tool.services.charge_mode import ChargeModeService, ChargeModeType

logger = logging.getLogger(__name__)


class MainViewModel(QObject):
    data_updated = Signal(BatterySnapshot)
    session_stats_updated = Signal(dict)
    charge_mode_updated = Signal(bool, bool)

    def __init__(self, dll: DLLInterface, config: AppConfig) -> None:
        super().__init__()
        self._dll = dll
        self._config = config
        self._data_service = DataAcquisitionService(dll)
        self._charge_service = ChargeModeService(dll)

        self._start_time: float = 0.0
        self._sample_count: int = 0
        self._sum_voltage: float = 0.0
        self._sum_current: float = 0.0
        self._sum_temperature: float = 0.0
        self._sum_power: float = 0.0

        self._fast_charge_enabled: bool = False
        self._night_charge_enabled: bool = False

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def runtime(self) -> float:
        return _time.monotonic() - self._start_time if self._start_time > 0 else 0.0

    @property
    def fast_charge_enabled(self) -> bool:
        return self._fast_charge_enabled

    @property
    def night_charge_enabled(self) -> bool:
        return self._night_charge_enabled

    def start_session(self) -> None:
        self._start_time = _time.monotonic()
        self._sample_count = 0
        self._sum_voltage = 0.0
        self._sum_current = 0.0
        self._sum_temperature = 0.0
        self._sum_power = 0.0
        logger.info("监控会话已启动")

    def process_snapshot(self, snapshot: BatterySnapshot) -> None:
        self._sample_count += 1
        self._sum_voltage += snapshot.voltage
        self._sum_current += snapshot.current
        self._sum_temperature += snapshot.temperature
        power = abs(snapshot.voltage * snapshot.current) / 1_000_000
        self._sum_power += power

        self._update_charge_mode_state(snapshot.battery_mode)
        self.data_updated.emit(snapshot)
        self.session_stats_updated.emit(self._calculate_session_stats())

    def _update_charge_mode_state(self, battery_mode: int) -> None:
        self._fast_charge_enabled = bool(battery_mode & 0x01)
        self._night_charge_enabled = bool(battery_mode & 0x02)
        self.charge_mode_updated.emit(
            self._fast_charge_enabled,
            self._night_charge_enabled
        )

    def _calculate_session_stats(self) -> dict:
        n = self._sample_count
        if n == 0:
            return {}

        elapsed = self.runtime
        h, m, sec = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
        runtime_str = f"{h:02d}:{m:02d}:{sec:02d}"

        return {
            "sample_count": str(n),
            "avg_voltage": f"{self._sum_voltage / n:.0f} mV",
            "avg_current": f"{self._sum_current / n:.0f} mA",
            "avg_temperature": f"{self._sum_temperature / n:.1f} \u2103",
            "avg_power": f"{self._sum_power / n:.1f} W",
            "runtime": runtime_str,
        }

    def calculate_capacity_percentages(self, snapshot: BatterySnapshot) -> tuple:
        if snapshot.dc <= 0:
            return 0.0, 0.0

        fcc_pct = snapshot.fcc / snapshot.dc * 100
        rm_pct = snapshot.rm / snapshot.dc * 100
        return fcc_pct, rm_pct

    def format_charge_state(self, charge_state: str) -> tuple[str, str]:
        state_map = {
            "charging": ("充电中", "#00e676"),
            "discharging": ("放电中", "#ffab40"),
            "idle": ("待机", "#7a8fa3"),
            "full": ("已满", "#448aff"),
        }
        return state_map.get(charge_state, ("未知", "#7a8fa3"))

    def format_temperature_color(self, temperature: float) -> str:
        if temperature > 60:
            return "#ff5252"
        elif temperature > 45:
            return "#ffab40"
        return "#e0e8f0"

    def get_voltage_range_text(self, snapshot: BatterySnapshot) -> str:
        return f"{snapshot.min_voltage}-{snapshot.max_voltage}"

    def toggle_fast_charge(self) -> bool:
        try:
            new_state = self._charge_service.toggle(ChargeModeType.FAST_CHARGE)
            self._fast_charge_enabled = new_state
            logger.info("智能快充: %s", "开启" if new_state else "关闭")
            return new_state
        except Exception as e:
            logger.error("快充切换失败: %s", e)
            raise

    def toggle_night_charge(self) -> bool:
        try:
            new_state = self._charge_service.toggle(ChargeModeType.NIGHT_CHARGE)
            self._night_charge_enabled = new_state
            logger.info("夜间充电: %s", "开启" if new_state else "关闭")
            return new_state
        except Exception as e:
            logger.error("夜充切换失败: %s", e)
            raise

    def format_runtime(self) -> str:
        elapsed = self.runtime
        h, m, sec = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"

    def get_status_bar_text(self, snapshot: BatterySnapshot) -> str:
        return (
            f"采样 #{self._sample_count} \u2014 "
            f"{snapshot.timestamp.strftime('%H:%M:%S')} | "
            f"{snapshot.voltage}mV {snapshot.current}mA "
            f"{snapshot.temperature}\u2103 RSOC={snapshot.rsoc}%"
        )