"""通信诊断面板 - 展示 SMBus 通信质量指标。

组件结构：
- 主延迟条：渐变色按延迟区间变化（绿/橙/红）
- 2x2 网格：最大延迟 / 错误次数 / 错误率 / 连续成功
- 状态行：在线/离线 + 从机地址

设计原则：
- 纯展示组件：仅依赖 CommMetrics 不可变快照，无业务副作用
- 线程安全：依赖的 CommMetrics 为 frozen dataclass，跨线程安全
- 单一职责：仅渲染指标，不发起任何 IO
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
)

from lenovo_tool.core.data_models import CommMetrics
from lenovo_tool.ui.styles.main_style import (
    BORDER_ACCENT, BORDER_GLOW, BG_PANEL_SOLID,
    TEXT_LABEL, TEXT_VALUE, TEXT_SECONDARY,
    STATUS_GOOD, STATUS_WARN, STATUS_BAD,
    GLOW_CYAN, GLOW_GREEN, GLOW_ORANGE, GLOW_RED,
    FONT_XS, FONT_SM,
)

# SMBus 从机地址：与 ChargeMode.SLAVE_ADDR 保持一致
_SLAVE_ADDR_HEX = "0x16"

# 延迟区间阈值（ms）
_DELAY_GREEN_MAX = 50.0
_DELAY_ORANGE_MAX = 200.0
_DELAY_BAR_FULL = 500.0  # 进度条满刻度


def _color_for_delay(ms: float) -> str:
    """根据延迟返回 GLOW 颜色。"""
    if ms < _DELAY_GREEN_MAX:
        return GLOW_GREEN
    if ms < _DELAY_ORANGE_MAX:
        return GLOW_ORANGE
    return GLOW_RED


class _DelayBar(QWidget):
    """延迟条形图（0-500ms 范围，渐变填充）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value: float = 0.0
        self.setMinimumHeight(12)

    def set_value(self, ms: float) -> None:
        """更新延迟值并触发重绘。"""
        self._value = max(0.0, ms)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(BG_PANEL_SOLID))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 2, 2)

        # 填充（0-500ms 映射 0-100%）
        pct = min(100.0, self._value / _DELAY_BAR_FULL * 100.0)
        if pct > 0:
            fill_w = w * pct / 100.0
            color = QColor(_color_for_delay(self._value))
            gradient = QLinearGradient(0, 0, fill_w, 0)
            gradient.setColorAt(0, color)
            light = QColor(color)
            light.setAlpha(180)
            gradient.setColorAt(1, light)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(0, 0, fill_w, h), 2, 2)
        painter.end()


class CommDiagnosticsPanel(QWidget):
    """通信诊断面板：延迟/错误率/在线状态。

    使用方式：
        panel = CommDiagnosticsPanel()
        panel.set_data(comm_metrics)  # 每次采样后调用
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._metrics: CommMetrics | None = None
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 主延迟条
        delay_row = QHBoxLayout()
        delay_row.setSpacing(6)
        lbl = QLabel("采样延迟")
        lbl.setFixedWidth(60)
        lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )
        delay_row.addWidget(lbl)
        self._delay_bar = _DelayBar()
        self._delay_bar.setMinimumHeight(12)
        delay_row.addWidget(self._delay_bar, stretch=1)
        self._delay_val = QLabel("-- ms")
        self._delay_val.setFixedWidth(60)
        self._delay_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._delay_val.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: {FONT_SM}px; "
            f"font-weight: bold; font-family: Consolas, monospace; "
            f"border: none; background: transparent;"
        )
        delay_row.addWidget(self._delay_val)
        layout.addLayout(delay_row)

        # 详细指标 2x2 网格
        grid = QGridLayout()
        grid.setSpacing(6)
        self._max_lbl = QLabel("最大: -- ms")
        self._error_lbl = QLabel("错误: 0 次")
        self._rate_lbl = QLabel("错误率: 0.00%")
        self._success_lbl = QLabel("连续成功: 0")
        self._status_lbl = QLabel("\u25cf 在线")
        self._slave_lbl = QLabel(f"从机: {_SLAVE_ADDR_HEX}")
        for lbl in [
            self._max_lbl, self._error_lbl, self._rate_lbl,
            self._success_lbl, self._status_lbl, self._slave_lbl,
        ]:
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_XS}px; "
                f"border: none; background: transparent;"
            )
        grid.addWidget(self._max_lbl, 0, 0)
        grid.addWidget(self._error_lbl, 0, 1)
        grid.addWidget(self._rate_lbl, 1, 0)
        grid.addWidget(self._success_lbl, 1, 1)
        grid.addWidget(self._status_lbl, 2, 0)
        grid.addWidget(self._slave_lbl, 2, 1)
        layout.addLayout(grid)

    def set_data(self, metrics: CommMetrics | None) -> None:
        """更新面板数据。

        接受 None 时不更新（保留上一次状态），便于启动前占位。
        """
        if metrics is None:
            return
        self._metrics = metrics
        # 主延迟条
        self._delay_bar.set_value(metrics.avg_delay_ms)
        d_color = _color_for_delay(metrics.avg_delay_ms)
        self._delay_val.setText(f"{metrics.avg_delay_ms:.1f} ms")
        self._delay_val.setStyleSheet(
            f"color: {d_color}; font-size: {FONT_SM}px; "
            f"font-weight: bold; font-family: Consolas, monospace; "
            f"border: none; background: transparent;"
        )
        # 详细指标
        self._max_lbl.setText(f"最大: {metrics.max_delay_ms:.1f} ms")
        self._error_lbl.setText(f"错误: {metrics.error_count} 次")
        self._rate_lbl.setText(f"错误率: {metrics.error_rate:.2f}%")
        self._success_lbl.setText(f"连续成功: {metrics.consecutive_success}")
        # 在线/离线
        if metrics.is_online:
            self._status_lbl.setText("\u25cf 在线")
            self._status_lbl.setStyleSheet(
                f"color: {GLOW_GREEN}; font-size: {FONT_XS}px; font-weight: bold; "
                f"border: none; background: transparent;"
            )
        else:
            self._status_lbl.setText("\u25cf 离线")
            self._status_lbl.setStyleSheet(
                f"color: {GLOW_RED}; font-size: {FONT_XS}px; font-weight: bold; "
                f"border: none; background: transparent;"
            )
        # 从机地址固定展示
        self._slave_lbl.setText(f"从机: {_SLAVE_ADDR_HEX}")
