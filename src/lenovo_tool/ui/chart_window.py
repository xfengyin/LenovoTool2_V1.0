"""实时监控图表窗口 — 企业级监控大屏风格。

展示 10 条实时曲线（电压/电流/温度/功率/RSOC/SOH/FCC/RM/电芯压差/FET 温度），
底部状态栏显示统计信息，整体深色主题一致。

V3.0 变更：
- 4×3 网格，10 条曲线（保留原有 6 条 + 新增 FCC/RM/电芯压差/FET 温度 4 条）
- 修复 BUG-03：底部 3 个信息栏接入会话级极值
- 新增 CSV 导出按钮
"""

import csv
import time
from collections import deque
from datetime import datetime

import pyqtgraph as pg
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QFileDialog, QMessageBox,
)

from lenovo_tool.core.data_models import AppConfig, BatterySnapshot
from lenovo_tool.ui.styles.main_style import (
    global_stylesheet, BG_CARD, BG_PRIMARY, BG_INPUT,
    BORDER_SUBTLE, CHART_GRID,
    TEXT_LABEL, TEXT_SECONDARY, TEXT_ACCENT, TEXT_PRIMARY,
    TEXT_VALUE, STATUS_GOOD, STATUS_WARN, STATUS_BAD,
)


class _StyledChart(QFrame):
    """单个带统计信息的实时折线图，支持会话级极值追踪。

    关键能力：
    - 内部以 ring buffer 缓存最近 500 个点
    - 统一对外接口 `add_point(value)`（同时保留 `append` 兼容老代码）
    - 维护会话级极值（_min_v/_max_v/_min_a/_max_a/_max_temp/_sample_count），
      任何曲线都会更新 _sample_count，仅电压/电流/温度三类曲线会刷新对应极值
    - `get_session_stats()` 返回标准 dict，便于底部信息栏聚合展示
    """

    def __init__(
        self,
        name: str,
        title: str,
        unit: str,
        y_range: tuple[float, float],
        line_color: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        # === 标识 / 元数据 ===
        self.name = name          # CSV 列名标识（voltage / current / ...）
        self._unit = unit
        self._line_color = line_color

        # === 滑动窗口数据（500 点 ring buffer）===
        self._values: deque = deque(maxlen=500)
        self._times: deque = deque(maxlen=500)

        # === 曲线内显式 min/max（与 UI 显示对应）===
        self._min_val: float = float("inf")
        self._max_val: float = float("-inf")

        # === 会话级极值（BUG-03 修复：用于底部信息栏聚合）===
        # 任何曲线都更新 _sample_count；只有当 self.name 与字段对应时才刷新极值
        self._min_v: float = float("inf")
        self._max_v: float = float("-inf")
        self._min_a: float = float("inf")
        self._max_a: float = float("-inf")
        self._max_temp: float = float("-inf")
        self._sample_count: int = 0

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

    # ------------------------------------------------------------------
    # 数据写入
    # ------------------------------------------------------------------
    def add_point(self, value: float) -> None:
        """新增一个数据点（统一接口，CSV 导出与新代码请用此方法）。"""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return  # 非法值直接忽略，避免污染主流程

        now = time.time()
        self._times.append(now)
        self._values.append(v)
        self._curve.setData(list(self._times), list(self._values))
        if self._values:
            self._scatter.setData([now], [v])

        self._value_lbl.setText(f"{v:,.0f}")

        # 曲线内显式 min/max
        if v < self._min_val:
            self._min_val = v
        if v > self._max_val:
            self._max_val = v
        self._min_lbl.setText(f"MIN {self._min_val:,.0f}")
        self._max_lbl.setText(f"MAX {self._max_val:,.0f}")

        # 会话级极值（BUG-03 修复）
        self._sample_count += 1
        if self.name == "voltage":
            if v < self._min_v:
                self._min_v = v
            if v > self._max_v:
                self._max_v = v
        elif self.name == "current":
            if v < self._min_a:
                self._min_a = v
            if v > self._max_a:
                self._max_a = v
        elif self.name == "temperature":
            if v > self._max_temp:
                self._max_temp = v

    # 向后兼容的旧接口（保留以防外部调用方仍在使用）
    def append(self, value: float) -> None:
        self.add_point(value)

    def clear_data(self) -> None:
        """清空全部数据并重置会话极值。"""
        self._values.clear()
        self._times.clear()
        self._curve.clear()
        self._scatter.clear()
        self._value_lbl.setText("--")
        self._min_val = float("inf")
        self._max_val = float("-inf")
        self._min_lbl.setText("MIN --")
        self._max_lbl.setText("MAX --")

        # 会话级极值重置
        self._min_v = float("inf")
        self._max_v = float("-inf")
        self._min_a = float("inf")
        self._max_a = float("-inf")
        self._max_temp = float("-inf")
        self._sample_count = 0

    # ------------------------------------------------------------------
    # 会话级统计聚合（BUG-03 修复数据源）
    # ------------------------------------------------------------------
    def get_session_stats(self) -> dict[str, float | int | str]:
        """返回当前图表的会话级极值统计。

        字段：
        - name: 曲线标识
        - sample_count: 累计样本数
        - min_v / max_v: 仅当 name == 'voltage' 时有有效值
        - min_a / max_a: 仅当 name == 'current' 时有有效值
        - max_temp:       仅当 name == 'temperature' 时有有效值
        """
        return {
            "name": self.name,
            "sample_count": self._sample_count,
            "min_v": self._min_v,
            "max_v": self._max_v,
            "min_a": self._min_a,
            "max_a": self._max_a,
            "max_temp": self._max_temp,
        }

    @property
    def timestamps(self) -> list[float]:
        """暴露时间戳序列（用于 CSV 导出）。"""
        return list(self._times)

    @property
    def values_list(self) -> list[float]:
        """暴露数值序列（用于 CSV 导出）。"""
        return list(self._values)


class ChartWindow(QDialog):
    """实时监控图表窗口 — 4×3 布局，10 条曲线。"""

    # CSV 列顺序与 _charts 列表中曲线 name 一一对应
    _CSV_HEADERS: tuple[str, ...] = (
        "timestamp",
        "voltage", "current", "temperature", "power",
        "rsoc", "soh", "fcc", "rm",
        "cell_spread", "fet_temp",
    )

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._sample_count = 0
        self.setWindowTitle("实时监控 — 图表")
        self.setMinimumSize(1280, 820)
        self.resize(1400, 880)
        self.setStyleSheet(global_stylesheet())
        self._init_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
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

        # === V3.0 新增：CSV 导出按钮 ===
        export_btn = QPushButton("💾 导出CSV")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._on_export_csv)
        header.addWidget(export_btn)

        clear_btn = QPushButton("🔄 清空数据")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)

        close_btn = QPushButton("✕ 关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        root.addLayout(header)

        # 4×3 图表网格（10 条曲线：6 原有 + 4 新增）
        grid = QGridLayout()
        grid.setSpacing(6)

        # 保留原有 6 条 + 新增 4 条 = 10 条
        chart_specs = [
            # name,        title,   unit,  y_range,                    color
            ("voltage",     "电压",   "mV", self._config.voltage_y_range, "#00e5c8"),
            ("current",     "电流",   "mA", self._config.current_y_range, "#ffab40"),
            ("temperature", "温度",   "℃",  (20, 60),                   "#e040fb"),
            ("power",       "功率",   "W",  (0, 80),                    "#ff5252"),
            ("rsoc",        "RSOC",   "%",  (0, 105),                   "#448aff"),
            ("soh",         "SOH",    "%",  (40, 105),                  "#00e676"),
            # === V3.0 新增 4 条 ===
            ("fcc",         "FCC",    "mAh", self._config.fcc_y_range,  "#00e5ff"),
            ("rm",          "RM",     "mAh", self._config.rm_y_range,   "#3388ff"),
            ("cell_spread", "电芯压差", "mV", (0, 200),                  "#ffaa00"),
            ("fet_temp",    "FET 温度", "℃", (0, 120),                  "#aa55ff"),
        ]

        # 用 name→chart 的字典保存引用，便于按名字查询（如 CSV 导出、底部信息栏）
        self._charts: list[_StyledChart] = []
        self._chart_by_name: dict[str, _StyledChart] = {}

        for idx, (name, c_title, unit, y_range, color) in enumerate(chart_specs):
            chart = _StyledChart(
                name=name, title=c_title, unit=unit,
                y_range=y_range, line_color=color,
            )
            self._charts.append(chart)
            self._chart_by_name[name] = chart
            # 4 列 × 2 行 = 8 个位置；多于 8 时按 4 列继续向下扩展
            grid.addWidget(chart, idx // 4, idx % 4)

        root.addLayout(grid, stretch=1)

        # 底部信息栏（BUG-03 修复：保存 QLabel 引用并实时更新）
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        # 使用占位文本与颜色，文字会在 on_snapshot 中实时刷新
        self._lbl_v_range = QLabel("电压范围: --")
        self._lbl_a_range = QLabel("电流范围: --")
        self._lbl_max_temp = QLabel("温度峰值: --")

        for lbl, color in [
            (self._lbl_v_range, "#00e5c8"),
            (self._lbl_a_range, "#ffab40"),
            (self._lbl_max_temp, "#e040fb"),
        ]:
            lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; "
                f"font-weight: bold; border: none; "
                f"background: transparent;"
            )
            bottom.addWidget(lbl)

        bottom.addStretch()
        root.addLayout(bottom)

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def _clear_all(self) -> None:
        for chart in self._charts:
            chart.clear_data()
        self._sample_count = 0
        self._count_lbl.setText("采样: 0")
        # BUG-03：清空后底部信息栏回到占位
        self._lbl_v_range.setText("电压范围: --")
        self._lbl_a_range.setText("电流范围: --")
        self._lbl_max_temp.setText("温度峰值: --")

    def _on_export_csv(self) -> None:
        """导出 8 条曲线当前缓冲的数据为 CSV（按时间戳对齐）。"""
        default_name = (
            f"battery_chart_"
            f"{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "导出图表数据", default_name, "CSV files (*.csv)"
        )
        if not path:
            return

        # 合并所有曲线的 t/v 对到按时间戳秒级对齐的字典
        aligned: dict[str, dict[str, float]] = {}
        for chart in self._charts:
            for ts, val in zip(chart.timestamps, chart.values_list):
                ts_key = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                aligned.setdefault(ts_key, {})[chart.name] = val

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(list(self._CSV_HEADERS))
                for ts_key in sorted(aligned.keys()):
                    row = aligned[ts_key]
                    writer.writerow(
                        [ts_key]
                        + [row.get(n, "") for n in self._CSV_HEADERS[1:]]
                    )
        except OSError as exc:
            QMessageBox.critical(
                self, "导出失败", f"无法写入 CSV 文件：\n{exc}"
            )
            return

        QMessageBox.information(
            self, "导出完成",
            f"已导出 {len(aligned)} 条采样点至：\n{path}",
        )

    # ------------------------------------------------------------------
    # 数据接入
    # ------------------------------------------------------------------
    @Slot(BatterySnapshot)
    def on_snapshot(self, snapshot: BatterySnapshot) -> None:
        self._sample_count += 1
        power = abs(snapshot.voltage * snapshot.current) / 1_000_000

        # === 原有 6 条 ===
        self._chart_by_name["voltage"].add_point(float(snapshot.voltage))
        self._chart_by_name["current"].add_point(float(snapshot.current))
        self._chart_by_name["temperature"].add_point(snapshot.temperature)
        self._chart_by_name["power"].add_point(round(power, 1))
        self._chart_by_name["rsoc"].add_point(float(snapshot.rsoc))
        self._chart_by_name["soh"].add_point(float(snapshot.soh))

        # === V3.0 新增 4 条 ===
        self._chart_by_name["fcc"].add_point(float(snapshot.fcc))
        self._chart_by_name["rm"].add_point(float(snapshot.rm))

        if snapshot.cell_voltages is not None:
            self._chart_by_name["cell_spread"].add_point(
                float(snapshot.cell_voltages.spread)
            )
        if snapshot.fet_temperature is not None:
            self._chart_by_name["fet_temp"].add_point(
                float(snapshot.fet_temperature)
            )

        # 顶部信息
        self._count_lbl.setText(f"采样: {self._sample_count}")
        self._time_lbl.setText(snapshot.timestamp.strftime("%H:%M:%S"))

        # === BUG-03 修复：底部 3 个 QLabel 实时刷新 ===
        v_stats = self._chart_by_name["voltage"].get_session_stats()
        a_stats = self._chart_by_name["current"].get_session_stats()
        t_stats = self._chart_by_name["temperature"].get_session_stats()

        if v_stats["sample_count"] > 0:
            self._lbl_v_range.setText(
                f"电压范围: {v_stats['min_v']:,.0f} ~ "
                f"{v_stats['max_v']:,.0f} mV"
            )
        if a_stats["sample_count"] > 0:
            self._lbl_a_range.setText(
                f"电流范围: {a_stats['min_a']:,.0f} ~ "
                f"{a_stats['max_a']:,.0f} mA"
            )
        if t_stats["sample_count"] > 0:
            self._lbl_max_temp.setText(
                f"温度峰值: {t_stats['max_temp']:.1f} ℃"
            )
