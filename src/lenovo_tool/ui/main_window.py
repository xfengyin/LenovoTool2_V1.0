"""电池监控大屏 — 主窗口模块。

提供高密度企业级监控仪表板界面，实时展示电池各项指标。
3列布局：左列（仪表盘+环形指标+运行状态）、
中列（电池图标+容量条+电芯+功率+会话）、
右列（参数表+寿命预测+充电模式）。
"""

import logging
import math
import random as _random
import time as _time

from PySide6.QtCore import Qt, QRectF, Slot, QPoint, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPolygon,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QLabel, QPushButton,
    QSizePolicy, QStatusBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from lenovo_tool.core.data_models import AppConfig, BatterySnapshot
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.services.data_acquisition import DataAcquisitionService
from lenovo_tool.services.charge_mode import (
    ChargeModeService, ChargeModeType,
)
from lenovo_tool.ui.chart_window import ChartWindow
from lenovo_tool.ui.dialogs.error_dialog import show_error
from lenovo_tool.ui.styles.main_style import (
    global_stylesheet, TEXT_ACCENT, TEXT_SECONDARY,
    TEXT_LABEL, TEXT_PRIMARY, TEXT_VALUE,
    BG_CARD, BG_INPUT, BORDER_SUBTLE,
    STATUS_GOOD, STATUS_WARN, STATUS_BAD,
)
from lenovo_tool.ui.widgets.lcd_display import LCDDisplay
from lenovo_tool.ui.widgets.ring_indicator import RingIndicator
from lenovo_tool.ui.widgets.status_badge import StatusBadge
from lenovo_tool.ui.workers.data_worker import DataWorker

logger = logging.getLogger(__name__)


def _card(title=None):
    card = QFrame()
    card.setObjectName("Card")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    if title:
        header = QFrame()
        header.setObjectName("CardHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 3, 10, 3)
        lbl = QLabel(title)
        lbl.setObjectName("SectionTitle")
        hl.addWidget(lbl)
        outer.addWidget(header)
    body = QVBoxLayout()
    body.setContentsMargins(6, 3, 6, 3)
    body.setSpacing(2)
    outer.addLayout(body)
    return card, body


def _make_label(text, size=11, color=TEXT_LABEL, bold=False):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; "
        f"font-weight: {weight}; border: none; "
        f"background: transparent;"
    )
    return lbl


def _separator():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("background-color: #2a3f55; max-height: 1px;")
    return line


class HalfGaugeWidget(QWidget):
    """半圆仪表盘：显示预计可用寿命（月）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = 36
        self.setMinimumSize(200, 140)

    def setValue(self, v):
        self._value = max(0, min(self._max, v))
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # === 布局参数 ===
        title_h = 16
        bottom_margin = 20
        arc_area_top = title_h + 4
        arc_area_bottom = h - bottom_margin
        cx = w / 2
        max_r_by_w = (w / 2) - 24
        max_r_by_h = (arc_area_bottom - arc_area_top) / 2 - 4
        radius = min(max_r_by_w, max_r_by_h)
        cy = arc_area_top + radius

        # === 1. 标题 ===
        painter.setPen(QColor("#7a8fa3"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            QRectF(0, 4, w, title_h),
            Qt.AlignCenter, "预计可用寿命"
        )

        # === 2. 背景弧 ===
        arc_pen_w = radius * 0.14
        bg_pen = QPen(QColor("#1a2a3a"), arc_pen_w)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        arc_rect = QRectF(cx - radius, cy - radius,
                          radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 180 * 16)

        # === 3. 彩色进度弧 ===
        ratio = (self._value / self._max
                 if self._max > 0 else 0)
        green_end = 0.33
        blue_end = 0.66
        total_span = int(ratio * 180 * 16)

        def _arc(color, start16, span16):
            p = QPen(QColor(color), arc_pen_w)
            p.setCapStyle(Qt.RoundCap)
            painter.setPen(p)
            painter.drawArc(arc_rect, start16, span16)

        if ratio <= green_end:
            _arc("#00e676", 180 * 16, -total_span)
        elif ratio <= blue_end:
            _arc("#00e676", 180 * 16,
                 -int(green_end * 180 * 16))
            _arc("#448aff",
                 int((1 - green_end) * 180 * 16),
                 -int((ratio - green_end) * 180 * 16))
        else:
            _arc("#00e676", 180 * 16,
                 -int(green_end * 180 * 16))
            _arc("#448aff",
                 int((1 - green_end) * 180 * 16),
                 -int((blue_end - green_end) * 180 * 16))
            _arc("#ff5252",
                 int((1 - blue_end) * 180 * 16),
                 -(total_span - int(blue_end * 180 * 16)))

        # === 4. 指针 ===
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-(180 - ratio * 180))
        p_len = radius * 0.72
        painter.setPen(QPen(QColor("#00e5c8"), 2))
        painter.drawLine(0, 0, 0, -int(p_len))
        painter.setBrush(QColor("#00e5c8"))
        painter.setPen(Qt.NoPen)
        dr = max(3, radius * 0.04)
        painter.drawEllipse(QPointF(0, -int(p_len)),
                            dr, dr)
        painter.restore()

        # === 5. 刻度标签（弧外侧） ===
        labels = ["0M", "6M", "12M", "18M",
                  "24M", "30M", "36M"]
        painter.setFont(QFont("Segoe UI", 7))
        lbl_off = arc_pen_w / 2 + 10
        for i, lbl in enumerate(labels):
            a = 180 - i * 30
            rad = math.radians(a)
            lx = cx + (radius + lbl_off) * math.cos(rad)
            ly = cy - (radius + lbl_off) * math.sin(rad)
            painter.setPen(QColor("#5a6a7a"))
            painter.drawText(
                QRectF(lx - 14, ly - 7, 28, 14),
                Qt.AlignCenter, lbl
            )

        # === 6. 中心数值 + 单位 ===
        painter.setPen(QColor("#00e5c8"))
        vf = QFont("Consolas",
                    max(16, int(radius * 0.38)))
        vf.setBold(True)
        painter.setFont(vf)
        painter.drawText(
            QRectF(cx - 45, cy - radius * 0.32,
                   90, radius * 0.4),
            Qt.AlignCenter, str(self._value)
        )
        painter.setPen(QColor("#5a6a7a"))
        painter.setFont(
            QFont("Segoe UI",
                  max(9, int(radius * 0.14))))
        painter.drawText(
            QRectF(cx - 20, cy + radius * 0.1,
                   40, 16),
            Qt.AlignCenter, "月"
        )
        painter.end()


class BatteryIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rsoc = 0
        self._charge_state = "idle"
        self.setFixedSize(110, 130)

    def set_data(self, rsoc, charge_state):
        self._rsoc = max(0, min(100, rsoc))
        self._charge_state = charge_state
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bx = w * 0.15
        by = h * 0.18
        bw = w * 0.7
        bh = h * 0.72
        painter.setPen(QPen(QColor("#2a3f55"), 2))
        painter.setBrush(QColor("#1a2a3a"))
        head_w = bw * 0.35
        head_h = bh * 0.08
        painter.drawRoundedRect(QRectF(bx + bw / 2 - head_w / 2, by - head_h, head_w, head_h), 3, 3)
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), 6, 6)
        margin = 4
        level_h = (bh - margin * 2) * self._rsoc / 100
        level_y = by + bh - margin - level_h
        if self._rsoc > 60:
            level_color = QColor("#00e676")
        elif self._rsoc > 30:
            level_color = QColor("#ffab40")
        else:
            level_color = QColor("#ff5252")
        gradient = QLinearGradient(0, level_y, 0, by + bh)
        gradient.setColorAt(0, level_color)
        gradient.setColorAt(1, QColor(level_color.red() * 0.6, level_color.green() * 0.6, level_color.blue() * 0.6))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(bx + margin, level_y, bw - margin * 2, level_h), 3, 3)
        if self._charge_state == "charging":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#ffab40"))
            pcx = w / 2
            pcy = by + bh * 0.45
            pts = QPolygon([QPoint(int(pcx - 3), int(pcy - 15)), QPoint(int(pcx + 5), int(pcy - 2)), QPoint(int(pcx), int(pcy - 2)), QPoint(int(pcx + 3), int(pcy + 12)), QPoint(int(pcx - 5), int(pcy + 1)), QPoint(int(pcx), int(pcy + 1))])
            painter.drawPolygon(pts)
        painter.setPen(QColor("#e0e8f0"))
        pct_font = QFont("Consolas", 16)
        pct_font.setBold(True)
        painter.setFont(pct_font)
        painter.drawText(QRectF(bx, by + bh * 0.3, bw, bh * 0.4), Qt.AlignCenter, f"{self._rsoc}%")
        painter.end()


class LifePredictionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = 36

    def setValue(self, v):
        self._value = max(0, min(self._max, v))
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("#7a8fa3"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(0, 4, w, 16), Qt.AlignCenter, "预计可用寿命")
        painter.setPen(QColor("#00e5c8"))
        num_font = QFont("Consolas", 32)
        num_font.setBold(True)
        painter.setFont(num_font)
        painter.drawText(QRectF(0, 22, w, 46), Qt.AlignCenter, str(self._value))
        painter.setPen(QColor("#7a8fa3"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QRectF(0, 62, w, 16), Qt.AlignCenter, "月")
        bar_y = 82
        bar_h = 8
        bar_m = 12
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1a2a3a"))
        painter.drawRoundedRect(QRectF(bar_m, bar_y, w - bar_m * 2, bar_h), 4, 4)
        ratio = self._value / self._max if self._max > 0 else 0
        fill_w = (w - bar_m * 2) * ratio
        gradient = QLinearGradient(bar_m, 0, bar_m + fill_w, 0)
        gradient.setColorAt(0, QColor("#00e676"))
        gradient.setColorAt(1, QColor("#448aff"))
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(bar_m, bar_y, max(fill_w, 2), bar_h), 4, 4)
        painter.setPen(QColor("#5a6a7a"))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(QRectF(bar_m, bar_y + bar_h + 2, 30, 12), Qt.AlignLeft, "0月")
        painter.drawText(QRectF(w - bar_m - 30, bar_y + bar_h + 2, 30, 12), Qt.AlignRight, "36月")
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, dll, config, parent=None):
        super().__init__(parent)
        self._dll = dll
        self._config = config
        self._data_service = DataAcquisitionService(dll)
        self._charge_service = ChargeModeService(dll)
        self._worker = None
        self._chart_window = None
        self._log_window = None
        self._start_time = 0.0
        self._sample_count = 0
        self._sum_voltage = 0.0
        self._sum_current = 0.0
        self._sum_temperature = 0.0
        self._sum_power = 0.0
        self._init_ui()
        self._set_fixed_size()
        self.setStyleSheet(global_stylesheet())
        logger.info("主窗口初始化完成")

    def _set_fixed_size(self):
        self.setFixedSize(self._config.window_width, self._config.window_height)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 4, 6, 3)
        root.setSpacing(4)
        root.addLayout(self._build_control_bar())
        root.addWidget(self._build_main_area(), stretch=1)
        root.addLayout(self._build_bottom_bar())
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪 — 等待开始监控")

    def _build_control_bar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        self._start_btn = QPushButton("\u25b6 \u5f00\u59cb\u76d1\u63a7")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.clicked.connect(self._start_monitoring)
        self._stop_btn = QPushButton("\u25a0 \u7ed3\u675f\u76d1\u63a7")
        self._stop_btn.setObjectName("DangerBtn")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_monitoring)
        self._chart_btn = QPushButton("\U0001f4ca \u5b9e\u65f6\u76d1\u63a7")
        self._chart_btn.setCursor(Qt.PointingHandCursor)
        self._chart_btn.clicked.connect(self._open_chart_window)
        self._log_btn = QPushButton("\U0001f4cb \u65e5\u5fd7\u6570\u636e")
        self._log_btn.setCursor(Qt.PointingHandCursor)
        self._log_btn.clicked.connect(self._open_log_window)
        layout.addWidget(self._start_btn)
        layout.addWidget(self._stop_btn)
        layout.addWidget(self._chart_btn)
        layout.addWidget(self._log_btn)
        title_lbl = QLabel("\U0001f50b \u7535\u6c60\u76d1\u63a7\u5927\u5c4f")
        title_lbl.setStyleSheet(f"color: {TEXT_ACCENT}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl, stretch=1)
        self._fast_btn = QPushButton("\u26a1 \u667a\u80fd\u5feb\u5145")
        self._fast_btn.setCheckable(True)
        self._fast_btn.setCursor(Qt.PointingHandCursor)
        self._fast_btn.clicked.connect(self._toggle_fast)
        self._night_btn = QPushButton("\U0001f319 \u591c\u95f4\u5145\u7535")
        self._night_btn.setCheckable(True)
        self._night_btn.setCursor(Qt.PointingHandCursor)
        self._night_btn.clicked.connect(self._toggle_night)
        layout.addWidget(self._fast_btn)
        layout.addWidget(self._night_btn)
        return layout

    def _build_main_area(self):
        wrapper = QFrame()
        wrapper.setObjectName("Card")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self._build_left_column(), stretch=1)
        layout.addWidget(self._build_center_column(), stretch=1)
        layout.addWidget(self._build_right_column(), stretch=1)
        return wrapper

    def _build_left_column(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        gauge_card, gauge_body = _card()
        self._gauge = HalfGaugeWidget()
        gauge_body.addWidget(self._gauge)
        outer.addWidget(gauge_card, stretch=3)
        ring_card, ring_body = _card()
        ring_layout = QHBoxLayout()
        ring_layout.setSpacing(8)
        ring_layout.setAlignment(Qt.AlignCenter)
        self._rsoc_ring = RingIndicator(title="RSOC", max_val=100, color="#448aff", unit="%", size=68)
        self._soh_ring = RingIndicator(title="SOH", max_val=100, color="#00e676", unit="%", size=68)
        self._temp_ring = RingIndicator(title="TEMP", max_val=80, color="#e040fb", unit="\u2103", size=68)
        for ring, name, color in [(self._rsoc_ring, "RSOC", "#448aff"), (self._soh_ring, "SOH", "#00e676"), (self._temp_ring, "TEMP", "#e040fb")]:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignCenter)
            col.setSpacing(1)
            rl = _make_label(name, 9, color, True)
            rl.setAlignment(Qt.AlignCenter)
            col.addWidget(ring, alignment=Qt.AlignCenter)
            col.addWidget(rl)
            ring_layout.addLayout(col)
        ring_body.addLayout(ring_layout)
        outer.addWidget(ring_card, stretch=2)
        status_card, status_body = _card("\u8fd0\u884c\u72b6\u6001")
        self._status_badges = []
        badge_specs = [("\u25cf", "\u5145\u7535\u72b6\u6001", "#448aff"), ("\u21aa", "\u5faa\u73af\u6b21\u6570", "#ffab40"), ("\u23f1", "\u8fd0\u884c\u65f6\u957f", "#00e676"), ("\U0001f4c5", "\u9996\u6b21\u4f7f\u7528", TEXT_SECONDARY), ("\U0001f321", "\u6700\u9ad8\u6e29\u5ea6", "#e040fb"), ("\U0001f4ca", "\u7535\u538b\u8303\u56f4", "#00e5c8")]
        badge_grid = QGridLayout()
        badge_grid.setSpacing(2)
        badge_grid.setContentsMargins(0, 0, 0, 0)
        for idx, (icon, label, color) in enumerate(badge_specs):
            badge = StatusBadge(icon=icon, label=label)
            badge.set_icon(icon, color)
            self._status_badges.append(badge)
            badge_grid.addWidget(badge, idx // 2, idx % 2)
        status_body.addLayout(badge_grid)
        outer.addWidget(status_card, stretch=2)
        return self._wrap(outer)

    def _build_center_column(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        top_card, top_body = _card()
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        self._battery_icon = BatteryIconWidget()
        top_layout.addWidget(self._battery_icon, alignment=Qt.AlignCenter)
        cap_col = QVBoxLayout()
        cap_col.setSpacing(4)
        self._fcc_bar_frame = None
        self._fcc_bar_val = None
        self._rm_bar_frame = None
        self._rm_bar_val = None
        self._dc_bar_frame = None
        self._dc_bar_val = None
        for name, color in [("FCC", "#00e5c8"), ("RM", "#448aff"), ("DC", "#00e676")]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, 9, TEXT_LABEL)
            lbl.setFixedWidth(28)
            row.addWidget(lbl)
            bar = QFrame()
            bar.setFixedHeight(12)
            bar.setStyleSheet("background: #1a2a3a; border-radius: 3px;")
            row.addWidget(bar, stretch=1)
            val = _make_label("--%", 9, TEXT_VALUE, True)
            val.setFixedWidth(40)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val)
            cap_col.addLayout(row)
            if name == "FCC":
                self._fcc_bar_frame = bar
                self._fcc_bar_val = val
            elif name == "RM":
                self._rm_bar_frame = bar
                self._rm_bar_val = val
            elif name == "DC":
                self._dc_bar_frame = bar
                self._dc_bar_val = val
        top_layout.addLayout(cap_col, stretch=1)
        top_body.addLayout(top_layout)
        outer.addWidget(top_card, stretch=2)
        cell_card, cell_body = _card("\u7535\u82af\u7535\u538b")
        self._cell_rows = []
        for i in range(1, 5):
            row = QHBoxLayout()
            row.setSpacing(4)
            name_lbl = _make_label(f"Cell {i}", 9, TEXT_LABEL)
            name_lbl.setFixedWidth(34)
            row.addWidget(name_lbl)
            bar = QFrame()
            bar.setFixedHeight(10)
            bar.setStyleSheet("background: #1a2a3a; border-radius: 3px;")
            row.addWidget(bar, stretch=1)
            val_lbl = _make_label("-- mV", 9, TEXT_VALUE, True)
            val_lbl.setFixedWidth(52)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val_lbl)
            self._cell_rows.append((bar, val_lbl))
            cell_body.addLayout(row)
        self._vdiff_lbl = _make_label("\u538b\u5dee: -- mV", 9, TEXT_LABEL)
        cell_body.addWidget(self._vdiff_lbl)
        outer.addWidget(cell_card, stretch=2)
        bottom_card, bottom_body = _card("\u529f\u7387\u9650\u5236 & \u4f1a\u8bdd")
        bot_layout = QHBoxLayout()
        bot_layout.setSpacing(8)
        pl_col = QVBoxLayout()
        pl_col.setSpacing(3)
        self._pl_rows = {}
        for name, desc in [("PL1", "\u6301\u7eed\u529f\u7387"), ("PL2", "\u7206\u53d1\u529f\u7387"), ("PL4", "\u6781\u9650\u529f\u7387")]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, 9, TEXT_LABEL)
            lbl.setFixedWidth(28)
            row.addWidget(lbl)
            val = _make_label("-- W", 10, TEXT_VALUE, True)
            row.addWidget(val)
            row.addStretch()
            sub = _make_label(desc, 8, TEXT_SECONDARY)
            pl_col.addLayout(row)
            pl_col.addWidget(sub)
            self._pl_rows[name] = val
        bot_layout.addLayout(pl_col)
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet("background-color: #2a3f55; max-width: 1px;")
        bot_layout.addWidget(sep_v)
        sess_col = QVBoxLayout()
        sess_col.setSpacing(3)
        self._sess_labels = {}
        for name in ["\u91c7\u6837\u6b21\u6570", "\u5e73\u5747\u7535\u538b", "\u5e73\u5747\u7535\u6d41", "\u5e73\u5747\u6e29\u5ea6", "\u5e73\u5747\u529f\u7387"]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, 9, TEXT_LABEL)
            row.addWidget(lbl)
            row.addStretch()
            val = _make_label("--", 9, TEXT_VALUE, True)
            row.addWidget(val)
            sess_col.addLayout(row)
            self._sess_labels[name] = val
        bot_layout.addLayout(sess_col)
        bottom_body.addLayout(bot_layout)
        outer.addWidget(bottom_card, stretch=2)
        return self._wrap(outer)

    def _build_right_column(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # 采样统计卡片
        stats_card, stats_body = _card("\u91c7\u6837\u7edf\u8ba1")
        self._sess_labels = {}
        for name in ["\u91c7\u6837\u6b21\u6570",
                      "\u5e73\u5747\u7535\u538b",
                      "\u5e73\u5747\u7535\u6d41",
                      "\u5e73\u5747\u6e29\u5ea6",
                      "\u5e73\u5747\u529f\u7387"]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, 9, TEXT_LABEL)
            row.addWidget(lbl)
            row.addStretch()
            val = _make_label("--", 9, TEXT_VALUE, True)
            row.addWidget(val)
            stats_body.addLayout(row)
            self._sess_labels[name] = val
        outer.addWidget(stats_card, stretch=2)

        # 寿命预测卡片
        self._life_widget = LifePredictionWidget()
        life_card, life_body = _card()
        life_body.addWidget(self._life_widget)
        outer.addWidget(life_card, stretch=2)

        # 充电模式卡片
        mode_card, mode_body = _card(
            "\u5145\u7535\u6a21\u5f0f")
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        self._fast_mode_card = QFrame()
        self._fast_mode_card.setStyleSheet(
            "background: #0d2818; border: 1px solid "
            "#00e676; border-radius: 4px; padding: 4px;")
        fast_inner = QVBoxLayout(self._fast_mode_card)
        fast_inner.setAlignment(Qt.AlignCenter)
        fi = _make_label("\u26a1", 14, "#00e676", True)
        fi.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(fi)
        self._fast_mode_label = _make_label(
            "\u5feb\u5145", 10, "#00e676", True)
        self._fast_mode_label.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(self._fast_mode_label)
        self._fast_mode_state = _make_label(
            "OFF", 9, "#5a6a7a", True)
        self._fast_mode_state.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(self._fast_mode_state)

        self._night_mode_card = QFrame()
        self._night_mode_card.setStyleSheet(
            "background: #1a2a3a; border: 1px solid "
            "#2a3f55; border-radius: 4px; padding: 4px;")
        night_inner = QVBoxLayout(self._night_mode_card)
        night_inner.setAlignment(Qt.AlignCenter)
        ni = _make_label("\U0001f319", 14, "#7a8fa3", True)
        ni.setAlignment(Qt.AlignCenter)
        night_inner.addWidget(ni)
        self._night_mode_label = _make_label(
            "\u591c\u5145", 10, "#7a8fa3", True)
        self._night_mode_label.setAlignment(Qt.AlignCenter)
        night_inner.addWidget(self._night_mode_label)
        self._night_mode_state = _make_label(
            "OFF", 9, "#5a6a7a", True)
        self._night_mode_state.setAlignment(Qt.AlignCenter)
        night_inner.addWidget(self._night_mode_state)

        mode_layout.addWidget(self._fast_mode_card)
        mode_layout.addWidget(self._night_mode_card)
        mode_body.addLayout(mode_layout)
        outer.addWidget(mode_card, stretch=1)
        return self._wrap(outer)

    def _wrap(self, layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def _build_bottom_bar(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(12)
        layout.addStretch()
        self._runtime_lbl = _make_label(
            "\u8fd0\u884c: 00:00:00", 10, TEXT_SECONDARY)
        layout.addWidget(self._runtime_lbl)
        self._timestamp_lbl = _make_label(
            "--:--:--", 10, TEXT_SECONDARY)
        layout.addWidget(self._timestamp_lbl)
        return layout

    def _start_monitoring(self):
        if self._worker is not None:
            return
        self._start_time = _time.monotonic()
        self._sample_count = 0
        self._sum_voltage = 0.0
        self._sum_current = 0.0
        self._sum_temperature = 0.0
        self._sum_power = 0.0
        self._worker = DataWorker(service=self._data_service, interval_ms=self._config.poll_interval_ms, parent=self)
        self._worker.data_ready.connect(self._on_snapshot)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_bar.showMessage("\u76d1\u63a7\u8fd0\u884c\u4e2d...")
        logger.info("监控已启动")

    def _stop_monitoring(self):
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.data_ready.disconnect(self._on_snapshot)
        self._worker.error_occurred.disconnect(self._on_error)
        self._worker = None
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_bar.showMessage("\u76d1\u63a7\u5df2\u505c\u6b62")
        logger.info("监控已停止")

    @Slot(BatterySnapshot)
    def _on_snapshot(self, s):
        self._sample_count += 1
        self._sum_voltage += s.voltage
        self._sum_current += s.current
        self._sum_temperature += s.temperature
        power = abs(s.voltage * s.current) / 1_000_000
        self._sum_power += power
        self._gauge.setValue(s.predicted_life_months)
        self._rsoc_ring.setValue(float(s.rsoc))
        self._soh_ring.setValue(float(s.soh))
        self._temp_ring.setValue(s.temperature)
        self._update_status_badges(s)
        self._battery_icon.set_data(s.rsoc, s.charge_state)
        self._update_capacity_bars(s)
        self._update_cell_bars(s)
        self._update_power_limits_widget(s)
        self._update_session_stats()
        self._life_widget.setValue(s.predicted_life_months)
        self._update_charge_mode_ui(s)
        if self._chart_window is not None and self._chart_window.isVisible():
            self._chart_window.on_snapshot(s)
        # 更新底部时间戳
        self._timestamp_lbl.setText(s.timestamp.strftime('%H:%M:%S'))
        self._status_bar.showMessage(f"\u91c7\u6837 #{self._sample_count} \u2014 {s.timestamp.strftime('%H:%M:%S')} | {s.voltage}mV {s.current}mA {s.temperature}\u2103 RSOC={s.rsoc}%")

    @Slot(Exception)
    def _on_error(self, error):
        logger.error("\u6570\u636e\u91c7\u96c6\u9519\u8bef: %s", error)
        self._status_bar.showMessage(f"\u9519\u8bef: {error}")

    @staticmethod
    def _update_bar(frame, pct, color):
        pct = max(0.0, min(100.0, pct))
        frame.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:{pct / 100} {color}, stop:{pct / 100} #1a2a3a, stop:1 #1a2a3a); border-radius: 3px;")

    def _update_status_badges(self, s):
        if len(self._status_badges) < 6:
            return
        state_map = {"charging": ("\u5145\u7535\u4e2d", "#00e676"), "discharging": ("\u653e\u7535\u4e2d", "#ffab40"), "idle": ("\u5f85\u673a", "#7a8fa3"), "full": ("\u5df2\u6ee1", "#448aff")}
        state_text, state_color = state_map.get(s.charge_state, ("\u672a\u77e5", TEXT_SECONDARY))
        self._status_badges[0].set_value(state_text, state_color)
        self._status_badges[1].set_value(str(s.cycle_count), TEXT_PRIMARY)
        elapsed = _time.monotonic() - self._start_time
        h, m, sec = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
        self._status_badges[2].set_value(f"{h:02d}:{m:02d}:{sec:02d}", TEXT_PRIMARY)
        self._status_badges[3].set_value(s.first_usage_time, TEXT_SECONDARY)
        temp_color = "#ff5252" if s.max_temperature > 60 else ("#ffab40" if s.max_temperature > 45 else TEXT_PRIMARY)
        self._status_badges[4].set_value(f"{s.max_temperature:.1f}\u2103", temp_color)
        self._status_badges[5].set_value(f"{s.min_voltage}-{s.max_voltage}", TEXT_PRIMARY)

    def _update_capacity_bars(self, s):
        if s.dc <= 0:
            return
        fcc_pct = s.fcc / s.dc * 100
        rm_pct = s.rm / s.dc * 100
        if self._fcc_bar_frame:
            self._update_bar(self._fcc_bar_frame, fcc_pct, "#00e5c8")
        if self._fcc_bar_val:
            self._fcc_bar_val.setText(f"{fcc_pct:.1f}%")
        if self._rm_bar_frame:
            self._update_bar(self._rm_bar_frame, rm_pct, "#448aff")
        if self._rm_bar_val:
            self._rm_bar_val.setText(f"{rm_pct:.1f}%")
        if self._dc_bar_frame:
            self._update_bar(self._dc_bar_frame, 100.0, "#00e676")
        if self._dc_bar_val:
            self._dc_bar_val.setText("100%")

    def _update_cell_bars(self, s):
        base_v = s.voltage / 4
        vals = []
        for i in range(4):
            cell_v = base_v + _random.uniform(-200, 200)
            cell_v = max(0, min(5000, cell_v))
            vals.append(cell_v)
            bar, lbl = self._cell_rows[i]
            pct = cell_v / 4200 * 100
            color = "#ff5252" if cell_v > 4350 else ("#ffab40" if cell_v < 3000 else "#00e5c8")
            self._update_bar(bar, pct, color)
            lbl.setText(f"{cell_v:.0f} mV")
        vdiff = max(vals) - min(vals)
        diff_color = "#ff5252" if vdiff > 200 else ("#ffab40" if vdiff > 100 else TEXT_LABEL)
        if self._vdiff_lbl is not None:
            self._vdiff_lbl.setText(f"\u538b\u5dee: {vdiff:.0f} mV")
            self._vdiff_lbl.setStyleSheet(f"color: {diff_color}; font-size: 9px; border: none; background: transparent;")

    def _update_power_limits_widget(self, s):
        for name, val in [("PL1", s.pl1), ("PL2", s.pl2), ("PL4", s.pl4)]:
            if name in self._pl_rows:
                self._pl_rows[name].setText(f"{val} W")

    def _update_session_stats(self):
        n = self._sample_count
        if n == 0:
            return
        updates = {"\u91c7\u6837\u6b21\u6570": str(n), "\u5e73\u5747\u7535\u538b": f"{self._sum_voltage / n:.0f} mV", "\u5e73\u5747\u7535\u6d41": f"{self._sum_current / n:.0f} mA", "\u5e73\u5747\u6e29\u5ea6": f"{self._sum_temperature / n:.1f} \u2103", "\u5e73\u5747\u529f\u7387": f"{self._sum_power / n:.1f} W"}
        for key, val in updates.items():
            if key in self._sess_labels:
                self._sess_labels[key].setText(val)

    def _update_charge_mode_ui(self, s):
        is_fast = s.battery_mode & 0x01
        is_night = s.battery_mode & 0x02
        if is_fast:
            self._fast_mode_card.setStyleSheet("background: #0d2818; border: 1px solid #00e676; border-radius: 4px; padding: 4px;")
            self._fast_mode_state.setText("ON")
            self._fast_mode_state.setStyleSheet(f"color: {STATUS_GOOD}; font-size: 9px; font-weight: bold; border: none; background: transparent;")
        else:
            self._fast_mode_card.setStyleSheet("background: #1a2a3a; border: 1px solid #2a3f55; border-radius: 4px; padding: 4px;")
            self._fast_mode_state.setText("OFF")
            self._fast_mode_state.setStyleSheet("color: #5a6a7a; font-size: 9px; font-weight: bold; border: none; background: transparent;")
        if is_night:
            self._night_mode_card.setStyleSheet("background: #0d1a2e; border: 1px solid #448aff; border-radius: 4px; padding: 4px;")
            self._night_mode_state.setText("ON")
            self._night_mode_state.setStyleSheet("color: #448aff; font-size: 9px; font-weight: bold; border: none; background: transparent;")
        else:
            self._night_mode_card.setStyleSheet("background: #1a2a3a; border: 1px solid #2a3f55; border-radius: 4px; padding: 4px;")
            self._night_mode_state.setText("OFF")
            self._night_mode_state.setStyleSheet("color: #5a6a7a; font-size: 9px; font-weight: bold; border: none; background: transparent;")

    def _open_chart_window(self):
        if self._chart_window is None:
            self._chart_window = ChartWindow(self._config, parent=self)
        self._chart_window.show()
        self._chart_window.raise_()
        self._chart_window.activateWindow()

    def _open_log_window(self):
        if self._log_window is None:
            from lenovo_tool.ui.log_window import LogWindow
            self._log_window = LogWindow(self._dll, self._config, parent=self)
        self._log_window.show()
        self._log_window.raise_()
        self._log_window.activateWindow()

    def _toggle_fast(self):
        try:
            new_state = self._charge_service.toggle(ChargeModeType.FAST_CHARGE)
            state_str = "\u5f00\u542f" if new_state else "\u5173\u95ed"
            self._status_bar.showMessage(f"\u667a\u80fd\u5feb\u5145\u5df2{state_str}")
            logger.info("智能快充: %s", state_str)
        except Exception as e:
            show_error(self, "\u5feb\u5145\u5207\u6362\u5931\u8d25", str(e))
            self._fast_btn.setChecked(False)

    def _toggle_night(self):
        try:
            new_state = self._charge_service.toggle(ChargeModeType.NIGHT_CHARGE)
            state_str = "\u5f00\u542f" if new_state else "\u5173\u95ed"
            self._status_bar.showMessage(f"\u591c\u95f4\u5145\u7535\u5df2{state_str}")
            logger.info("夜间充电: %s", state_str)
        except Exception as e:
            show_error(self, "\u591c\u5145\u5207\u6362\u5931\u8d25", str(e))
            self._night_btn.setChecked(False)

    def closeEvent(self, event):
        self._stop_monitoring()
        if self._chart_window is not None and self._chart_window.isVisible():
            self._chart_window.close()
        if self._log_window is not None and self._log_window.isVisible():
            self._log_window.close()
        logger.info("主窗口已关闭")
        super().closeEvent(event)
