"""Status badge / indicator with icon, label, and colored background."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusBadge(QWidget):
    """Horizontal badge with icon + label + value, auto-colored.

    Used for charge state, health rating, etc.
    """

    def __init__(
        self,
        icon: str = "●",
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
            "font-size: 10px; border: none; background: transparent;"
        )

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: #7a8fa3; font-size: 10px; border: none; "
            f"background: transparent;"
        )

        self._value_lbl = QLabel("--")
        self._value_lbl.setStyleSheet(
            f"color: #e0e8f0; font-size: 12px; font-weight: bold; "
            f"border: none; background: transparent;"
        )

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._label_lbl)
        layout.addStretch()
        layout.addWidget(self._value_lbl)

    def set_value(self, text: str, color: str = "#e0e8f0") -> None:
        self._value_lbl.setText(text)
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; "
            f"border: none; background: transparent;"
        )

    def set_icon(self, icon: str, color: str = "#e0e8f0") -> None:
        self._icon_lbl.setText(icon)
        self._icon_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; "
            f"border: none; background: transparent;"
        )