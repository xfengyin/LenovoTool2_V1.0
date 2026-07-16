"""科技感监控面板组件 - 带四角装饰和发光边框。

仿大屏监控面板样式：半透明深色背景 + 霓虹青发光边框 + 四角 L 形装饰线
+ 顶部标题条（左侧竖条装饰 + 标题文字）。
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from lenovo_tool.ui.styles.main_style import (
    BG_PANEL_SOLID, BG_CARD_HEADER,
    BORDER_ACCENT, BORDER_GLOW, BORDER_SUBTLE,
    TEXT_ACCENT, TEXT_PRIMARY,
    FONT_SM, FONT_MD,
)


class PanelWidget(QWidget):
    """科技感面板：四角装饰 + 发光边框 + 标题栏。

    使用方式：
        panel = PanelWidget("面板标题")
        panel.content_layout.addWidget(some_widget)
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self.setMinimumHeight(100)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        title_bar = QFrame()
        title_bar.setFixedHeight(28)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.setSpacing(6)

        # 左侧装饰竖条
        self._deco = QLabel()
        self._deco.setFixedSize(3, 14)
        self._deco.setStyleSheet(f"background-color: {BORDER_GLOW}; border: none;")
        title_layout.addWidget(self._deco)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: {TEXT_ACCENT}; font-size: {FONT_MD}px; "
            f"font-weight: bold; letter-spacing: 1px; border: none; "
            f"background: transparent;"
        )
        title_layout.addWidget(self._title_lbl)
        title_layout.addStretch()

        outer.addWidget(title_bar)

        # 内容区
        content = QFrame()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(10, 6, 10, 8)
        self.content_layout.setSpacing(4)
        outer.addWidget(content, stretch=1)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        bg_color = QColor(BG_PANEL_SOLID)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(0, 0, w, h))

        # 边框
        border_color = QColor(BORDER_ACCENT)
        border_color.setAlpha(120)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(0.5, 0.5, w - 1, h - 1))

        # 顶部发光线
        glow_gradient = QLinearGradient(0, 0, w, 0)
        glow_color = QColor(BORDER_GLOW)
        glow_color.setAlpha(0)
        glow_gradient.setColorAt(0, glow_color)
        glow_color.setAlpha(180)
        glow_gradient.setColorAt(0.3, glow_color)
        glow_gradient.setColorAt(0.7, glow_color)
        glow_color.setAlpha(0)
        glow_gradient.setColorAt(1, glow_color)
        painter.setPen(QPen(glow_gradient, 2))
        painter.drawLine(1, 1, w - 1, 1)

        # 四角 L 形装饰
        corner_len = 10
        corner_color = QColor(BORDER_GLOW)
        painter.setPen(QPen(corner_color, 2))

        # 左上
        painter.drawLine(2, 2 + corner_len, 2, 2)
        painter.drawLine(2, 2, 2 + corner_len, 2)
        # 右上
        painter.drawLine(w - 2 - corner_len, 2, w - 2, 2)
        painter.drawLine(w - 2, 2, w - 2, 2 + corner_len)
        # 左下
        painter.drawLine(2, h - 2 - corner_len, 2, h - 2)
        painter.drawLine(2, h - 2, 2 + corner_len, h - 2)
        # 右下
        painter.drawLine(w - 2 - corner_len, h - 2, w - 2, h - 2)
        painter.drawLine(w - 2, h - 2, w - 2, h - 2 - corner_len)

        painter.end()
