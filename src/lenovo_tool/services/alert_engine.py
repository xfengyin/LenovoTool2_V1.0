"""实时告警引擎。

基于 10 条预设规则的实时告警评估器，支持：
- 规则评估（数据驱动，每帧 BatterySnapshot 评估）
- 去抖控制（10 秒内不重复触发）
- 状态跟踪（活动/恢复）
- 视觉/声音/日志三种通道分发（通过 Qt Signal 解耦）
- 阈值可热更新
- 外部触发（ALM-08/09 由 DataWorker/MetricsService 主动调用）

设计原则：
- 开闭原则：新增规则仅在 ALERT_RULES 列表中追加，主流程不动。
- 单一职责：只负责告警评估与状态管理，UI 通知通过 Signal 解耦。
- 线程模型：evaluate() 必须在主线程或单一调用线程中调用；外部触发可跨线程（Qt 自动排队）。
"""

import logging
from datetime import datetime
from typing import Callable, Dict, List

from PySide6.QtCore import QObject, Signal

from lenovo_tool.core.data_models import AlertEvent, BatterySnapshot

logger = logging.getLogger(__name__)


# 告警规则定义
# 字段说明：
#   id: 规则唯一标识（ALM-01 ~ ALM-10）
#   level: 告警级别 "critical" | "warning"
#   check: 触发判定函数 (snapshot, threshold) -> bool
#   default_threshold: 默认阈值
#   message: 告警描述
#   ext_trigger: True 表示由外部触发（evaluate 时不评估）
ALERT_RULES: List[Dict] = [
    {
        "id": "ALM-01",
        "level": "critical",
        "check": lambda s, t: s.temperature > t,
        "default_threshold": 60.0,
        "message": "电芯温度过高",
    },
    {
        "id": "ALM-02",
        "level": "critical",
        "check": lambda s, t: s.fet_temperature is not None and s.fet_temperature > t,
        "default_threshold": 80.0,
        "message": "FET 温度过高",
    },
    {
        "id": "ALM-03",
        "level": "warning",
        "check": lambda s, t: s.soh < t,
        "default_threshold": 50.0,
        "message": "电池健康度低",
    },
    {
        "id": "ALM-04",
        "level": "warning",
        "check": lambda s, t: s.rsoc < t,
        "default_threshold": 20.0,
        "message": "剩余电量低",
    },
    {
        "id": "ALM-05",
        "level": "critical",
        "check": lambda s, t: s.dv > 0 and s.voltage > s.dv * t,
        "default_threshold": 1.05,
        "message": "电压异常（>设计电压×1.05）",
    },
    {
        "id": "ALM-06",
        "level": "warning",
        "check": lambda s, t: s.dv > 0 and s.voltage < s.dv * t,
        "default_threshold": 0.9,
        "message": "电压异常（<设计电压×0.9）",
    },
    {
        "id": "ALM-07",
        "level": "warning",
        "check": lambda s, t: s.cell_voltages is not None and s.cell_voltages.spread > t,
        "default_threshold": 50.0,
        "message": "电芯压差过大",
    },
    {
        "id": "ALM-08",
        "level": "warning",
        "check": lambda s, t: False,  # 由外部触发（MetricsService / DataWorker）
        "default_threshold": 200.0,
        "message": "采样延迟过高",
        "ext_trigger": True,
    },
    {
        "id": "ALM-09",
        "level": "critical",
        "check": lambda s, t: False,  # 由外部触发
        "default_threshold": 3,
        "message": "通信连续失败",
        "ext_trigger": True,
    },
    {
        "id": "ALM-10",
        "level": "warning",
        "check": lambda s, t: s.predicted_life_months < t,
        "default_threshold": 6,
        "message": "预测寿命不足",
    },
]


class AlertEngine(QObject):
    """实时告警引擎。

    评估入口：``evaluate(snapshot)``（数据驱动）
    外部触发：``trigger_external(alert_id, current_value)``（事件驱动）
    状态查询：``get_active()`` / ``get_active_count()``
    """

    # 新告警触发：携带 AlertEvent（含 level / current_value / threshold）
    alert_triggered = Signal(object)
    # 告警恢复：携带 alert_id + 恢复事件（recovered=True, recovery_time 已填）
    alert_recovered = Signal(str, object)
    # 活动告警列表变更：携带当前所有活动告警列表
    active_alerts_changed = Signal(list)

    def __init__(
        self,
        debounce_seconds: float = 10.0,
        sound_enabled: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._debounce_seconds = debounce_seconds
        self._sound_enabled = sound_enabled
        # 阈值表（可热更新）
        self._thresholds: Dict[str, float] = {
            r["id"]: r["default_threshold"] for r in ALERT_RULES
        }
        # 当前活动告警：alert_id -> AlertEvent
        self._active: Dict[str, AlertEvent] = {}
        # 最近一次触发时间（用于去抖）
        self._last_trigger_time: Dict[str, datetime] = {}

    # ============== 阈值/声音控制 ==============
    def set_threshold(self, alert_id: str, value: float) -> None:
        """热更新某条规则的阈值。"""
        self._thresholds[alert_id] = value

    def set_sound_enabled(self, enabled: bool) -> None:
        self._sound_enabled = enabled

    def is_sound_enabled(self) -> bool:
        return self._sound_enabled

    def get_thresholds(self) -> Dict[str, float]:
        """返回阈值副本，避免外部篡改。"""
        return dict(self._thresholds)

    # ============== 评估入口 ==============
    def evaluate(self, snapshot: BatterySnapshot) -> None:
        """评估一个 BatterySnapshot，逐条规则判定。

        命中：创建 AlertEvent → 推送 alert_triggered → 记录活动状态
        恢复：从活动表移除 → 推送 alert_recovered
        去抖：同一 alert_id 在 debounce_seconds 内不重复触发。
        """
        now = datetime.now()
        any_change = False

        for rule in ALERT_RULES:
            # 外部触发的规则不在 evaluate 中评估
            if rule.get("ext_trigger"):
                continue

            alert_id = rule["id"]
            threshold = self._thresholds[alert_id]
            try:
                triggered: bool = bool(rule["check"](snapshot, threshold))
            except Exception as e:
                # 规则评估异常不应阻塞其它规则；记录但跳过
                logger.debug("规则 %s 评估异常: %s", alert_id, e)
                triggered = False

            if triggered:
                if alert_id in self._active:
                    # 仍在活动状态：仅更新 current_value，不重复触发事件
                    self._active[alert_id] = self._active[alert_id]
                    continue
                last = self._last_trigger_time.get(alert_id)
                if last and (now - last).total_seconds() < self._debounce_seconds:
                    # 去抖窗口内：忽略
                    continue

                event = AlertEvent(
                    alert_id=alert_id,
                    level=rule["level"],
                    message=rule["message"],
                    current_value=self._extract_value(snapshot, alert_id),
                    threshold=threshold,
                    timestamp=now,
                )
                self._active[alert_id] = event
                self._last_trigger_time[alert_id] = now
                logger.warning(
                    "ALERT TRIGGERED: %s [%s] %s value=%.2f threshold=%.2f",
                    alert_id, rule["level"], rule["message"],
                    event.current_value, threshold,
                )
                self.alert_triggered.emit(event)
                any_change = True
            else:
                if alert_id in self._active:
                    old_event = self._active.pop(alert_id)
                    recovery = AlertEvent(
                        alert_id=old_event.alert_id,
                        level=old_event.level,
                        message=old_event.message,
                        current_value=old_event.current_value,
                        threshold=old_event.threshold,
                        timestamp=old_event.timestamp,
                        recovered=True,
                        recovery_time=now,
                    )
                    logger.info("ALERT RECOVERED: %s", alert_id)
                    self.alert_recovered.emit(alert_id, recovery)
                    any_change = True

        if any_change:
            self.active_alerts_changed.emit(list(self._active.values()))

    # ============== 外部触发（ALM-08/09） ==============
    def trigger_external(self, alert_id: str, current_value: float) -> None:
        """由外部组件（如 DataWorker/MetricsService）主动触发某条规则。"""
        rule = next((r for r in ALERT_RULES if r["id"] == alert_id), None)
        if rule is None:
            logger.warning("trigger_external 未知告警 id: %s", alert_id)
            return
        now = datetime.now()
        last = self._last_trigger_time.get(alert_id)
        if last and (now - last).total_seconds() < self._debounce_seconds:
            return
        if alert_id in self._active:
            return

        event = AlertEvent(
            alert_id=alert_id,
            level=rule["level"],
            message=rule["message"],
            current_value=current_value,
            threshold=self._thresholds[alert_id],
            timestamp=now,
        )
        self._active[alert_id] = event
        self._last_trigger_time[alert_id] = now
        logger.warning(
            "ALERT EXTERNAL: %s [%s] %s value=%.2f",
            alert_id, rule["level"], rule["message"], current_value,
        )
        self.alert_triggered.emit(event)
        self.active_alerts_changed.emit(list(self._active.values()))

    def recover_external(self, alert_id: str) -> None:
        """由外部组件主动声明某条规则已恢复。"""
        if alert_id not in self._active:
            return
        old_event = self._active.pop(alert_id)
        recovery = AlertEvent(
            alert_id=old_event.alert_id,
            level=old_event.level,
            message=old_event.message,
            current_value=old_event.current_value,
            threshold=old_event.threshold,
            timestamp=old_event.timestamp,
            recovered=True,
            recovery_time=datetime.now(),
        )
        logger.info("ALERT RECOVERED (external): %s", alert_id)
        self.alert_recovered.emit(alert_id, recovery)
        self.active_alerts_changed.emit(list(self._active.values()))

    # ============== 查询接口 ==============
    def get_active(self) -> List[AlertEvent]:
        return list(self._active.values())

    def get_active_count(self) -> int:
        return len(self._active)

    def get_active_ids(self) -> List[str]:
        return list(self._active.keys())

    def has_critical(self) -> bool:
        """是否存在 critical 级别活动告警（用于 UI 状态颜色切换）。"""
        return any(e.level == "critical" for e in self._active.values())

    def clear_all(self) -> None:
        """清空所有活动告警（全部以恢复事件形式发出）。"""
        ids = list(self._active.keys())
        for aid in ids:
            self.recover_external(aid)

    # ============== 内部辅助 ==============
    def _extract_value(self, snapshot: BatterySnapshot, alert_id: str) -> float:
        """从 snapshot 中提取对应规则的当前值，用于事件 current_value 字段。"""
        if alert_id == "ALM-01":
            return float(snapshot.temperature)
        if alert_id == "ALM-02":
            return float(snapshot.fet_temperature) if snapshot.fet_temperature is not None else 0.0
        if alert_id == "ALM-03":
            return float(snapshot.soh)
        if alert_id == "ALM-04":
            return float(snapshot.rsoc)
        if alert_id == "ALM-05":
            return float(snapshot.voltage)
        if alert_id == "ALM-06":
            return float(snapshot.voltage)
        if alert_id == "ALM-07":
            return float(snapshot.cell_voltages.spread) if snapshot.cell_voltages else 0.0
        if alert_id == "ALM-10":
            return float(snapshot.predicted_life_months)
        return 0.0
