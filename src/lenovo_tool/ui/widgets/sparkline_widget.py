"""Mini sparkline chart for embedding in dashboard panels.

Renders a tiny real-time line chart with a filled area underneath.
Optimized for small spaces (40-80px height).
"""

import time
from collections import deque

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout


class SparklineWidget(QWidget):
    """Compact real-time sparkline with title and current value."""

    def __init__(
        self,
        title: str,
        unit: str = "",
        color: str = "#00e5c8",
        max_points: int = 60,
        height: int = 50,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._color = color
        self._values: deque[float] = deque(maxlen=max_points)
        self.setFixedHeight(height)

        # Title + value at top
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: #7a8fa3; font-size: 10px; "
            f"font-weight: bold; border: none; background: transparent;"
        )
        self._value_lbl = QLabel("--")
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold; "
            f"font-family: Consolas, monospace; border: none; background: transparent;"
        )

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._title_lbl)
        header.addStretch()
        header.addWidget(self._value_lbl)
        if unit:
            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet(
                f"color: #5a6a7a; font-size: 9px; border: none; background: transparent;"
            )
            header.addWidget(unit_lbl)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)

    def append(self, value: float) -> None:
        self._values.append(value)
        self._value_lbl.setText(f"{value:,.0f}")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() - 22  # leave room for header text
        y_offset = 20

        if h <= 0 or w < 2:
            return

        vals = list(self._values)
        vmin = min(vals) if len(vals) > 1 else vals[0] - 10
        vmax = max(vals) if len(vals) > 1 else vals[0] + 10
        vrange = vmax - vmin
        if vrange == 0:
            vrange = 1.0

        # Build path
        path = QPainterPath()
        step = w / max(len(vals) - 1, 1)
        for i, v in enumerate(vals):
            x = i * step
            y = y_offset + h - ((v - vmin) / vrange) * h
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Fill gradient
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, y_offset + h)
        fill_path.lineTo(0, y_offset + h)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, y_offset, 0, y_offset + h)
        c = QColor(self._color)
        gradient.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 60))
        gradient.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 5))
        painter.fillPath(fill_path, gradient)

        # Stroke line
        pen = QPen(QColor(self._color), 1.8)
        painter.setPen(pen)
        painter.drawPath(path)

        # Current value dot
        if vals:
            last_x = (len(vals) - 1) * step
            last_y = y_offset + h - ((vals[-1] - vmin) / vrange) * h
            painter.setBrush(QColor(self._color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(last_x - 3, last_y - 3, 6, 6))

        painter.end()