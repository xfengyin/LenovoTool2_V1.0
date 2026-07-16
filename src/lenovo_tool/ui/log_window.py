"""日志数据窗口 — 企业级监控大屏风格。

全寄存器扫描，带分类筛选、搜索、CSV导出，
深色主题一致，专业数据表格展示。
"""

from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QLabel, QFrame,
    QLineEdit, QGridLayout,
)

from lenovo_tool.core.data_models import AppConfig, LogSnapshot
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.core.register_definitions import (
    REGISTER_CATALOG,
)
from lenovo_tool.services.csv_export import CSVExportService
from lenovo_tool.services.log_data_service import LogDataService
from lenovo_tool.ui.dialogs.error_dialog import show_warning
from lenovo_tool.ui.styles.main_style import (
    global_stylesheet, TEXT_ACCENT, TEXT_SECONDARY,
    TEXT_LABEL, TEXT_PRIMARY, TEXT_VALUE,
    BG_CARD, BG_INPUT, BORDER_SUBTLE,
    STATUS_GOOD, STATUS_WARN,
)
from lenovo_tool.ui.workers.log_worker import LogWorker


# 分类颜色映射
_CATEGORY_COLORS = {
    1: "#00e5c8",  # Word(无符号)
    2: "#ffab40",  # Word(有符号)
    3: "#e040fb",  # Word(HEX)
    4: "#ff5252",  # 温度
    5: "#448aff",  # 模式位
    6: "#7a8fa3",  # SMBus消息
    7: "#00e676",  # Block子字段
    8: "#00e5c8",  # SOH
    9: "#ffab40",  # 寿命预测
}


class LogWindow(QDialog):
    """全寄存器扫描日志窗口。"""

    HEADERS = ["#", "寄存器名称", "地址", "数值", "单位", "分类"]

    INTERVAL_MAP = {
        "300ms": 0.3,
        "500ms": 0.5,
        "1s": 1.0,
        "2s": 2.0,
        "5s": 5.0,
    }

    _CATEGORY_NAMES = {
        1: "Word(无符号)",
        2: "Word(有符号)",
        3: "Word(HEX)",
        4: "温度",
        5: "模式位",
        6: "SMBus消息",
        7: "Block子字段",
        8: "SOH(计算)",
        9: "寿命预测(HEX)",
    }

    def __init__(self, dll, config, parent=None):
        super().__init__(parent)
        self._dll = dll
        self._config = config
        self._log_service = LogDataService(dll)
        self._csv_service = None
        self._log_worker = None
        self._scan_count = 0

        self.setWindowTitle("日志数据 — 全寄存器扫描")
        self.setMinimumSize(1000, 720)
        self.resize(1100, 780)
        self.setStyleSheet(global_stylesheet())
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # 顶部控制栏
        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(8)

        title = QLabel("📋 日志数据")
        title.setStyleSheet(
            f"color: {TEXT_ACCENT}; font-size: 15px; "
            f"font-weight: bold; border: none; "
            f"background: transparent;"
        )

        self._scan_btn = QPushButton("🔍 单次扫描")
        self._start_log_btn = QPushButton("▶ 开始记录")
        self._stop_log_btn = QPushButton("■ 停止记录")
        self._stop_log_btn.setEnabled(False)
        self._stop_log_btn.setObjectName("DangerBtn")

        for btn in (
            self._scan_btn, self._start_log_btn,
            self._stop_log_btn,
        ):
            btn.setCursor(Qt.PointingHandCursor)

        # 间隔选择
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(
            list(self.INTERVAL_MAP.keys())
        )
        self._interval_combo.setCurrentText("1s")
        self._interval_combo.setFixedWidth(80)

        interval_lbl = QLabel("间隔:")
        interval_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 11px; "
            f"border: none; background: transparent;"
        )

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self._scan_btn)
        header_layout.addWidget(self._start_log_btn)
        header_layout.addWidget(self._stop_log_btn)
        header_layout.addSpacing(8)
        header_layout.addWidget(interval_lbl)
        header_layout.addWidget(self._interval_combo)

        root.addWidget(header)

        # 搜索栏 + 分类筛选 + 统计
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        search_lbl = QLabel("搜索:")
        search_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 11px; "
            f"border: none; background: transparent;"
        )
        filter_row.addWidget(search_lbl)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "输入寄存器名称筛选..."
        )
        self._search_input.setFixedWidth(200)
        self._search_input.setStyleSheet(
            f"background: {BG_INPUT}; color: {TEXT_VALUE}; "
            f"border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: 4px; padding: 4px 8px; "
            f"font-size: 11px;"
        )
        self._search_input.textChanged.connect(
            self._on_search_changed
        )
        filter_row.addWidget(self._search_input)

        cat_lbl = QLabel("分类:")
        cat_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 11px; "
            f"border: none; background: transparent;"
        )
        filter_row.addWidget(cat_lbl)

        self._category_combo = QComboBox()
        self._category_combo.addItem("全部分类")
        for cat_id, cat_name in sorted(
            self._CATEGORY_NAMES.items()
        ):
            self._category_combo.addItem(cat_name, cat_id)
        self._category_combo.setFixedWidth(130)
        self._category_combo.currentIndexChanged.connect(
            self._on_filter_changed
        )
        filter_row.addWidget(self._category_combo)

        filter_row.addStretch()

        # 统计信息
        self._count_lbl = QLabel("寄存器: 0")
        self._count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; "
            f"border: none; background: transparent;"
        )
        filter_row.addWidget(self._count_lbl)

        self._time_lbl = QLabel("--:--:--")
        self._time_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; "
            f"border: none; background: transparent;"
        )
        filter_row.addWidget(self._time_lbl)

        root.addLayout(filter_row)

        # 状态行
        self._status_lbl = QLabel("就绪 — 点击单次扫描开始")
        self._status_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; "
            f"border: none; background: transparent;"
        )
        root.addWidget(self._status_lbl)

        # 数据表格
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        # 表格深色样式
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_INPUT};
                alternate-background-color: {BG_CARD};
                color: {TEXT_PRIMARY};
                gridline-color: {BORDER_SUBTLE};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                selection-background-color: {TEXT_ACCENT};
                selection-color: #0d1520;
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 3px 6px;
                border: none;
            }}
            QHeaderView::section {{
                background-color: #1b2d42;
                color: {TEXT_SECONDARY};
                font-weight: bold;
                font-size: 11px;
                padding: 5px 8px;
                border: none;
                border-right: 1px solid {BORDER_SUBTLE};
                border-bottom: 1px solid {BORDER_SUBTLE};
            }}
        """)

        # 列宽
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        for col in (2, 3, 4, 5):
            header_view.setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )

        root.addWidget(self._table, stretch=1)

        # 保存原始数据用于筛选
        self._raw_items = []
        self._current_filter = ""
        self._current_category = -1

    def _setup_connections(self):
        self._scan_btn.clicked.connect(self._on_scan)
        self._start_log_btn.clicked.connect(
            self._on_start_log
        )
        self._stop_log_btn.clicked.connect(
            self._on_stop_log
        )

    def _on_search_changed(self, text):
        self._current_filter = text.lower()
        self._apply_filters()

    def _on_filter_changed(self, index):
        if index <= 0:
            self._current_category = -1
        else:
            self._current_category = (
                self._category_combo.currentData()
            )
        self._apply_filters()

    def _apply_filters(self):
        """应用搜索和分类筛选。"""
        filtered = []
        for item_data in self._raw_items:
            name = item_data["name"]
            cat = item_data["cat_id"]

            if (
                self._current_filter
                and self._current_filter not in name.lower()
            ):
                continue

            if (
                self._current_category >= 0
                and cat != self._current_category
            ):
                continue

            filtered.append(item_data)

        self._render_table(filtered)
        self._count_lbl.setText(
            f"寄存器: {len(filtered)}/{len(self._raw_items)}"
        )

    def _on_scan(self):
        self._status_lbl.setText("⏳ 扫描中...")
        try:
            snapshot = (
                self._log_service.fetch_log_snapshot()
            )
            self._scan_count += 1
            self._process_snapshot(snapshot)
            self._status_lbl.setText(
                f"✅ 扫描完成 — {len(snapshot.values)} 个寄存器 "
                f"(第 {self._scan_count} 次)"
            )
            self._time_lbl.setText(
                datetime.now().strftime("%H:%M:%S")
            )
        except Exception as e:
            show_warning(self, "扫描错误", str(e))
            self._status_lbl.setText("❌ 扫描失败")

    def _on_start_log(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "/", "CSV (*.csv)"
        )
        if not filepath:
            return

        self._csv_service = CSVExportService(
            filepath,
            delimiter=self._config.csv_delimiter,
            encoding=self._config.csv_encoding,
        )
        self._csv_service.open()

        interval_text = (
            self._interval_combo.currentText()
        )
        # 优先使用 UI 选择；缺省回退到配置（settings.yaml 中的
        # polling.log_scan_interval_ms）转换为秒
        interval_sec = self.INTERVAL_MAP.get(interval_text)
        if interval_sec is None:
            interval_sec = max(
                0.1, self._config.log_scan_interval_ms / 1000.0
            )

        self._log_worker = LogWorker(
            self._log_service, interval_sec
        )
        self._log_worker.data_ready.connect(
            self._on_log_data
        )
        self._log_worker.start()

        self._start_log_btn.setEnabled(False)
        self._stop_log_btn.setEnabled(True)
        self._scan_btn.setEnabled(False)
        self._status_lbl.setText(
            f"🔴 记录中... 间隔 {interval_text}"
        )

    def _on_stop_log(self):
        if self._log_worker:
            self._log_worker.stop()
            self._log_worker = None
        if self._csv_service:
            self._csv_service.close()
            self._csv_service = None

        self._start_log_btn.setEnabled(True)
        self._stop_log_btn.setEnabled(False)
        self._scan_btn.setEnabled(True)
        self._status_lbl.setText("就绪")

    @Slot(LogSnapshot)
    def _on_log_data(self, snapshot):
        self._scan_count += 1
        self._process_snapshot(snapshot)
        self._time_lbl.setText(
            datetime.now().strftime("%H:%M:%S")
        )
        self._status_lbl.setText(
            f"🔴 记录中... #{self._scan_count} "
            f"— {len(snapshot.values)} 寄存器"
        )
        if self._csv_service:
            row: dict[str, object] = {}
            if self._config.csv_include_timestamp:
                row["time"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            row.update(snapshot.values)
            self._csv_service.write_row(row)

    def _process_snapshot(self, snapshot):
        """解析快照为结构化数据并应用筛选。"""
        from lenovo_tool.core.register_definitions import (
            RegisterCategory,
        )

        items = []
        for name, value in snapshot.values.items():
            info = REGISTER_CATALOG.get(name)
            addr_str = (
                f"0x{info.address:02X}" if info else "--"
            )
            unit = snapshot.units.get(name, "-")
            cat_id = info.category.value if info else 0
            cat_name = self._CATEGORY_NAMES.get(
                cat_id, "-"
            )

            if info and info.category in (
                RegisterCategory.WORD_HEX,
                RegisterCategory.PREDICTED_HEX,
            ):
                val_str = str(value)
            elif isinstance(value, float):
                val_str = f"{value:.1f}"
            else:
                val_str = str(value)

            items.append({
                "name": name,
                "addr": addr_str,
                "val_str": val_str,
                "unit": unit,
                "cat_name": cat_name,
                "cat_id": cat_id,
            })

        self._raw_items = items
        self._apply_filters()

    def _render_table(self, items):
        """渲染筛选后的数据到表格。"""
        self._table.setRowCount(len(items))

        for row, item_data in enumerate(items):
            row_num = row + 1
            cat_id = item_data["cat_id"]
            cat_color = _CATEGORY_COLORS.get(
                cat_id, TEXT_PRIMARY
            )

            texts = [
                str(row_num),
                item_data["name"],
                item_data["addr"],
                item_data["val_str"],
                item_data["unit"],
                item_data["cat_name"],
            ]

            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)

                if col in (0, 2, 3):
                    item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter
                    )

                # 值列加粗+颜色
                if col == 3:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor(cat_color))

                # 分类列颜色
                if col == 5:
                    item.setForeground(QColor(cat_color))

                # 地址列等宽字体
                if col == 2:
                    item.setFont(QFont("Consolas", 10))

                self._table.setItem(row, col, item)

    def closeEvent(self, event):
        self._on_stop_log()
        super().closeEvent(event)
