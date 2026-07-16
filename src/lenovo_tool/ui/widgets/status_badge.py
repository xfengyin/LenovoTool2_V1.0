"""Status badge / indicator with icon, label, and colored background."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from lenovo_tool.ui.styles.main_style import (
    TEXT_LABEL, TEXT_PRIMARY, FONT_SM, FONT_BASE,
)


class StatusBadge(QWidget):
    """Horizontal badge with icon + label + value, auto-colored.

    Used for charge state, health rating, etc.
    """

    def __init__(
        self,
        icon: str = "\u25cf",
        label: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFixedWidth(14)
        self._icon_lbl.setStyleSheet(
            f"font-size: {FONT_SM}px; border: none; background: transparent;"
        )

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )

        self._value_lbl = QLabel("--")
        self._value_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_BASE}px; "
            f"font-weight: bold; border: none; background: transparent;"
        )

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._label_lbl)
        layout.addStretch()
        layout.addWidget(self._value_lbl)

    def set_value(self, text: str, color: str = TEXT_PRIMARY) -> None:
        self._value_lbl.setText(text)
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: {FONT_BASE}px; font-weight: bold; "
            f"border: none; background: transparent;"
        )

    def set_icon(self, icon: str, color: str = TEXT_PRIMARY) -> None:
        self._icon_lbl.setText(icon)
        self._icon_lbl.setStyleSheet(
            f"color: {color}; font-size: {FONT_SM}px; "
            f"border: none; background: transparent;"
        )
