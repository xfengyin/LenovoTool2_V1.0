"""半圆仪表盘 - 大屏风格：刻度线 + 发光指针 + 渐变色弧。

显示预计可用寿命（月），带平滑指针动画和霓虹发光效果。
"""

import math

from PySide6.QtCore import Qt, QRectF, QPointF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget

from lenovo_tool.ui.styles.main_style import (
    BAR_BG, TEXT_LABEL, TEXT_VALUE, TEXT_SECONDARY,
    STATUS_GOOD, STATUS_BAD,
    GLOW_CYAN, BORDER_GLOW,
)


class HalfGaugeWidget(QWidget):
    """半圆仪表盘 - 大屏风格。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._display_value = 0.0
        self._max = 36
        self._anim = None
        self.setMinimumSize(220, 150)

    # --- 动画属性 ---
    def _get_dv(self) -> float:
        return self._display_value

    def _set_dv(self, v: float) -> None:
        self._display_value = v
        self.update()

    displayValue = Property(float, _get_dv, _set_dv)

    def setValue(self, v):
        self._value = max(0, min(self._max, v))
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(800)
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(float(self._value))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        title_h = 18
        bottom_margin = 22
        arc_area_top = title_h + 4
        arc_area_bottom = h - bottom_margin
        cx = w / 2
        max_r_by_w = (w / 2) - 20
        max_r_by_h = (arc_area_bottom - arc_area_top) / 2 - 6
        radius = min(max_r_by_w, max_r_by_h)
        cy = arc_area_top + radius

        # 标题
        painter.setPen(QColor(TEXT_LABEL))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            QRectF(0, 2, w, title_h),
            Qt.AlignCenter, "\u9884\u8ba1\u53ef\u7528\u5bff\u547d"
        )

        arc_pen_w = radius * 0.12

        # 背景弧发光
        glow_color = QColor(GLOW_CYAN)
        glow_color.setAlpha(20)
        glow_pen = QPen(glow_color, arc_pen_w + 4)
        glow_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(glow_pen)
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 180 * 16)

        # 背景弧
        bg_pen = QPen(QColor(BAR_BG), arc_pen_w)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(arc_rect, 0, 180 * 16)

        ratio = self._display_value / self._max if self._max > 0 else 0
        green_end = 0.33
        blue_end = 0.66
        total_span = int(ratio * 180 * 16)

        def _draw_arc(color, start16, span16):
            p = QPen(QColor(color), arc_pen_w)
            p.setCapStyle(Qt.RoundCap)
            painter.setPen(p)
            painter.drawArc(arc_rect, start16, span16)

        if ratio <= green_end:
            _draw_arc(STATUS_GOOD, 180 * 16, -total_span)
        elif ratio <= blue_end:
            _draw_arc(STATUS_GOOD, 180 * 16, -int(green_end * 180 * 16))
            _draw_arc("#3388ff", int((1 - green_end) * 180 * 16), -int((ratio - green_end) * 180 * 16))
        else:
            _draw_arc(STATUS_GOOD, 180 * 16, -int(green_end * 180 * 16))
            _draw_arc("#3388ff", int((1 - green_end) * 180 * 16), -int((blue_end - green_end) * 180 * 16))
            _draw_arc(STATUS_BAD, int((1 - blue_end) * 180 * 16), -(total_span - int(blue_end * 180 * 16)))

        # 刻度线
        scale_r = radius - arc_pen_w / 2 - 4
        painter.setPen(QPen(QColor(BORDER_GLOW), 1))
        painter.setOpacity(0.4)
        for i in range(13):
            deg = 180 - i * 15
            rad = math.radians(deg)
            inner = scale_r - 3
            outer = scale_r + 1
            x1 = cx + inner * math.cos(rad)
            y1 = cy - inner * math.sin(rad)
            x2 = cx + outer * math.cos(rad)
            y2 = cy - outer * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.setOpacity(1.0)

        # 指针发光
        needle_angle = 180 - ratio * 180
        needle_len = radius * 0.68

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-needle_angle)

        # 指针光晕
        glow = QColor(GLOW_CYAN)
        glow.setAlpha(50)
        painter.setPen(QPen(glow, 4))
        painter.drawLine(0, 0, 0, -int(needle_len))

        # 指针主体
        painter.setPen(QPen(QColor(TEXT_VALUE), 2))
        painter.drawLine(0, 0, 0, -int(needle_len))

        # 指针头
        painter.setBrush(QColor(TEXT_VALUE))
        painter.setPen(Qt.NoPen)
        dr = max(3, radius * 0.045)
        painter.drawEllipse(QPointF(0, -int(needle_len)), dr, dr)

        # 中心圆点
        painter.setBrush(QColor(GLOW_CYAN))
        cr = max(4, radius * 0.07)
        painter.drawEllipse(QPointF(0, 0), cr, cr)

        painter.restore()

        # 刻度标签
        labels = ["0M", "6M", "12M", "18M", "24M", "30M", "36M"]
        painter.setFont(QFont("Segoe UI", 7))
        lbl_off = arc_pen_w / 2 + 12
        for i, lbl in enumerate(labels):
            a = 180 - i * 30
            rad = math.radians(a)
            lx = cx + (radius + lbl_off) * math.cos(rad)
            ly = cy - (radius + lbl_off) * math.sin(rad)
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(QRectF(lx - 14, ly - 7, 28, 14), Qt.AlignCenter, lbl)

        # 数值大字
        painter.setPen(QColor(TEXT_VALUE))
        vf = QFont("Consolas", max(16, int(radius * 0.40)))
        vf.setBold(True)
        painter.setFont(vf)
        painter.drawText(QRectF(cx - 45, cy - radius * 0.28, 90, radius * 0.4), Qt.AlignCenter, str(int(self._display_value)))

        painter.setPen(QColor(TEXT_SECONDARY))
        painter.setFont(QFont("Segoe UI", max(9, int(radius * 0.15))))
        painter.drawText(QRectF(cx - 20, cy + radius * 0.12, 40, 16), Qt.AlignCenter, "\u6708")

        painter.end()
