"""实时监控图表窗口 — 企业级监控大屏风格。

展示电压、电流、温度、功率、RSOC、SOH 6条实时曲线，
底部状态栏显示统计信息，整体深色主题一致。
"""

import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, Slot, QDateTime
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QWidget,
)

from lenovo_tool.core.data_models import AppConfig, BatterySnapshot
from lenovo_tool.ui.styles.main_style import (
    global_stylesheet, BG_CARD, BG_PRIMARY, BG_INPUT,
    BORDER_SUBTLE, CHART_GRID,
    TEXT_LABEL, TEXT_SECONDARY, TEXT_ACCENT, TEXT_PRIMARY,
    TEXT_VALUE, STATUS_GOOD, STATUS_WARN, STATUS_BAD,
)


class _StyledChart(QFrame):
    """单个带统计信息的实时折线图。"""

    def __init__(
        self,
        title,
        unit,
        y_range,
        line_color,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self._unit = unit
        self._line_color = line_color
        self._values = deque(maxlen=500)
        self._times = deque(maxlen=500)
        self._min_val = float("inf")
        self._max_val = float("-inf")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        # 顶部：标题 + 实时值 + 单位
        header = QHBoxLayout()
        header.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 12px; "
            f"font-weight: bold; border: none; "
            f"background: transparent;"
        )
        header.addWidget(title_lbl)
        header.addStretch()

        # 统计：min/max
        self._min_lbl = QLabel("MIN --")
        self._min_lbl.setStyleSheet(
            f"color: {STATUS_BAD}; font-size: 9px; "
            f"border: none; background: transparent;"
        )
        self._max_lbl = QLabel("MAX --")
        self._max_lbl.setStyleSheet(
            f"color: {STATUS_GOOD}; font-size: 9px; "
            f"border: none; background: transparent;"
        )
        header.addWidget(self._min_lbl)
        header.addWidget(self._max_lbl)

        self._value_lbl = QLabel("--")
        self._value_lbl.setStyleSheet(
            f"color: {line_color}; font-size: 20px; "
            f"font-weight: bold; "
            f"font-family: Consolas, monospace; "
            f"border: none; background: transparent;"
        )
        header.addWidget(self._value_lbl)

        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; "
            f"border: none; background: transparent;"
        )
        header.addWidget(unit_lbl)

        outer.addLayout(header)

        # 图表
        pg.setConfigOptions(antialias=True)
        self._plot = pg.PlotWidget()
        self._plot.setBackground(BG_INPUT)
        self._plot.setMinimumHeight(140)

        pi = self._plot.getPlotItem()
        if pi:
            pi.showGrid(x=True, y=True, alpha=0.1)
            for ax_name in ("bottom", "left"):
                axis = pi.getAxis(ax_name)
                axis.setPen(pg.mkPen(BORDER_SUBTLE, width=1))
                axis.setTextPen(
                    pg.mkPen(TEXT_SECONDARY, width=1)
                )
                axis.setFont(QFont("Consolas", 8))
            pi.hideAxis("top")
            pi.hideAxis("right")
            pi.setContentsMargins(2, 2, 2, 2)

        self._plot.setYRange(*y_range, padding=0.08)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()

        # 曲线 + 填充
        c = QColor(line_color)
        pen = pg.mkPen(line_color, width=2)
        brush = pg.mkBrush(
            QColor(c.red(), c.green(), c.blue(), 30)
        )
        self._curve = self._plot.plot(
            pen=pen, fillLevel=0, fillBrush=brush,
        )

        # 最新值标记点
        self._scatter = pg.ScatterPlotItem(
            size=8, pen=None,
            brush=pg.mkBrush(line_color),
        )
        self._plot.addItem(self._scatter)

        outer.addWidget(self._plot)

    def append(self, value):
        now = time.time()
        self._times.append(now)
        self._values.append(value)
        self._curve.setData(
            list(self._times), list(self._values)
        )
        if self._values:
            self._scatter.setData([now], [value])

        self._value_lbl.setText(f"{value:,.0f}")

        self._min_val = min(self._min_val, value)
        self._max_val = max(self._max_val, value)
        self._min_lbl.setText(f"MIN {self._min_val:,.0f}")
        self._max_lbl.setText(f"MAX {self._max_val:,.0f}")

    def clear_data(self):
        self._values.clear()
        self._times.clear()
        self._curve.clear()
        self._scatter.clear()
        self._value_lbl.setText("--")
        self._min_val = float("inf")
        self._max_val = float("-inf")
        self._min_lbl.setText("MIN --")
        self._max_lbl.setText("MAX --")


class ChartWindow(QDialog):
    """实时监控图表窗口 — 3x2 布局，6条曲线。"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._sample_count = 0
        self.setWindowTitle("实时监控 — 图表")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)
        self.setStyleSheet(global_stylesheet())
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # 顶部控制栏
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("📊 实时监控")
        title.setStyleSheet(
            f"color: {TEXT_ACCENT}; font-size: 16px; "
            f"font-weight: bold; border: none; "
            f"background: transparent;"
        )
        header.addWidget(title)

        header.addStretch()

        self._count_lbl = QLabel("采样: 0")
        self._count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; "
            f"border: none; background: transparent;"
        )
        header.addWidget(self._count_lbl)

        self._time_lbl = QLabel("--:--:--")
        self._time_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; "
            f"border: none; background: transparent;"
        )
        header.addWidget(self._time_lbl)

        clear_btn = QPushButton("🔄 清空数据")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)

        close_btn = QPushButton("✕ 关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        root.addLayout(header)

        # 3x2 图表网格
        grid = QGridLayout()
        grid.setSpacing(6)

        self._charts = []

        chart_specs = [
            ("电压", "mV", self._config.voltage_y_range, "#00e5c8"),
            ("电流", "mA", self._config.current_y_range, "#ffab40"),
            ("温度", "℃", (20, 60), "#e040fb"),
            ("功率", "W", (0, 80), "#ff5252"),
            ("RSOC", "%", (0, 105), "#448aff"),
            ("SOH", "%", (40, 105), "#00e676"),
        ]

        for idx, (title, unit, y_range, color) in enumerate(
            chart_specs
        ):
            chart = _StyledChart(
                title, unit, y_range, color
            )
            self._charts.append(chart)
            grid.addWidget(chart, idx // 3, idx % 3)

        root.addLayout(grid, stretch=1)

        # 底部信息栏
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        for text, color in [
            ("电压范围: --", "#00e5c8"),
            ("电流范围: --", "#ffab40"),
            ("温度峰值: --", "#e040fb"),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; "
                f"font-weight: bold; border: none; "
                f"background: transparent;"
            )
            bottom.addWidget(lbl)

        bottom.addStretch()
        root.addLayout(bottom)

    def _clear_all(self):
        for chart in self._charts:
            chart.clear_data()
        self._sample_count = 0
        self._count_lbl.setText("采样: 0")

    @Slot(BatterySnapshot)
    def on_snapshot(self, snapshot):
        self._sample_count += 1
        power = abs(snapshot.voltage * snapshot.current) / 1_000_000

        vals = [
            float(snapshot.voltage),
            float(snapshot.current),
            snapshot.temperature,
            round(power, 1),
            float(snapshot.rsoc),
            float(snapshot.soh),
        ]
        for chart, val in zip(self._charts, vals):
            chart.append(val)

        self._count_lbl.setText(
            f"采样: {self._sample_count}"
        )
        self._time_lbl.setText(
            snapshot.timestamp.strftime("%H:%M:%S")
        )
