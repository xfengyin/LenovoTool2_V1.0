"""寿命预测组件：显示预计可用寿命"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QLinearGradient, QPen
from PySide6.QtWidgets import QWidget


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