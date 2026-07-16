"""高性能渐变进度条组件。

直接使用 QPainter 绘制，避免频繁 setStyleSheet 导致的 QSS 重新解析开销。
用于 FCC/RM/DC 容量条、电芯电压条等需要高频更新的场景。
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from lenovo_tool.ui.styles.main_style import BAR_BG, BAR_RADIUS


class GradientBar(QWidget):
    """渐变填充进度条，通过 paintEvent 直接绘制。

    相比 QFrame + setStyleSheet 方式，更新时仅触发 paintEvent，
    无需重新解析 QSS 字符串，适合高频数据更新场景。
    """

    def __init__(self, height: int = 12, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pct: float = 0.0
        self._color: QColor = QColor(BAR_BG)
        self.setFixedHeight(height)

    def setValue(self, pct: float, color: str = BAR_BG) -> None:
        """设置进度百分比 (0-100) 和填充颜色，触发重绘。"""
        self._pct = max(0.0, min(100.0, pct))
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        rect = QRectF(0, 0, w, h)

        # 背景轨道
        painter.setPen(QPen(QColor(BAR_BG), 0))
        painter.setBrush(QColor(BAR_BG))
        painter.drawRoundedRect(rect, BAR_RADIUS, BAR_RADIUS)

        # 填充区域
        if self._pct > 0:
            fill_w = w * self._pct / 100.0
            fill_rect = QRectF(0, 0, fill_w, h)
            gradient = QLinearGradient(0, 0, fill_w, 0)
            light = QColor(self._color)
            light.setAlpha(220)
            gradient.setColorAt(0, self._color)
            gradient.setColorAt(1, light)
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(fill_rect, BAR_RADIUS, BAR_RADIUS)

        painter.end()
