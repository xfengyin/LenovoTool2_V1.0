"""ChartWindow ViewModel — 管理图表数据状态。

负责：
- 图表历史数据的缓存与管理
- 数据点的聚合与清理
- 图表配置的管理
"""

import logging
from collections import deque
from typing import Deque, List, Tuple

from PySide6.QtCore import QObject, Signal

from lenovo_tool.core.data_models import BatterySnapshot, AppConfig

logger = logging.getLogger(__name__)


class ChartViewModel(QObject):
    data_updated = Signal(list)
    history_cleared = Signal()

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._max_points: int = int(
            config.chart_history_seconds * 1000 / config.poll_interval_ms
        )
        self._history: Deque[BatterySnapshot] = deque(maxlen=self._max_points)

    @property
    def history(self) -> Deque[BatterySnapshot]:
        return self._history

    @property
    def max_points(self) -> int:
        return self._max_points

    def add_snapshot(self, snapshot: BatterySnapshot) -> None:
        self._history.append(snapshot)
        self.data_updated.emit(list(self._history))

    def get_voltage_data(self) -> List[Tuple[float, int]]:
        return [(s.timestamp.timestamp(), s.voltage) for s in self._history]

    def get_current_data(self) -> List[Tuple[float, int]]:
        return [(s.timestamp.timestamp(), s.current) for s in self._history]

    def get_temperature_data(self) -> List[Tuple[float, float]]:
        return [(s.timestamp.timestamp(), s.temperature) for s in self._history]

    def get_fcc_data(self) -> List[Tuple[float, int]]:
        return [(s.timestamp.timestamp(), s.fcc) for s in self._history]

    def get_rm_data(self) -> List[Tuple[float, int]]:
        return [(s.timestamp.timestamp(), s.rm) for s in self._history]

    def clear_history(self) -> None:
        self._history.clear()
        self.history_cleared.emit()
        logger.info("图表历史已清空")

    def get_latest_snapshot(self) -> BatterySnapshot | None:
        return self._history[-1] if self._history else None