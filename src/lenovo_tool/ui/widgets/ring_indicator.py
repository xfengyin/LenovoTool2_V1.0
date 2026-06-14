"""Ring / donut progress indicator for dashboard display.

Shows a value as a colored arc ring with percentage or raw value in center.
"""

import math

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QRadialGradient, QFont,
)
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class RingIndicator(QWidget):
    """Circular ring gauge showing a percentage or value.

    Used for RSOC, SOH, cycle life etc.
    """

    def __init__(
        self,
        title: str = "",
        max_val: float = 100,
        color: str = "#00e5c8",
        unit: str = "%",
        size: int = 80,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._value = 0.0
        self._max = max_val
        self._color = color
        self._unit = unit

        self.setFixedSize(size, size)

    def setValue(self, value: float) -> None:
        self._value = min(value, self._max)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h)
        pen_width = side * 0.12

        # Center the ring
        margin = pen_width / 2 + 2
        rect = QRectF(margin, margin, side - margin * 2, side - margin * 2)

        # Background ring (dark)
        bg_pen = QPen(QColor("#1a2a3a"), pen_width)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Value ring
        ratio = self._value / self._max if self._max > 0 else 0
        angle = int(ratio * 360 * 16)

        color = QColor(self._color)
        if ratio < 0.3:
            color = QColor("#ff5252")
        elif ratio < 0.6:
            color = QColor("#ffab40")

        val_pen = QPen(color, pen_width)
        val_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(val_pen)
        # Start from top (90 degrees = 16*90 = 1440)
        painter.drawArc(rect, 1440, -angle)

        # Center text
        painter.setPen(QColor("#e0e8f0"))
        font = painter.font()
        font.setPixelSize(int(side * 0.22))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{int(self._value)}")

        painter.end()