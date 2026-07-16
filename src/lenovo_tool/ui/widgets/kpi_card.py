"""KPI 指标卡片 - 大号数字 + 标签 + 底部装饰条。

仿大屏风格的 KPI 卡：
- 顶部图标 / 数字大号显示
- 下方标签文字
- 底部渐变色装饰条
"""

from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from lenovo_tool.ui.styles.main_style import (
    BG_PANEL_SOLID, BORDER_ACCENT, BORDER_GLOW,
    TEXT_PRIMARY, TEXT_LABEL, TEXT_VALUE, TEXT_SECONDARY,
    FONT_SM, FONT_BASE, FONT_XL, FONT_HUGE,
    GLOW_CYAN, GLOW_GREEN, GLOW_ORANGE, GLOW_RED,
)


class KpiCard(QWidget):
    """KPI 数字指标卡片。

    Args:
        label: 标签文字
        color: 主色调（十六进制颜色）
        suffix: 数值单位后缀
        big_font: 是否使用更大号字体
    """

    def __init__(
        self,
        label: str = "",
        color: str = GLOW_CYAN,
        suffix: str = "",
        big_font: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self._suffix = suffix
        self._value: float = 0
        self._display_value: float = 0
        self._anim = None
        self._int_mode = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self._val_lbl = QLabel("0" + suffix)
        self._val_lbl.setAlignment(Qt.AlignCenter)
        size = FONT_HUGE if big_font else FONT_XL
        weight = "bold"
        self._val_lbl.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-weight: {weight}; "
            f"font-family: 'Consolas', 'Courier New', monospace; "
            f"border: none; background: transparent;"
        )
        layout.addWidget(self._val_lbl)

        self._label_lbl = QLabel(label)
        self._label_lbl.setAlignment(Qt.AlignCenter)
        self._label_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )
        layout.addWidget(self._label_lbl)

        self.setMinimumHeight(60 if not big_font else 80)

    # --- 动画属性 ---
    def _get_dv(self) -> float:
        return self._display_value

    def _set_dv(self, v: float) -> None:
        self._display_value = v
        if self._int_mode:
            self._val_lbl.setText(f"{int(v)}{self._suffix}")
        else:
            self._val_lbl.setText(f"{v:.1f}{self._suffix}")

    displayValue = Property(float, _get_dv, _set_dv)

    def set_value(self, value: float | int, animate: bool = True) -> None:
        """设置数值，带动画过渡。"""
        self._value = float(value)
        if animate:
            if self._anim is not None:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"displayValue")
            self._anim.setDuration(600)
            self._anim.setStartValue(self._display_value)
            self._anim.setEndValue(self._value)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.start()
        else:
            self._display_value = self._value
            self._set_dv(self._value)

    def set_float_mode(self) -> None:
        self._int_mode = False

    def set_color(self, color: str) -> None:
        self._color = color
        f = self._val_lbl.styleSheet()
        import re
        f = re.sub(r"color: #[0-9a-fA-F]+;", f"color: {color};", f)
        self._val_lbl.setStyleSheet(f)
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.setBrush(QColor(BG_PANEL_SOLID))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(0, 0, w, h))

        # 边框
        border = QColor(BORDER_ACCENT)
        border.setAlpha(80)
        painter.setPen(border)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(0.5, 0.5, w - 1, h - 1))

        # 底部渐变装饰条
        bar_h = 3
        gradient = QLinearGradient(0, h - bar_h, w, h - bar_h)
        c = QColor(self._color)
        c.setAlpha(0)
        gradient.setColorAt(0, c)
        c.setAlpha(200)
        gradient.setColorAt(0.3, c)
        gradient.setColorAt(0.7, c)
        c.setAlpha(0)
        gradient.setColorAt(1, c)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRect(QRectF(0, h - bar_h, w, bar_h))

        # 顶部细发光线
        glow = QColor(BORDER_GLOW)
        glow.setAlpha(60)
        painter.setPen(glow)
        painter.drawLine(1, 0, w - 1, 0)

        painter.end()
