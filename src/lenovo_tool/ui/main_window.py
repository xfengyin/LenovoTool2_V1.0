"""电池监控大屏 — 主窗口模块。

提供高密度企业级监控仪表板界面，实时展示电池各项指标。
3列布局：左列（仪表盘+环形指标+运行状态）、
中列（电池图标+容量条+电压详情+功率+会话）、
右列（容量详情+充电模式）。

UI层仅负责界面组装和事件绑定，业务逻辑由ViewModel处理。
"""

import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QLabel, QPushButton, QStatusBar,
)

from lenovo_tool.core.data_models import AppConfig, BatterySnapshot
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.ui.chart_window import ChartWindow
from lenovo_tool.ui.dialogs.error_dialog import show_error
from lenovo_tool.ui.styles.main_style import (
    global_stylesheet, TEXT_ACCENT, TEXT_SECONDARY,
    TEXT_LABEL, TEXT_PRIMARY, TEXT_VALUE, STATUS_GOOD,
    BAR_BG, BORDER_SUBTLE, FONT_XS, FONT_SM, FONT_BASE, FONT_MD, FONT_LG,
)
from lenovo_tool.ui.view_models.main_view_model import MainViewModel
from lenovo_tool.ui.widgets.half_gauge_widget import HalfGaugeWidget
from lenovo_tool.ui.widgets.battery_icon_widget import BatteryIconWidget
from lenovo_tool.ui.widgets.gradient_bar import GradientBar
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


def _make_label(text, size=FONT_SM, color=TEXT_LABEL, bold=False):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; "
        f"font-weight: {weight}; border: none; "
        f"background: transparent;"
    )
    return lbl


class MainWindow(QMainWindow):
    def __init__(self, dll: DLLInterface, config: AppConfig, parent=None):
        super().__init__(parent)
        self._dll = dll
        self._config = config
        self._view_model = MainViewModel(dll, config)
        self._worker = None
        self._chart_window = None
        self._log_window = None
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
        self._setup_event_bindings()

    def _setup_event_bindings(self):
        self._view_model.session_stats_updated.connect(self._on_session_stats_updated)
        self._view_model.charge_mode_updated.connect(self._on_charge_mode_updated)

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
        title_lbl.setStyleSheet(
            f"color: {TEXT_ACCENT}; font-size: {FONT_MD}px; "
            f"font-weight: bold; border: none; background: transparent;"
        )
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
        for ring, name, color in [
            (self._rsoc_ring, "RSOC", "#448aff"),
            (self._soh_ring, "SOH", "#00e676"),
            (self._temp_ring, "TEMP", "#e040fb"),
        ]:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignCenter)
            col.setSpacing(1)
            rl = _make_label(name, FONT_XS, color, True)
            rl.setAlignment(Qt.AlignCenter)
            col.addWidget(ring, alignment=Qt.AlignCenter)
            col.addWidget(rl)
            ring_layout.addLayout(col)
        ring_body.addLayout(ring_layout)
        outer.addWidget(ring_card, stretch=2)
        status_card, status_body = _card("\u8fd0\u884c\u72b6\u6001")
        self._status_badges = []
        badge_specs = [
            ("\u25cf", "\u5145\u7535\u72b6\u6001", "#448aff"),
            ("\u21aa", "\u5faa\u73af\u6b21\u6570", "#ffab40"),
            ("\u23f1", "\u8fd0\u884c\u65f6\u957f", "#00e676"),
            ("\U0001f4c5", "\u9996\u6b21\u4f7f\u7528", TEXT_SECONDARY),
            ("\U0001f321", "\u6700\u9ad8\u6e29\u5ea6", "#e040fb"),
            ("\U0001f4ca", "\u7535\u538b\u8303\u56f4", "#00e5c8"),
        ]
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
        # --- Top: Battery icon + capacity bars ---
        top_card, top_body = _card()
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        self._battery_icon = BatteryIconWidget()
        top_layout.addWidget(self._battery_icon, alignment=Qt.AlignCenter)
        cap_col = QVBoxLayout()
        cap_col.setSpacing(4)
        self._fcc_bar = GradientBar(height=12)
        self._fcc_bar_val = None
        self._rm_bar = GradientBar(height=12)
        self._rm_bar_val = None
        self._dc_bar = GradientBar(height=12)
        self._dc_bar_val = None
        for name, color, bar, attr_bar, attr_val in [
            ("FCC", "#00e5c8", self._fcc_bar, "_fcc_bar", "_fcc_bar_val"),
            ("RM", "#448aff", self._rm_bar, "_rm_bar", "_rm_bar_val"),
            ("DC", "#00e676", self._dc_bar, "_dc_bar", "_dc_bar_val"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, FONT_XS, TEXT_LABEL)
            lbl.setFixedWidth(28)
            row.addWidget(lbl)
            row.addWidget(bar, stretch=1)
            val = _make_label("--%", FONT_XS, TEXT_VALUE, True)
            val.setFixedWidth(40)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val)
            cap_col.addLayout(row)
            setattr(self, attr_val, val)
        top_layout.addLayout(cap_col, stretch=1)
        top_body.addLayout(top_layout)
        outer.addWidget(top_card, stretch=2)
        # --- Middle: Voltage details (real data, replaces fake cell voltages) ---
        volt_card, volt_body = _card("\u7535\u538b\u8be6\u60c5")
        self._volt_bar = GradientBar(height=12)
        self._volt_bar_val = _make_label("-- mV", FONT_SM, TEXT_VALUE, True)
        self._volt_bar_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v_row1 = QHBoxLayout()
        v_row1.setSpacing(4)
        v_row1.addWidget(_make_label("\u5f53\u524d\u7535\u538b", FONT_XS, TEXT_LABEL))
        v_row1.addWidget(self._volt_bar, stretch=1)
        v_row1.addWidget(self._volt_bar_val)
        volt_body.addLayout(v_row1)
        self._dv_lbl = _make_label("\u8bbe\u8ba1\u7535\u538b: -- mV", FONT_XS, TEXT_SECONDARY)
        self._vmin_lbl = _make_label("\u6700\u4f4e\u7535\u538b: -- mV", FONT_XS, TEXT_SECONDARY)
        self._vmax_lbl = _make_label("\u6700\u9ad8\u7535\u538b: -- mV", FONT_XS, TEXT_SECONDARY)
        volt_body.addWidget(self._dv_lbl)
        volt_body.addWidget(self._vmin_lbl)
        volt_body.addWidget(self._vmax_lbl)
        outer.addWidget(volt_card, stretch=2)
        # --- Bottom: Power limits & session stats ---
        bottom_card, bottom_body = _card("\u529f\u7387\u9650\u5236 & \u4f1a\u8bdd")
        bot_layout = QHBoxLayout()
        bot_layout.setSpacing(8)
        pl_col = QVBoxLayout()
        pl_col.setSpacing(3)
        self._pl_rows = {}
        for name, desc in [
            ("PL1", "\u6301\u7eed\u529f\u7387"),
            ("PL2", "\u7206\u53d1\u529f\u7387"),
            ("PL4", "\u6781\u9650\u529f\u7387"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, FONT_XS, TEXT_LABEL)
            lbl.setFixedWidth(28)
            row.addWidget(lbl)
            val = _make_label("-- W", FONT_BASE, TEXT_VALUE, True)
            row.addWidget(val)
            row.addStretch()
            sub = _make_label(desc, FONT_XS, TEXT_SECONDARY)
            pl_col.addLayout(row)
            pl_col.addWidget(sub)
            self._pl_rows[name] = val
        bot_layout.addLayout(pl_col)
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-width: 1px;")
        bot_layout.addWidget(sep_v)
        sess_col = QVBoxLayout()
        sess_col.setSpacing(3)
        self._sess_labels = {}
        for name in ["\u91c7\u6837\u6b21\u6570", "\u5e73\u5747\u7535\u538b", "\u5e73\u5747\u7535\u6d41", "\u5e73\u5747\u6e29\u5ea6", "\u5e73\u5747\u529f\u7387"]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, FONT_XS, TEXT_LABEL)
            row.addWidget(lbl)
            row.addStretch()
            val = _make_label("--", FONT_XS, TEXT_VALUE, True)
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
        # --- Capacity details (replaces duplicate session stats) ---
        cap_card, cap_body = _card("\u5bb9\u91cf\u8be6\u60c5")
        self._cap_labels = {}
        for name in ["FCC", "RM", "DC", "\u5065\u5eb7\u5ea6"]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _make_label(name, FONT_XS, TEXT_LABEL)
            row.addWidget(lbl)
            row.addStretch()
            val = _make_label("--", FONT_SM, TEXT_VALUE, True)
            row.addWidget(val)
            cap_body.addLayout(row)
            self._cap_labels[name] = val
        outer.addWidget(cap_card, stretch=2)
        # --- Health assessment (replaces duplicate life prediction) ---
        health_card, health_body = _card("\u5065\u5eb7\u8bc4\u4f30")
        self._soh_val_lbl = _make_label("SOH: --%", FONT_SM, TEXT_VALUE, True)
        health_body.addWidget(self._soh_val_lbl)
        self._cycle_val_lbl = _make_label("\u5faa\u73af\u6b21\u6570: --", FONT_SM, TEXT_SECONDARY)
        health_body.addWidget(self._cycle_val_lbl)
        self._degrade_val_lbl = _make_label("\u8870\u51cf\u7387: --%", FONT_SM, TEXT_SECONDARY)
        health_body.addWidget(self._degrade_val_lbl)
        outer.addWidget(health_card, stretch=2)
        # --- Charge mode ---
        mode_card, mode_body = _card("\u5145\u7535\u6a21\u5f0f")
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        self._fast_mode_card = QFrame()
        self._fast_mode_card.setStyleSheet(
            f"background: #0d2818; border: 1px solid {STATUS_GOOD}; "
            f"border-radius: 4px; padding: 4px;"
        )
        fast_inner = QVBoxLayout(self._fast_mode_card)
        fast_inner.setAlignment(Qt.AlignCenter)
        fi = _make_label("\u26a1", FONT_LG, STATUS_GOOD, True)
        fi.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(fi)
        self._fast_mode_label = _make_label("\u5feb\u5145", FONT_SM, STATUS_GOOD, True)
        self._fast_mode_label.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(self._fast_mode_label)
        self._fast_mode_state = _make_label("OFF", FONT_XS, "#5a6a7a", True)
        self._fast_mode_state.setAlignment(Qt.AlignCenter)
        fast_inner.addWidget(self._fast_mode_state)
        self._night_mode_card = QFrame()
        self._night_mode_card.setStyleSheet(
            f"background: {BAR_BG}; border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: 4px; padding: 4px;"
        )
        night_inner = QVBoxLayout(self._night_mode_card)
        night_inner.setAlignment(Qt.AlignCenter)
        ni = _make_label("\U0001f319", FONT_LG, "#7a8fa3", True)
        ni.setAlignment(Qt.AlignCenter)
        night_inner.addWidget(ni)
        self._night_mode_label = _make_label("\u591c\u5145", FONT_SM, "#7a8fa3", True)
        self._night_mode_label.setAlignment(Qt.AlignCenter)
        night_inner.addWidget(self._night_mode_label)
        self._night_mode_state = _make_label("OFF", FONT_XS, "#5a6a7a", True)
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
        self._runtime_lbl = _make_label("\u8fd0\u884c: 00:00:00", FONT_BASE, TEXT_SECONDARY)
        layout.addWidget(self._runtime_lbl)
        self._timestamp_lbl = _make_label("--:--:--", FONT_BASE, TEXT_SECONDARY)
        layout.addWidget(self._timestamp_lbl)
        return layout

    def _start_monitoring(self):
        if self._worker is not None:
            return
        self._view_model.start_session()
        self._worker = DataWorker(
            service=self._view_model._data_service,
            interval_ms=self._config.poll_interval_ms,
            parent=self,
        )
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
    def _on_snapshot(self, snapshot: BatterySnapshot):
        self._view_model.process_snapshot(snapshot)
        self._update_gauge(snapshot)
        self._update_rings(snapshot)
        self._update_status_badges(snapshot)
        self._update_battery_icon(snapshot)
        self._update_capacity_bars(snapshot)
        self._update_voltage_details(snapshot)
        self._update_power_limits(snapshot)
        self._update_capacity_details(snapshot)
        self._update_health(snapshot)
        if self._chart_window is not None and self._chart_window.isVisible():
            self._chart_window.on_snapshot(snapshot)
        self._timestamp_lbl.setText(snapshot.timestamp.strftime('%H:%M:%S'))
        self._status_bar.showMessage(self._view_model.get_status_bar_text(snapshot))

    @Slot(Exception)
    def _on_error(self, error):
        logger.error("\u6570\u636e\u91c7\u96c6\u9519\u8bef: %s", error)
        self._status_bar.showMessage(f"\u9519\u8bef: {error}")

    @Slot(dict)
    def _on_session_stats_updated(self, stats):
        updates = {
            "\u91c7\u6837\u6b21\u6570": stats.get("sample_count", "--"),
            "\u5e73\u5747\u7535\u538b": stats.get("avg_voltage", "--"),
            "\u5e73\u5747\u7535\u6d41": stats.get("avg_current", "--"),
            "\u5e73\u5747\u6e29\u5ea6": stats.get("avg_temperature", "--"),
            "\u5e73\u5747\u529f\u7387": stats.get("avg_power", "--"),
        }
        for key, val in updates.items():
            if key in self._sess_labels:
                self._sess_labels[key].setText(str(val))
        self._runtime_lbl.setText(f"\u8fd0\u884c: {stats.get('runtime', '00:00:00')}")

    @Slot(bool, bool)
    def _on_charge_mode_updated(self, is_fast: bool, is_night: bool):
        self._update_fast_mode_ui(is_fast)
        self._update_night_mode_ui(is_night)

    def _update_gauge(self, s):
        self._gauge.setValue(s.predicted_life_months)

    def _update_rings(self, s):
        self._rsoc_ring.setValue(float(s.rsoc))
        self._soh_ring.setValue(float(s.soh))
        self._temp_ring.setValue(s.temperature)

    def _update_status_badges(self, s):
        if len(self._status_badges) < 6:
            return
        state_text, state_color = self._view_model.format_charge_state(s.charge_state)
        self._status_badges[0].set_value(state_text, state_color)
        self._status_badges[1].set_value(str(s.cycle_count), TEXT_PRIMARY)
        self._status_badges[2].set_value(self._view_model.format_runtime(), TEXT_PRIMARY)
        self._status_badges[3].set_value(s.first_usage_time, TEXT_SECONDARY)
        temp_color = self._view_model.format_temperature_color(s.max_temperature)
        self._status_badges[4].set_value(f"{s.max_temperature:.1f}\u2103", temp_color)
        self._status_badges[5].set_value(self._view_model.get_voltage_range_text(s), TEXT_PRIMARY)

    def _update_battery_icon(self, s):
        self._battery_icon.set_data(s.rsoc, s.charge_state)

    def _update_capacity_bars(self, s):
        fcc_pct, rm_pct = self._view_model.calculate_capacity_percentages(s)
        self._fcc_bar.setValue(fcc_pct, "#00e5c8")
        self._fcc_bar_val.setText(f"{fcc_pct:.1f}%")
        self._rm_bar.setValue(rm_pct, "#448aff")
        self._rm_bar_val.setText(f"{rm_pct:.1f}%")
        self._dc_bar.setValue(100.0, "#00e676")
        self._dc_bar_val.setText("100%")

    def _update_voltage_details(self, s):
        """Update voltage display with real data from snapshot."""
        dv = s.dv if s.dv > 0 else 1
        volt_pct = min(100.0, s.voltage / dv * 100)
        volt_color = "#ff5252" if s.voltage > dv * 1.05 else ("#ffab40" if s.voltage < dv * 0.9 else "#00e5c8")
        self._volt_bar.setValue(volt_pct, volt_color)
        self._volt_bar_val.setText(f"{s.voltage} mV")
        self._dv_lbl.setText(f"\u8bbe\u8ba1\u7535\u538b: {s.dv} mV")
        self._vmin_lbl.setText(f"\u6700\u4f4e\u7535\u538b: {s.min_voltage} mV" if s.min_voltage else "\u6700\u4f4e\u7535\u538b: -- mV")
        self._vmax_lbl.setText(f"\u6700\u9ad8\u7535\u538b: {s.max_voltage} mV" if s.max_voltage else "\u6700\u9ad8\u7535\u538b: -- mV")

    def _update_power_limits(self, s):
        for name, val in [("PL1", s.pl1), ("PL2", s.pl2), ("PL4", s.pl4)]:
            if name in self._pl_rows:
                self._pl_rows[name].setText(f"{val} W")

    def _update_capacity_details(self, s):
        """Update capacity details card with real mAh values."""
        if "FCC" in self._cap_labels:
            self._cap_labels["FCC"].setText(f"{s.fcc} mAh")
        if "RM" in self._cap_labels:
            self._cap_labels["RM"].setText(f"{s.rm} mAh")
        if "DC" in self._cap_labels:
            self._cap_labels["DC"].setText(f"{s.dc} mAh")
        if "\u5065\u5eb7\u5ea6" in self._cap_labels:
            health = s.fcc / s.dc * 100 if s.dc > 0 else 0
            self._cap_labels["\u5065\u5eb7\u5ea6"].setText(f"{health:.1f}%")

    def _update_health(self, s):
        """Update health assessment card."""
        self._soh_val_lbl.setText(f"SOH: {s.soh}%")
        self._cycle_val_lbl.setText(f"\u5faa\u73af\u6b21\u6570: {s.cycle_count}")
        degrade = (1 - s.fcc / s.dc) * 100 if s.dc > 0 else 0
        degrade_color = "#ff5252" if degrade > 30 else ("#ffab40" if degrade > 15 else TEXT_SECONDARY)
        self._degrade_val_lbl.setText(f"\u8870\u51cf\u7387: {degrade:.1f}%")
        self._degrade_val_lbl.setStyleSheet(
            f"color: {degrade_color}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )

    def _update_fast_mode_ui(self, is_fast: bool):
        if is_fast:
            self._fast_mode_card.setStyleSheet(
                f"background: #0d2818; border: 1px solid {STATUS_GOOD}; "
                f"border-radius: 4px; padding: 4px;"
            )
            self._fast_mode_state.setText("ON")
            self._fast_mode_state.setStyleSheet(
                f"color: {STATUS_GOOD}; font-size: {FONT_XS}px; "
                f"font-weight: bold; border: none; background: transparent;"
            )
        else:
            self._fast_mode_card.setStyleSheet(
                f"background: {BAR_BG}; border: 1px solid {BORDER_SUBTLE}; "
                f"border-radius: 4px; padding: 4px;"
            )
            self._fast_mode_state.setText("OFF")
            self._fast_mode_state.setStyleSheet(
                f"color: #5a6a7a; font-size: {FONT_XS}px; "
                f"font-weight: bold; border: none; background: transparent;"
            )

    def _update_night_mode_ui(self, is_night: bool):
        if is_night:
            self._night_mode_card.setStyleSheet(
                f"background: #0d1a2e; border: 1px solid #448aff; "
                f"border-radius: 4px; padding: 4px;"
            )
            self._night_mode_state.setText("ON")
            self._night_mode_state.setStyleSheet(
                f"color: #448aff; font-size: {FONT_XS}px; "
                f"font-weight: bold; border: none; background: transparent;"
            )
        else:
            self._night_mode_card.setStyleSheet(
                f"background: {BAR_BG}; border: 1px solid {BORDER_SUBTLE}; "
                f"border-radius: 4px; padding: 4px;"
            )
            self._night_mode_state.setText("OFF")
            self._night_mode_state.setStyleSheet(
                f"color: #5a6a7a; font-size: {FONT_XS}px; "
                f"font-weight: bold; border: none; background: transparent;"
            )

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
            new_state = self._view_model.toggle_fast_charge()
            state_str = "\u5f00\u542f" if new_state else "\u5173\u95ed"
            self._status_bar.showMessage(f"\u667a\u80fd\u5feb\u5145\u5df2{state_str}")
        except Exception as e:
            show_error(self, "\u5feb\u5145\u5207\u6362\u5931\u8d25", str(e))
            self._fast_btn.setChecked(False)

    def _toggle_night(self):
        try:
            new_state = self._view_model.toggle_night_charge()
            state_str = "\u5f00\u542f" if new_state else "\u5173\u95ed"
            self._status_bar.showMessage(f"\u591c\u95f4\u5145\u7535\u5df2{state_str}")
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
