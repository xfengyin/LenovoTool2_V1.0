"""Custom-drawn circular gauge for battery life prediction.

Ported from legacy LifePredict.py Drawing class with:
- Clean separation of geometry/painting and data
- DPI-aware scaling
- Proper sizeHint/minimumSizeHint for layout
- Color configuration as instance attributes
"""

import math

from PySide6.QtCore import Qt, QRectF, Signal, QPoint, QPointF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPolygon,
    QRadialGradient,
)
from PySide6.QtWidgets import QFrame, QLCDNumber, QWidget


class GaugeWidget(QWidget):
    """Circular gauge displaying predicted battery life (0-36 months).

    Features a 3-color arc (green/blue/red) with a pointer and LCD display.
    """

    value_changed = Signal(int)

    MIN_VALUE: int = 0
    MAX_VALUE: int = 36

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(200, 150)

        self._value: int = 0
        self._title: str = "预计可用寿命（月）"

        self.pieColorStart = QColor(63, 191, 127)   # Green
        self.pieColorMid = QColor(63, 127, 191)      # Blue
        self.pieColorEnd = QColor(203, 72, 72)       # Red
        self.pointerColor = QColor(72, 203, 203)     # Cyan

        self._font = QFont("Microsoft YaHei", 8)
        self._font.setBold(True)

        self._lcd = QLCDNumber(self)
        self._lcd.setSmallDecimalPoint(False)
        self._lcd.setDigitCount(2)
        self._lcd.setFrameStyle(QFrame.NoFrame)
        self._lcd.setSegmentStyle(QLCDNumber.Flat)
        self._lcd.setStyleSheet(
            "color: rgb(115, 251, 253); background: transparent;"
        )

        self._startAngle = 45
        self._endAngle = 45
        self._scaleMajor = 8

    def setValue(self, value: int) -> None:
        """Set the gauge value (0-36 months)."""
        if 0 <= value <= self.MAX_VALUE:
            self._value = value
            self.value_changed.emit(value)
            self.update()

    def value(self) -> int:
        return self._value

    def setTitle(self, title: str) -> None:
        self._title = title
        self.update()

    # -- Event handlers ------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        width = self.width()
        height = self.height()

        painter = QPainter(self)
        painter.translate(width / 2, height / 2)

        side = min(width, height)
        painter.scale(side / 200.0, side / 200.0)

        painter.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing
        )

        self._drawColorPie(painter)
        self._drawPointer(painter)
        self._drawTicks(painter)
        self._drawLabels(painter)
        self._drawTitle(painter)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Reposition the LCD display when the widget is resized."""
        super().resizeEvent(event)
        self._lcd.setGeometry(100, 120, 30, 30)

    # -- Private drawing methods ---------------------------------------------

    def _drawColorPie(self, painter: QPainter) -> None:
        painter.save()
        radius = 99
        painter.setPen(Qt.NoPen)
        rect = QRectF(-radius, -radius, radius * 2, radius * 2)

        angleAll = 360.0 - self._startAngle - self._endAngle
        angleStart = angleAll * 0.25
        angleMid = angleAll * 0.5
        angleEnd = angleAll * 0.25

        ratio = 0.8

        # Green segment
        rg = QRadialGradient(0, 0, radius, 0, 0)
        rg.setColorAt(0, Qt.transparent)
        rg.setColorAt(ratio, Qt.transparent)
        rg.setColorAt(ratio + 0.01, self.pieColorStart)
        rg.setColorAt(1, self.pieColorStart)
        painter.setBrush(rg)
        painter.drawPie(
            rect,
            int(270 - self._startAngle - angleStart) * 16,
            int(angleStart) * 16,
        )

        # Blue segment
        rg = QRadialGradient(0, 0, radius, 0, 0)
        rg.setColorAt(0, Qt.transparent)
        rg.setColorAt(ratio, Qt.transparent)
        rg.setColorAt(ratio + 0.01, self.pieColorMid)
        rg.setColorAt(1, self.pieColorMid)
        painter.setBrush(rg)
        painter.drawPie(
            rect,
            int(
                270 - self._startAngle - angleStart - angleMid
            ) * 16,
            int(angleMid) * 16,
        )

        # Red segment
        rg = QRadialGradient(0, 0, radius, 0, 0)
        rg.setColorAt(0, Qt.transparent)
        rg.setColorAt(ratio, Qt.transparent)
        rg.setColorAt(ratio + 0.01, self.pieColorEnd)
        rg.setColorAt(1, self.pieColorEnd)
        painter.setBrush(rg)
        painter.drawPie(
            rect,
            int(
                270
                - self._startAngle
                - angleStart
                - angleMid
                - angleEnd
            ) * 16,
            int(angleEnd) * 16,
        )

        painter.restore()

    def _drawPointer(self, painter: QPainter) -> None:
        painter.save()
        radius = 58
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.pointerColor)

        pts = QPolygon([
            QPoint(-5, 0),
            QPoint(0, -8),
            QPoint(5, 0),
            QPoint(0, radius),
        ])

        painter.rotate(self._startAngle)
        degRotate = (
            (360.0 - self._startAngle - self._endAngle)
            / (self.MAX_VALUE - self.MIN_VALUE)
            * self._value
        )
        painter.rotate(degRotate)
        painter.drawConvexPolygon(pts)
        painter.restore()

    def _drawTicks(self, painter: QPainter) -> None:
        painter.save()
        radius = 79
        painter.rotate(self._startAngle)
        steps = self._scaleMajor
        angleStep = (
            (360.0 - self._startAngle - self._endAngle) / steps
        )

        for i in range(steps + 1):
            if i < 3:
                color = self.pieColorStart
            elif i < 7:
                color = self.pieColorMid
            else:
                color = self.pieColorEnd
            painter.setPen(QPen(color, 1, Qt.SolidLine))
            painter.drawLine(0, radius - 5, 0, radius)
            painter.rotate(angleStep)
        painter.restore()

    def _drawLabels(self, painter: QPainter) -> None:
        painter.save()
        startRad = 4
        deltaRad = 0.6
        radius = 63
        offset = 5.5

        for i in range(self._scaleMajor + 1):
            sina = math.sin(startRad - i * deltaRad)
            cosa = math.cos(startRad - i * deltaRad)

            value = math.ceil(
                1.0
                * i
                * (
                    (self.MAX_VALUE - self.MIN_VALUE)
                    / self._scaleMajor
                )
                + self.MIN_VALUE
            )
            strValue = str(int(value))

            metrics = QFontMetrics(self._font)
            textWidth = metrics.horizontalAdvance(strValue)
            textHeight = metrics.height()

            x = radius * cosa - textWidth / 2
            y = -radius * sina + textHeight / 4

            painter.setFont(self._font)
            painter.setPen(QColor(115, 251, 253))
            painter.drawText(
                int(x - offset), int(y), strValue + "M"
            )
        painter.restore()

    def _drawTitle(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(Qt.white)
        painter.drawText(-60, 75, self._title)
        painter.restore()