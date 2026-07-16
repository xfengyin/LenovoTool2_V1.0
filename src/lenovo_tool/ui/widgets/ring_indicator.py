"""Ring / donut progress indicator for dashboard display.

Shows a value as a colored arc ring with percentage or raw value in center.
Includes smooth value transition animation.
"""

from PySide6.QtCore import Qt, QRectF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QColor, QPainter, QPen, QFont,
)
from PySide6.QtWidgets import QWidget

from lenovo_tool.ui.styles.main_style import (
    BAR_BG, TEXT_PRIMARY, STATUS_BAD, STATUS_WARN,
)


class RingIndicator(QWidget):
    """Circular ring gauge showing a percentage or value.

    Used for RSOC, SOH, temperature etc.
    Includes smooth animation and unit display.
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
        self._value: float = 0.0
        self._display_value: float = 0.0
        self._max = max_val
        self._color = color
        self._unit = unit
        self._anim: QPropertyAnimation | None = None

        self.setFixedSize(size, size)

    # --- Qt property for animation ---
    def _get_display_value(self) -> float:
        return self._display_value

    def _set_display_value(self, v: float) -> None:
        self._display_value = v
        self.update()

    displayValue = Property(float, _get_display_value, _set_display_value)

    def setValue(self, value: float) -> None:
        """Set target value with smooth animation."""
        self._value = min(value, self._max)
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(500)
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(self._value)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h)
        pen_width = side * 0.12

        margin = pen_width / 2 + 2
        rect = QRectF(margin, margin, side - margin * 2, side - margin * 2)

        # Background ring
        bg_pen = QPen(QColor(BAR_BG), pen_width)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Value ring
        ratio = self._display_value / self._max if self._max > 0 else 0
        angle = int(ratio * 360 * 16)

        color = QColor(self._color)
        if ratio < 0.3:
            color = QColor(STATUS_BAD)
        elif ratio < 0.6:
            color = QColor(STATUS_WARN)

        val_pen = QPen(color, pen_width)
        val_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(val_pen)
        painter.drawArc(rect, 1440, -angle)

        # Center text: value + unit
        painter.setPen(QColor(TEXT_PRIMARY))
        font = QFont("Consolas")
        font.setPixelSize(int(side * 0.22))
        font.setBold(True)
        painter.setFont(font)
        text = f"{int(self._display_value)}"
        if self._unit:
            text += self._unit
        painter.drawText(rect, Qt.AlignCenter, text)

        painter.end()
