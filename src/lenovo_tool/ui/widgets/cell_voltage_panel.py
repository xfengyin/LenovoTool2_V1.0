"""电芯电压监控面板 - 4 芯独立显示 + 压差分析 + 均衡状态。

设计要点：
- CellVoltagePanel：顶层容器，组合 4 个 CellBar + 状态摘要
- CellBar：单芯条形图，根据电压范围切换颜色（橙/青/红）
- 颜色阈值：<3700 mV 橙（欠压）、3700-4250 mV 绿/青（正常）、>4250 mV 红（过压）
- 性能：直接 QPainter 绘制，避免 setStyleSheet 频繁重解析
- 内存：仅保留必要状态（self._cells, self._displays），无多余对象复制
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
)

from lenovo_tool.core.data_models import CellVoltage
from lenovo_tool.ui.styles.main_style import (
    BG_PANEL_SOLID, BORDER_ACCENT,
    TEXT_LABEL, TEXT_VALUE, TEXT_SECONDARY,
    FONT_XS, FONT_SM,
    GLOW_CYAN, GLOW_GREEN, GLOW_ORANGE, GLOW_RED,
)


class CellVoltagePanel(QWidget):
    """4 芯电压条形图面板。

    布局：
    - 4 行 CellBar，每行：标签 + 进度条 + 数值
    - 底部 2x2 网格：压差 / 均衡状态 / 最低 / 最高
    """

    # 4 芯电压的有效量程：用于映射到 0-100% 进度
    _MIN_MV: int = 3000
    _MAX_MV: int = 4500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 仅缓存必要状态；使用 list 而非 tuple 保持可写以便 set_data 原地更新
        self._cells: list[int] = [0, 0, 0, 0]
        self.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 4 芯行
        self._rows: list[tuple[QLabel, "CellBar", QLabel]] = []
        for i in range(4):
            row = QHBoxLayout()
            row.setSpacing(6)
            label = QLabel(f"Cell {i+1}")
            label.setFixedWidth(40)
            label.setStyleSheet(
                f"color: {TEXT_LABEL}; font-size: {FONT_SM}px; "
                f"border: none; background: transparent;"
            )
            bar = CellBar(min_mv=self._MIN_MV, max_mv=self._MAX_MV)
            bar.setMinimumHeight(14)
            val = QLabel("-- mV")
            val.setFixedWidth(60)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: {FONT_SM}px; "
                f"font-weight: bold; font-family: Consolas, monospace; "
                f"border: none; background: transparent;"
            )
            row.addWidget(label)
            row.addWidget(bar, stretch=1)
            row.addWidget(val)
            layout.addLayout(row)
            self._rows.append((label, bar, val))

        # 分隔线
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_ACCENT}; border: none;")
        layout.addWidget(sep)

        # 压差/均衡状态
        info_layout = QGridLayout()
        info_layout.setSpacing(4)
        self._spread_lbl = QLabel("压差: -- mV")
        self._status_lbl = QLabel("均衡: --")
        self._min_lbl = QLabel("最低: --")
        self._max_lbl = QLabel("最高: --")
        for lbl in (self._spread_lbl, self._status_lbl, self._min_lbl, self._max_lbl):
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_XS}px; "
                f"border: none; background: transparent;"
            )
        info_layout.addWidget(self._spread_lbl, 0, 0)
        info_layout.addWidget(self._status_lbl, 0, 1)
        info_layout.addWidget(self._min_lbl, 1, 0)
        info_layout.addWidget(self._max_lbl, 1, 1)
        layout.addLayout(info_layout)

    def set_data(self, cell: CellVoltage | None) -> None:
        """更新 4 芯电压数据；cell 为 None 时跳过以保留上次显示。"""
        if cell is None:
            return
        cells = (cell.cell1, cell.cell2, cell.cell3, cell.cell4)
        self._cells = list(cells)
        for i, (label, bar, val) in enumerate(self._rows):
            mv = cells[i]
            bar.set_value(mv)
            val.setText(f"{mv} mV")

        # 颜色逻辑：按压差状态切换
        spread = cell.spread
        if spread < 30:
            spread_color = GLOW_GREEN
            status_text = "● 正常"
            status_color = GLOW_GREEN
        elif spread < 100:
            spread_color = GLOW_ORANGE
            status_text = "● 关注"
            status_color = GLOW_ORANGE
        else:
            spread_color = GLOW_RED
            status_text = "● 异常"
            status_color = GLOW_RED
        self._spread_lbl.setText(f"压差: {spread} mV")
        self._spread_lbl.setStyleSheet(
            f"color: {spread_color}; font-size: {FONT_XS}px; font-weight: bold; "
            f"border: none; background: transparent;"
        )
        self._status_lbl.setText(f"均衡: {status_text}")
        self._status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: {FONT_XS}px; font-weight: bold; "
            f"border: none; background: transparent;"
        )
        min_idx, min_v = cell.min_cell
        max_idx, max_v = cell.max_cell
        self._min_lbl.setText(f"最低: Cell{min_idx} ({min_v} mV)")
        self._max_lbl.setText(f"最高: Cell{max_idx} ({max_v} mV)")


class CellBar(QWidget):
    """单芯电压条形图，带颜色阈值（<3700 橙 / 正常青 / >4250 红）。"""

    # 颜色阈值（mV）
    _LOW_MV: int = 3700
    _HIGH_MV: int = 4250

    def __init__(
        self,
        parent: QWidget | None = None,
        min_mv: int = 3000,
        max_mv: int = 4500,
    ) -> None:
        super().__init__(parent)
        self._value: int = 0
        self._min_mv = min_mv
        self._max_mv = max_mv
        self.setMinimumHeight(14)

    def set_value(self, mv: int) -> None:
        """设置当前电压（mV），触发重绘。"""
        self._value = mv
        self.update()

    def _color_for(self, mv: int) -> str:
        """根据电压返回对应颜色 hex。"""
        if mv < self._LOW_MV:
            return GLOW_ORANGE
        if mv > self._HIGH_MV:
            return GLOW_RED
        return GLOW_CYAN

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        radius = 2.0

        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(BG_PANEL_SOLID))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # 填充：按比例映射到 0-100%
        span = self._max_mv - self._min_mv
        pct = max(0.0, min(100.0, (self._value - self._min_mv) / span * 100))
        if pct > 0:
            fill_w = w * pct / 100.0
            color = QColor(self._color_for(self._value))
            gradient = QLinearGradient(0, 0, fill_w, 0)
            gradient.setColorAt(0, color)
            light = QColor(color)
            light.setAlpha(180)
            gradient.setColorAt(1, light)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(0, 0, fill_w, h), radius, radius)

        painter.end()
