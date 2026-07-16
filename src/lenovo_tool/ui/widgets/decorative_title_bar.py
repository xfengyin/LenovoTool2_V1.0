"""大屏顶部装饰标题栏 - 中间标题 + 左右装饰线 + 系统信息。

仿 WGCLOUD 顶部标题样式：
- 中央大标题，带发光效果
- 左右对称的装饰线条（向外延伸渐变消失）
- 左上角 / 右上角显示系统状态信息
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QFont, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from lenovo_tool.ui.styles.main_style import (
    BG_SECONDARY, BORDER_GLOW, BORDER_ACCENT,
    TEXT_ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    FONT_MD, FONT_LG, FONT_SM,
    GLOW_CYAN,
)


class DecorativeTitleBar(QWidget):
    """大屏顶部装饰标题栏。"""

    def __init__(self, title: str = "电池监控大屏", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # 左侧状态
        self._left_info = QLabel("")
        self._left_info.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )
        layout.addWidget(self._left_info)

        # 中间占位 - 标题用 paintEvent 绘制
        title_stretch = QLabel()
        layout.addWidget(title_stretch, stretch=1)

        # 右侧状态
        self._right_info = QLabel("")
        self._right_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._right_info.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )
        layout.addWidget(self._right_info)

    def set_left_text(self, text: str) -> None:
        self._left_info.setText(text)

    def set_right_text(self, text: str) -> None:
        self._right_info.setText(text)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2

        # 背景渐变
        bg = QLinearGradient(0, 0, 0, h)
        top = QColor(BG_SECONDARY)
        top.setAlpha(200)
        bg.setColorAt(0, top)
        bottom = QColor(BG_SECONDARY)
        bottom.setAlpha(100)
        bg.setColorAt(1, bottom)
        painter.setBrush(bg)
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(0, 0, w, h))

        # 底部渐变线
        line_y = h - 1
        line_grad = QLinearGradient(0, line_y, w, line_y)
        c = QColor(BORDER_GLOW)
        c.setAlpha(0)
        line_grad.setColorAt(0, c)
        c.setAlpha(80)
        line_grad.setColorAt(0.2, c)
        c.setAlpha(200)
        line_grad.setColorAt(0.4, c)
        c.setAlpha(255)
        line_grad.setColorAt(0.5, c)
        c.setAlpha(200)
        line_grad.setColorAt(0.6, c)
        c.setAlpha(80)
        line_grad.setColorAt(0.8, c)
        c.setAlpha(0)
        line_grad.setColorAt(1, c)
        painter.setPen(QPen(line_grad, 2))
        painter.drawLine(0, line_y, w, line_y)

        # 标题文字
        painter.setPen(QColor(TEXT_ACCENT))
        title_font = QFont("Microsoft YaHei", FONT_LG)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 4)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, 8, w, h - 16), Qt.AlignCenter, self._title)

        # 标题下方装饰线（短横线）
        line_w = 60
        line_y2 = h - 10
        dgl = QLinearGradient(cx - line_w, line_y2, cx + line_w, line_y2)
        gc = QColor(GLOW_CYAN)
        gc.setAlpha(0)
        dgl.setColorAt(0, gc)
        gc.setAlpha(255)
        dgl.setColorAt(0.5, gc)
        gc.setAlpha(0)
        dgl.setColorAt(1, gc)
        painter.setPen(QPen(dgl, 2))
        painter.drawLine(cx - line_w, line_y2, cx + line_w, line_y2)

        # 装饰菱形点
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(GLOW_CYAN))
        dot_size = 5
        painter.drawRect(QRectF(cx - dot_size / 2, line_y2 - dot_size / 2, dot_size, dot_size))

        painter.end()
