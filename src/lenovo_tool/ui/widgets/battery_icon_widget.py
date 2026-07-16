"""电池图标组件：显示电量状态和充电状态

使用相对尺寸绘制，支持自适应缩放，颜色使用统一常量。
"""

from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient, QPolygon
from PySide6.QtWidgets import QWidget, QSizePolicy

from lenovo_tool.ui.styles.main_style import (
    BAR_BG, BORDER_SUBTLE, TEXT_PRIMARY,
    STATUS_GOOD, STATUS_WARN, STATUS_BAD,
)


class BatteryIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rsoc = 0
        self._charge_state = "idle"
        self.setMinimumSize(80, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        painter.setPen(QPen(QColor(BORDER_SUBTLE), 2))
        painter.setBrush(QColor(BAR_BG))
        head_w = bw * 0.35
        head_h = bh * 0.08
        painter.drawRoundedRect(QRectF(bx + bw / 2 - head_w / 2, by - head_h, head_w, head_h), 3, 3)
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), 6, 6)
        margin = 4
        level_h = (bh - margin * 2) * self._rsoc / 100
        level_y = by + bh - margin - level_h
        if self._rsoc > 60:
            level_color = QColor(STATUS_GOOD)
        elif self._rsoc > 30:
            level_color = QColor(STATUS_WARN)
        else:
            level_color = QColor(STATUS_BAD)
        gradient = QLinearGradient(0, level_y, 0, by + bh)
        gradient.setColorAt(0, level_color)
        gradient.setColorAt(1, QColor(level_color.red() * 0.6, level_color.green() * 0.6, level_color.blue() * 0.6))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(bx + margin, level_y, bw - margin * 2, level_h), 3, 3)
        if self._charge_state == "charging":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(STATUS_WARN))
            pcx = w / 2
            pcy = by + bh * 0.45
            pts = QPolygon([QPoint(int(pcx - 3), int(pcy - 15)), QPoint(int(pcx + 5), int(pcy - 2)), QPoint(int(pcx), int(pcy - 2)), QPoint(int(pcx + 3), int(pcy + 12)), QPoint(int(pcx - 5), int(pcy + 1)), QPoint(int(pcx), int(pcy + 1))])
            painter.drawPolygon(pts)
        painter.setPen(QColor(TEXT_PRIMARY))
        pct_font = QFont("Consolas", 16)
        pct_font.setBold(True)
        painter.setFont(pct_font)
        painter.drawText(QRectF(bx, by + bh * 0.3, bw, bh * 0.4), Qt.AlignCenter, f"{self._rsoc}%")
        painter.end()
