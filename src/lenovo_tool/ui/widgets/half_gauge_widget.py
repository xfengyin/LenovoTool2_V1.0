"""半圆仪表盘组件：显示预计可用寿命（月）"""

import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget


class HalfGaugeWidget(QWidget):
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

        title_h = 16
        bottom_margin = 20
        arc_area_top = title_h + 4
        arc_area_bottom = h - bottom_margin
        cx = w / 2
        max_r_by_w = (w / 2) - 24
        max_r_by_h = (arc_area_bottom - arc_area_top) / 2 - 4
        radius = min(max_r_by_w, max_r_by_h)
        cy = arc_area_top + radius

        painter.setPen(QColor("#7a8fa3"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            QRectF(0, 4, w, title_h),
            Qt.AlignCenter, "预计可用寿命"
        )

        arc_pen_w = radius * 0.14
        bg_pen = QPen(QColor("#1a2a3a"), arc_pen_w)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        arc_rect = QRectF(cx - radius, cy - radius,
                          radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 180 * 16)

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