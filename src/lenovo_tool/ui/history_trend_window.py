"""历史趋势查询窗口。

提供历史电池数据的查询、摘要统计、CSV 导出与旧数据清理：
- 时间范围 + 指标选择查询
- 表格展示 + 摘要（最大/最小/平均）
- 会话过滤
- 一键清理过期数据
- CSV 导出查询结果
"""

import csv
import logging
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lenovo_tool.services.history_repository import HistoryRepository
from lenovo_tool.ui.styles.main_style import TEXT_PRIMARY, global_stylesheet

logger = logging.getLogger(__name__)


class HistoryTrendWindow(QMainWindow):
    """历史数据查询窗口。"""

    # (显示名, 指标键)
    METRICS: list[tuple[str, str]] = [
        ("电压 (mV)", "voltage"),
        ("电流 (mA)", "current"),
        ("温度 (℃)", "temperature"),
        ("RSOC (%)", "rsoc"),
        ("SOH (%)", "soh"),
        ("FCC (mAh)", "fcc"),
        ("RM (mAh)", "rm"),
        ("电芯1 (mV)", "cell1"),
        ("电芯2 (mV)", "cell2"),
        ("电芯3 (mV)", "cell3"),
        ("电芯4 (mV)", "cell4"),
        ("FET 温度 (℃)", "fet_temp"),
    ]

    def __init__(self, repo: HistoryRepository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._init_ui()
        self.setStyleSheet(global_stylesheet())
        self.resize(900, 600)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        toolbar.addWidget(QLabel("开始:"))
        self._start_edit = QDateTimeEdit(datetime.now() - timedelta(hours=1))
        self._start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._start_edit.setCalendarPopup(True)
        toolbar.addWidget(self._start_edit)

        toolbar.addWidget(QLabel("结束:"))
        self._end_edit = QDateTimeEdit(datetime.now())
        self._end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._end_edit.setCalendarPopup(True)
        toolbar.addWidget(self._end_edit)

        toolbar.addWidget(QLabel("指标:"))
        self._metric_combo = QComboBox()
        for name, _ in self.METRICS:
            self._metric_combo.addItem(name)
        toolbar.addWidget(self._metric_combo)

        self._query_btn = QPushButton("查询")
        self._query_btn.setCursor(Qt.PointingHandCursor)
        self._query_btn.clicked.connect(self._on_query)
        toolbar.addWidget(self._query_btn)

        self._export_btn = QPushButton("导出CSV")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(self._export_btn)

        toolbar.addWidget(QLabel("会话:"))
        self._session_combo = QComboBox()
        self._session_combo.addItem("(全部)", "")
        for sid in self._repo.get_session_ids():
            self._session_combo.addItem(sid[:18] + "...", sid)
        toolbar.addWidget(self._session_combo)

        self._cleanup_btn = QPushButton("清理旧数据")
        self._cleanup_btn.setCursor(Qt.PointingHandCursor)
        self._cleanup_btn.clicked.connect(self._on_cleanup)
        toolbar.addWidget(self._cleanup_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 摘要
        self._summary_lbl = QLabel("无数据")
        self._summary_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; padding: 4px;"
        )
        layout.addWidget(self._summary_lbl)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["时间", "数值"])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table)

        # 状态栏
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")

    def _on_query(self) -> None:
        """执行查询并刷新表格与摘要。"""
        start = self._start_edit.dateTime().toPython()
        end = self._end_edit.dateTime().toPython()
        idx = self._metric_combo.currentIndex()
        name, key = self.METRICS[idx]

        try:
            data = self._repo.query_range(start, end, key)
        except Exception as e:
            QMessageBox.warning(self, "查询失败", str(e))
            return

        self._table.setRowCount(len(data))
        for i, (ts, val) in enumerate(data):
            self._table.setItem(
                i, 0, QTableWidgetItem(ts.strftime("%Y-%m-%d %H:%M:%S"))
            )
            self._table.setItem(i, 1, QTableWidgetItem(f"{val:.2f}"))

        if data:
            vals = [v for _, v in data]
            avg = sum(vals) / len(vals)
            self._summary_lbl.setText(
                f"共 {len(data)} 条 | 最大: {max(vals):.2f} | "
                f"最小: {min(vals):.2f} | 平均: {avg:.2f}"
            )
        else:
            self._summary_lbl.setText("无数据")
        self.statusBar().showMessage(f"查询完成: {len(data)} 条记录")

    def _on_export(self) -> None:
        """导出当前表格内容为 CSV。"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出查询结果",
            f"history_export_{datetime.now():%Y%m%d_%H%M%S}.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "数值"])
                for i in range(self._table.rowCount()):
                    writer.writerow([
                        self._table.item(i, 0).text()
                        if self._table.item(i, 0)
                        else "",
                        self._table.item(i, 1).text()
                        if self._table.item(i, 1)
                        else "",
                    ])
            self.statusBar().showMessage(f"已导出到 {path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _on_cleanup(self) -> None:
        """删除超过保留期的数据。"""
        days = self._get_retention_days()
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"将删除 {days} 天前的所有数据，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            count = self._repo.cleanup_old(days)
            QMessageBox.information(
                self, "清理完成", f"已删除 {count} 条旧记录"
            )

    @staticmethod
    def _get_retention_days() -> int:
        """从 ConfigManager 读取保留期，失败时回退 30 天。"""
        try:
            from lenovo_tool.utils.config_manager import ConfigManager

            cfg = ConfigManager().get()
            if cfg is not None and hasattr(cfg, "history_retention_days"):
                return int(cfg.history_retention_days)
        except Exception as e:
            logger.warning("无法读取 history_retention_days: %s", e)
        return 30
