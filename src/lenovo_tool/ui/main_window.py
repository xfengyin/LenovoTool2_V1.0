"""电池监控大屏 - 主窗口（科技感数据监控大屏风格）。

布局：
- 顶部：装饰标题栏 + 系统状态
- 主体：三列面板布局
  - 左列：寿命预测仪表盘 + 环形指标（RSOC/SOH/TEMP） + 运行状态
  - 中列：KPI 指标卡（FCC/RM/电压/电流） + 电池图标 + 容量条 + 电压详情
  - 右列：健康评估 + 功率限制 + 充电模式 + 会话统计
- 底部：状态栏
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
    BAR_BG, BORDER_SUBTLE, BORDER_ACCENT, BORDER_GLOW,
    FONT_XS, FONT_SM, FONT_BASE, FONT_MD, FONT_LG,
    GLOW_CYAN, GLOW_GREEN, GLOW_ORANGE, GLOW_BLUE, GLOW_PURPLE, GLOW_RED,
    BG_PANEL_SOLID,
)
from lenovo_tool.ui.view_models.main_view_model import MainViewModel
from lenovo_tool.ui.widgets.half_gauge_widget import HalfGaugeWidget
from lenovo_tool.ui.widgets.battery_icon_widget import BatteryIconWidget
from lenovo_tool.ui.widgets.gradient_bar import GradientBar
from lenovo_tool.ui.widgets.ring_indicator import RingIndicator
from lenovo_tool.ui.widgets.panel_widget import PanelWidget
from lenovo_tool.ui.widgets.kpi_card import KpiCard
from lenovo_tool.ui.widgets.decorative_title_bar import DecorativeTitleBar
from lenovo_tool.ui.workers.data_worker import DataWorker

logger = logging.getLogger(__name__)


def _mk_label(text, size=FONT_SM, color=TEXT_LABEL, bold=False):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight}; "
        f"border: none; background: transparent;"
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
        root.setContentsMargins(4, 2, 4, 2)
        root.setSpacing(4)

        root.addWidget(self._build_title_bar())
        root.addWidget(self._build_control_bar())
        root.addWidget(self._build_main_area(), stretch=1)
        root.addWidget(self._build_bottom_bar())

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("\u5c31\u7eea - \u7b49\u5f85\u5f00\u59cb\u76d1\u63a7")

        self._setup_event_bindings()

    def _setup_event_bindings(self):
        self._view_model.session_stats_updated.connect(self._on_session_stats_updated)
        self._view_model.charge_mode_updated.connect(self._on_charge_mode_updated)

    # ============== 顶部标题栏 ==============
    def _build_title_bar(self):
        self._title_bar = DecorativeTitleBar("\u7535\u6c60\u76d1\u63a7\u5927\u5c4f")
        self._title_bar.set_left_text("\u7cfb\u7edf\u72b6\u6001\uff1a\u5728\u7ebf")
        self._title_bar.set_right_text("\u65f6\u95f4\uff1a--:--:--")
        return self._title_bar

    # ============== 控制栏 ==============
    def _build_control_bar(self):
        bar = QFrame()
        bar.setFixedHeight(40)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        self._start_btn = QPushButton("\u25b6 \u5f00\u59cb\u76d1\u63a7")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.clicked.connect(self._start_monitoring)
        layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("\u25a0 \u7ed3\u675f\u76d1\u63a7")
        self._stop_btn.setObjectName("DangerBtn")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_monitoring)
        layout.addWidget(self._stop_btn)

        self._chart_btn = QPushButton("\U0001f4ca \u5b9e\u65f6\u76d1\u63a7")
        self._chart_btn.setCursor(Qt.PointingHandCursor)
        self._chart_btn.clicked.connect(self._open_chart_window)
        layout.addWidget(self._chart_btn)

        self._log_btn = QPushButton("\U0001f4cb \u65e5\u5fd7\u6570\u636e")
        self._log_btn.setCursor(Qt.PointingHandCursor)
        self._log_btn.clicked.connect(self._open_log_window)
        layout.addWidget(self._log_btn)

        layout.addStretch()

        self._fast_btn = QPushButton("\u26a1 \u667a\u80fd\u5feb\u5145")
        self._fast_btn.setCheckable(True)
        self._fast_btn.setCursor(Qt.PointingHandCursor)
        self._fast_btn.clicked.connect(self._toggle_fast)
        layout.addWidget(self._fast_btn)

        self._night_btn = QPushButton("\U0001f319 \u591c\u95f4\u5145\u7535")
        self._night_btn.setCheckable(True)
        self._night_btn.setCursor(Qt.PointingHandCursor)
        self._night_btn.clicked.connect(self._toggle_night)
        layout.addWidget(self._night_btn)

        return bar

    # ============== 主体三列 ==============
    def _build_main_area(self):
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        layout.addWidget(self._build_left_column(), stretch=1)
        layout.addWidget(self._build_center_column(), stretch=1)
        layout.addWidget(self._build_right_column(), stretch=1)

        return wrapper

    # ============== 左列 ==============
    def _build_left_column(self):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        # 寿命预测
        life_panel = PanelWidget("\u5bff\u547d\u9884\u6d4b")
        self._gauge = HalfGaugeWidget()
        life_panel.content_layout.addWidget(self._gauge)
        col.addWidget(life_panel, stretch=3)

        # 环形指标
        ring_panel = PanelWidget("\u7535\u6c60\u72b6\u6001")
        ring_layout = QHBoxLayout()
        ring_layout.setSpacing(4)
        ring_layout.setAlignment(Qt.AlignCenter)
        self._rsoc_ring = RingIndicator(title="RSOC", color=GLOW_CYAN, unit="%", size=92)
        self._soh_ring = RingIndicator(title="SOH", color=GLOW_GREEN, unit="%", size=92)
        self._temp_ring = RingIndicator(title="TEMP", color=GLOW_ORANGE, unit="\u2103", max_val=80, size=92)
        ring_layout.addWidget(self._rsoc_ring)
        ring_layout.addWidget(self._soh_ring)
        ring_layout.addWidget(self._temp_ring)
        ring_panel.content_layout.addLayout(ring_layout)
        col.addWidget(ring_panel, stretch=3)

        # 运行状态
        status_panel = PanelWidget("\u8fd0\u884c\u72b6\u6001")
        self._status_rows = {}
        for name, color in [
            ("\u5145\u7535\u72b6\u6001", GLOW_CYAN),
            ("\u5faa\u73af\u6b21\u6570", GLOW_ORANGE),
            ("\u9996\u6b21\u4f7f\u7528", TEXT_SECONDARY),
            ("\u6700\u9ad8\u6e29\u5ea6", GLOW_RED),
        ]:
            row = QHBoxLayout()
            row.setSpacing(6)
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
            row.addWidget(dot)
            lbl = _mk_label(name, FONT_SM, TEXT_LABEL)
            lbl.setFixedWidth(64)
            row.addWidget(lbl)
            row.addStretch()
            val = _mk_label("--", FONT_SM, TEXT_VALUE, True)
            row.addWidget(val)
            status_panel.content_layout.addLayout(row)
            self._status_rows[name] = val
        col.addWidget(status_panel, stretch=2)

        return self._wrap(col)

    # ============== 中列 ==============
    def _build_center_column(self):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        # KPI 指标卡
        kpi_panel = PanelWidget("\u5bb9\u91cf\u6307\u6807")
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(4)
        self._kpi_fcc = KpiCard("FCC (mAh)", color=GLOW_CYAN, suffix="")
        self._kpi_rm = KpiCard("RM (mAh)", color=GLOW_BLUE, suffix="")
        self._kpi_rsoc = KpiCard("RSOC", color=GLOW_GREEN, suffix="%")
        self._kpi_current = KpiCard("\u7535\u6d41", color=GLOW_ORANGE, suffix=" mA")
        kpi_grid.addWidget(self._kpi_fcc, 0, 0)
        kpi_grid.addWidget(self._kpi_rm, 0, 1)
        kpi_grid.addWidget(self._kpi_rsoc, 1, 0)
        kpi_grid.addWidget(self._kpi_current, 1, 1)
        kpi_panel.content_layout.addLayout(kpi_grid)
        col.addWidget(kpi_panel, stretch=3)

        # 电池图标 + 容量条
        bat_panel = PanelWidget("\u7535\u6c60\u72b6\u6001")
        bat_layout = QHBoxLayout()
        bat_layout.setSpacing(8)
        self._battery_icon = BatteryIconWidget()
        self._battery_icon.setMinimumSize(100, 130)
        bat_layout.addWidget(self._battery_icon)

        bar_col = QVBoxLayout()
        bar_col.setSpacing(4)
        self._fcc_bar = GradientBar(height=10)
        self._fcc_val = _mk_label("--%", FONT_XS, GLOW_CYAN, True)
        self._rm_bar = GradientBar(height=10)
        self._rm_val = _mk_label("--%", FONT_XS, GLOW_BLUE, True)
        for name, bar, val, color in [
            ("FCC", self._fcc_bar, self._fcc_val, GLOW_CYAN),
            ("RM", self._rm_bar, self._rm_val, GLOW_BLUE),
        ]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lab = _mk_label(name, FONT_XS, TEXT_LABEL)
            lab.setFixedWidth(30)
            row.addWidget(lab)
            row.addWidget(bar, stretch=1)
            val.setFixedWidth(42)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val)
            bar_col.addLayout(row)
        bat_layout.addLayout(bar_col, stretch=1)
        bat_panel.content_layout.addLayout(bat_layout)
        col.addWidget(bat_panel, stretch=2)

        # 电压详情
        volt_panel = PanelWidget("\u7535\u538b\u8be6\u60c5")
        self._volt_bar = GradientBar(height=10)
        self._volt_bar_val = _mk_label("-- mV", FONT_SM, TEXT_VALUE, True)
        self._volt_bar_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v_row1 = QHBoxLayout()
        v_row1.setSpacing(4)
        v_row1.addWidget(_mk_label("\u5f53\u524d\u7535\u538b", FONT_SM, TEXT_LABEL))
        v_row1.addWidget(self._volt_bar, stretch=1)
        v_row1.addWidget(self._volt_bar_val)
        volt_panel.content_layout.addLayout(v_row1)

        self._dv_lbl = _mk_label("\u8bbe\u8ba1\u7535\u538b: -- mV", FONT_SM, TEXT_SECONDARY)
        self._vmin_lbl = _mk_label("\u6700\u4f4e\u7535\u538b: -- mV", FONT_SM, TEXT_SECONDARY)
        self._vmax_lbl = _mk_label("\u6700\u9ad8\u7535\u538b: -- mV", FONT_SM, TEXT_SECONDARY)
        volt_panel.content_layout.addWidget(self._dv_lbl)
        volt_panel.content_layout.addWidget(self._vmin_lbl)
        volt_panel.content_layout.addWidget(self._vmax_lbl)
        col.addWidget(volt_panel, stretch=2)

        return self._wrap(col)

    # ============== 右列 ==============
    def _build_right_column(self):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        # 健康评估
        health_panel = PanelWidget("\u5065\u5eb7\u8bc4\u4f30")
        health_grid = QGridLayout()
        health_grid.setSpacing(4)
        self._health_kpi_soh = KpiCard("SOH", color=GLOW_GREEN, suffix="%")
        self._health_kpi_cycle = KpiCard("\u5faa\u73af\u6b21\u6570", color=GLOW_ORANGE, suffix="")
        health_grid.addWidget(self._health_kpi_soh, 0, 0)
        health_grid.addWidget(self._health_kpi_cycle, 0, 1)
        health_panel.content_layout.addLayout(health_grid)

        degrade_row = QHBoxLayout()
        degrade_row.addWidget(_mk_label("\u8870\u51cf\u7387", FONT_SM, TEXT_LABEL))
        degrade_row.addStretch()
        self._degrade_val = _mk_label("--%", FONT_SM, TEXT_VALUE, True)
        degrade_row.addWidget(self._degrade_val)
        health_panel.content_layout.addLayout(degrade_row)

        self._health_bar = GradientBar(height=8)
        health_panel.content_layout.addWidget(self._health_bar)
        col.addWidget(health_panel, stretch=2)

        # 功率限制
        power_panel = PanelWidget("\u529f\u7387\u9650\u5236")
        self._pl_rows = {}
        for name, desc, color in [
            ("PL1", "\u6301\u7eed\u529f\u7387", GLOW_CYAN),
            ("PL2", "\u7206\u53d1\u529f\u7387", GLOW_ORANGE),
            ("PL4", "\u6781\u9650\u529f\u7387", GLOW_RED),
        ]:
            row = QHBoxLayout()
            row.setSpacing(6)
            lab = _mk_label(name, FONT_SM, color, True)
            lab.setFixedWidth(36)
            row.addWidget(lab)
            val = _mk_label("-- W", FONT_SM, TEXT_VALUE, True)
            row.addWidget(val)
            row.addStretch()
            sub = _mk_label(desc, FONT_XS, TEXT_SECONDARY)
            row.addWidget(sub)
            power_panel.content_layout.addLayout(row)
            self._pl_rows[name] = val
        col.addWidget(power_panel, stretch=1)

        # 充电模式
        mode_panel = PanelWidget("\u5145\u7535\u6a21\u5f0f")
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        self._fast_card = self._mk_mode_card("\u26a1", "\u5feb\u5145", GLOW_GREEN, False)
        self._night_card = self._mk_mode_card("\U0001f319", "\u591c\u5145", GLOW_BLUE, False)
        mode_layout.addWidget(self._fast_card)
        mode_layout.addWidget(self._night_card)
        mode_panel.content_layout.addLayout(mode_layout)
        col.addWidget(mode_panel, stretch=1)

        # 会话统计
        sess_panel = PanelWidget("\u4f1a\u8bdd\u7edf\u8ba1")
        self._sess_labels = {}
        for name in ["\u91c7\u6837\u6b21\u6570", "\u5e73\u5747\u7535\u538b", "\u5e73\u5747\u7535\u6d41", "\u5e73\u5747\u6e29\u5ea6", "\u5e73\u5747\u529f\u7387"]:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = _mk_label(name, FONT_SM, TEXT_LABEL)
            row.addWidget(lbl)
            row.addStretch()
            val = _mk_label("--", FONT_SM, TEXT_VALUE, True)
            row.addWidget(val)
            sess_panel.content_layout.addLayout(row)
            self._sess_labels[name] = val
        col.addWidget(sess_panel, stretch=2)

        return self._wrap(col)

    def _mk_mode_card(self, icon, label, color, active):
        card = QFrame()
        card.setMinimumHeight(70)
        bg = "rgba(0, 80, 100, 0.3)" if active else BG_PANEL_SOLID
        border = color if active else BORDER_ACCENT
        card.setStyleSheet(
            f"background: {bg}; border: 1px solid {border}; "
            f"border-radius: 4px;"
        )
        inner = QVBoxLayout(card)
        inner.setAlignment(Qt.AlignCenter)
        inner.setSpacing(2)
        ic = _mk_label(icon, FONT_LG, color, True)
        ic.setAlignment(Qt.AlignCenter)
        inner.addWidget(ic)
        lb = _mk_label(label, FONT_SM, color, True)
        lb.setAlignment(Qt.AlignCenter)
        inner.addWidget(lb)
        st = _mk_label("ON" if active else "OFF", FONT_XS, color if active else TEXT_SECONDARY, True)
        st.setAlignment(Qt.AlignCenter)
        inner.addWidget(st)
        card._state_label = st
        return card

    def _wrap(self, layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def _build_bottom_bar(self):
        bar = QFrame()
        bar.setFixedHeight(28)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)
        self._runtime_lbl = _mk_label("\u8fd0\u884c: 00:00:00", FONT_BASE, TEXT_SECONDARY)
        layout.addWidget(self._runtime_lbl)
        layout.addStretch()
        self._timestamp_lbl = _mk_label("--:--:--", FONT_BASE, TEXT_SECONDARY)
        layout.addWidget(self._timestamp_lbl)
        return bar

    # ============== 控制逻辑 ==============
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
        self._title_bar.set_left_text("\u7cfb\u7edf\u72b6\u6001\uff1a\u76d1\u63a7\u4e2d")
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
        self._title_bar.set_left_text("\u7cfb\u7edf\u72b6\u6001\uff1a\u5df2\u505c\u6b62")
        logger.info("监控已停止")

    @Slot(BatterySnapshot)
    def _on_snapshot(self, snapshot: BatterySnapshot):
        self._view_model.process_snapshot(snapshot)
        self._update_gauge(snapshot)
        self._update_rings(snapshot)
        self._update_status_rows(snapshot)
        self._update_battery_icon(snapshot)
        self._update_kpis(snapshot)
        self._update_capacity_bars(snapshot)
        self._update_voltage_details(snapshot)
        self._update_health(snapshot)
        self._update_power_limits(snapshot)
        if self._chart_window is not None and self._chart_window.isVisible():
            self._chart_window.on_snapshot(snapshot)
        self._timestamp_lbl.setText(snapshot.timestamp.strftime('%H:%M:%S'))
        self._title_bar.set_right_text(f"\u65f6\u95f4\uff1a{snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
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
        self._update_mode_card(self._fast_card, GLOW_GREEN, is_fast)
        self._update_mode_card(self._night_card, GLOW_BLUE, is_night)

    def _update_mode_card(self, card, color, active):
        bg = "rgba(0, 80, 60, 0.4)" if active else BG_PANEL_SOLID
        border = color if active else BORDER_ACCENT
        card.setStyleSheet(
            f"background: {bg}; border: 1px solid {border}; border-radius: 4px;"
        )
        if hasattr(card, '_state_label'):
            card._state_label.setText("ON" if active else "OFF")
            c = color if active else TEXT_SECONDARY
            card._state_label.setStyleSheet(
                f"color: {c}; font-size: {FONT_XS}px; font-weight: bold; "
                f"border: none; background: transparent;"
            )

    # ============== 数据更新 ==============
    def _update_gauge(self, s):
        self._gauge.setValue(s.predicted_life_months)

    def _update_rings(self, s):
        self._rsoc_ring.setValue(float(s.rsoc))
        self._soh_ring.setValue(float(s.soh))
        self._temp_ring.setValue(s.temperature)

    def _update_status_rows(self, s):
        state_text, state_color = self._view_model.format_charge_state(s.charge_state)
        if "\u5145\u7535\u72b6\u6001" in self._status_rows:
            self._status_rows["\u5145\u7535\u72b6\u6001"].setText(state_text)
            self._status_rows["\u5145\u7535\u72b6\u6001"].setStyleSheet(
                f"color: {state_color}; font-size: {FONT_SM}px; font-weight: bold; "
                f"border: none; background: transparent;"
            )
        if "\u5faa\u73af\u6b21\u6570" in self._status_rows:
            self._status_rows["\u5faa\u73af\u6b21\u6570"].setText(str(s.cycle_count))
        if "\u9996\u6b21\u4f7f\u7528" in self._status_rows:
            self._status_rows["\u9996\u6b21\u4f7f\u7528"].setText(s.first_usage_time)
        if "\u6700\u9ad8\u6e29\u5ea6" in self._status_rows:
            self._status_rows["\u6700\u9ad8\u6e29\u5ea6"].setText(f"{s.max_temperature:.1f}\u2103")

    def _update_battery_icon(self, s):
        self._battery_icon.set_data(s.rsoc, s.charge_state)

    def _update_kpis(self, s):
        self._kpi_fcc.set_value(s.fcc)
        self._kpi_rm.set_value(s.rm)
        self._kpi_rsoc.set_value(s.rsoc)
        self._kpi_current.set_value(s.current)
        self._health_kpi_soh.set_value(s.soh)
        self._health_kpi_cycle.set_value(s.cycle_count)

    def _update_capacity_bars(self, s):
        fcc_pct, rm_pct = self._view_model.calculate_capacity_percentages(s)
        self._fcc_bar.setValue(fcc_pct, GLOW_CYAN)
        self._fcc_val.setText(f"{fcc_pct:.1f}%")
        self._rm_bar.setValue(rm_pct, GLOW_BLUE)
        self._rm_val.setText(f"{rm_pct:.1f}%")

    def _update_voltage_details(self, s):
        dv = s.dv if s.dv > 0 else 1
        volt_pct = min(100.0, s.voltage / dv * 100)
        if s.voltage > dv * 1.05:
            vc = GLOW_RED
        elif s.voltage < dv * 0.9:
            vc = GLOW_ORANGE
        else:
            vc = GLOW_CYAN
        self._volt_bar.setValue(volt_pct, vc)
        self._volt_bar_val.setText(f"{s.voltage} mV")
        self._dv_lbl.setText(f"\u8bbe\u8ba1\u7535\u538b: {s.dv} mV")
        self._vmin_lbl.setText(f"\u6700\u4f4e\u7535\u538b: {s.min_voltage} mV" if s.min_voltage else "\u6700\u4f4e\u7535\u538b: -- mV")
        self._vmax_lbl.setText(f"\u6700\u9ad8\u7535\u538b: {s.max_voltage} mV" if s.max_voltage else "\u6700\u9ad8\u7535\u538b: -- mV")

    def _update_health(self, s):
        health = s.fcc / s.dc * 100 if s.dc > 0 else 0
        degrade = 100 - health
        self._health_bar.setValue(health, GLOW_GREEN if health > 80 else (GLOW_ORANGE if health > 50 else GLOW_RED))
        dc = GLOW_GREEN if degrade < 20 else (GLOW_ORANGE if degrade < 50 else GLOW_RED)
        self._degrade_val.setText(f"{degrade:.1f}%")
        self._degrade_val.setStyleSheet(
            f"color: {dc}; font-size: {FONT_SM}px; font-weight: bold; "
            f"border: none; background: transparent;"
        )

    def _update_power_limits(self, s):
        for name, val in [("PL1", s.pl1), ("PL2", s.pl2), ("PL4", s.pl4)]:
            if name in self._pl_rows:
                self._pl_rows[name].setText(f"{val} W")

    # ============== 窗口操作 ==============
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
