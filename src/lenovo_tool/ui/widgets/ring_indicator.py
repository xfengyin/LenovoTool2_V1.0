"""环形进度指示器 - 大屏风格：外圈发光 + 内圈刻度 + 中心数值。

包含平滑数值过渡动画和发光效果。
"""

import math

from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (
    QColor, QPainter, QPen, QFont, QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from lenovo_tool.ui.styles.main_style import (
    BAR_BG, TEXT_PRIMARY, TEXT_LABEL,
    STATUS_GOOD, STATUS_WARN, STATUS_BAD,
    BORDER_GLOW, GLOW_CYAN,
)


class RingIndicator(QWidget):
    """环形仪表盘，带发光效果和动画。"""

    def __init__(
        self,
        title: str = "",
        max_val: float = 100,
        color: str = GLOW_CYAN,
        unit: str = "%",
        size: int = 90,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._value: float = 0.0
        self._display_value: float = 0.0
        self._max = max_val
        self._color = color
        self._unit = unit
        self._anim = None

        self.setFixedSize(size, size)

    # --- 动画属性 ---
    def _get_dv(self) -> float:
        return self._display_value

    def _set_dv(self, v: float) -> None:
        self._display_value = v
        self.update()

    displayValue = Property(float, _get_dv, _set_dv)

    def setValue(self, value: float) -> None:
        self._value = min(value, self._max)
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(700)
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(self._value)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def setColor(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        side = min(w, h)
        cx, cy = w / 2, h / 2

        ratio = self._display_value / self._max if self._max > 0 else 0
        angle = int(ratio * 360 * 16)

        # 根据比例选颜色
        if ratio < 0.3:
            active_color = QColor(STATUS_BAD)
        elif ratio < 0.6:
            active_color = QColor(STATUS_WARN)
        else:
            active_color = QColor(self._color)

        # 外环发光
        outer_pen_w = side * 0.06
        glow_color = QColor(active_color)
        glow_color.setAlpha(40)
        glow_pen = QPen(glow_color, outer_pen_w)
        glow_pen.setCapStyle(Qt.RoundCap)
        glow_r = side / 2 - outer_pen_w / 2 - 2
        glow_rect = QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)
        painter.setPen(glow_pen)
        painter.drawArc(glow_rect, 90 * 16, -angle)

        # 主环背景
        ring_pen_w = side * 0.10
        ring_r = side / 2 - ring_pen_w / 2 - 4
        ring_rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        bg_color = QColor(BAR_BG)
        bg_color.setAlpha(180)
        bg_pen = QPen(bg_color, ring_pen_w)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(ring_rect, 0, 360 * 16)

        # 主环前景
        active_color_full = QColor(active_color)
        active_pen = QPen(active_color_full, ring_pen_w)
        active_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(active_pen)
        painter.drawArc(ring_rect, 90 * 16, -angle)

        # 内圈刻度线
        scale_r = ring_r - ring_pen_w / 2 - side * 0.05
        scale_color = QColor(BORDER_GLOW)
        scale_color.setAlpha(100)
        scale_pen = QPen(scale_color)
        scale_pen.setWidthF(1)
        painter.setPen(scale_pen)
        for i in range(36):
            deg = i * 10 - 90
            rad = math.radians(deg)
            inner_r = scale_r - 2
            outer_r = scale_r + 2
            x1 = cx + inner_r * math.cos(rad)
            y1 = cy + inner_r * math.sin(rad)
            x2 = cx + outer_r * math.cos(rad)
            y2 = cy + outer_r * math.sin(rad)
            painter.setOpacity(0.4)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.setOpacity(1.0)

        # 中心数值
        painter.setPen(active_color_full)
        val_font = QFont("Consolas")
        val_font.setPixelSize(int(side * 0.20))
        val_font.setBold(True)
        painter.setFont(val_font)
        text = f"{int(self._display_value)}"
        if self._unit:
            text += self._unit
        painter.drawText(QRectF(0, side * 0.08, side, side * 0.5), Qt.AlignCenter, text)

        # 底部标题
        painter.setPen(QColor(TEXT_LABEL))
        title_font = QFont("Segoe UI")
        title_font.setPixelSize(int(side * 0.09))
        painter.setFont(title_font)
        painter.drawText(QRectF(0, side * 0.62, side, side * 0.2), Qt.AlignCenter, self._title)

        painter.end()
