"""Composite value display widget with label, value, and unit."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from lenovo_tool.ui.styles.main_style import (
    BG_CARD, BORDER_SUBTLE, TEXT_LABEL, TEXT_VALUE,
)


class LCDDisplay(QWidget):
    """Vertical value display: field label, large value, unit.

    Replaces QLCDNumber with a more flexible QLabel-based display
    that fits the card layout better.
    """

    def __init__(
        self, label: str = "", unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label_text = label
        self._unit_text = unit
        self._value = 0
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Field name
        self._label = QLabel(self._label_text)
        self._label.setObjectName("FieldLabel")
        self._label.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 11px;"
        )

        # Value
        self._value_lbl = QLabel("--")
        self._value_lbl.setObjectName("ValueLabel")
        self._value_lbl.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 22px; "
            f"font-weight: bold; font-family: Consolas, monospace;"
        )

        # Unit
        self._unit_lbl = QLabel(self._unit_text)
        self._unit_lbl.setObjectName("UnitLabel")
        self._unit_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 10px;"
        )

        layout.addWidget(self._label)
        layout.addWidget(self._value_lbl)
        layout.addWidget(self._unit_lbl)

    def display(self, value: int | float) -> None:
        """Update the displayed value."""
        self._value = value
        if isinstance(value, float):
            self._value_lbl.setText(f"{value:.1f}")
        else:
            self._value_lbl.setText(str(value))

    def set_unit(self, unit: str) -> None:
        self._unit_text = unit
        self._unit_lbl.setText(unit)

    def set_color(self, color: str) -> None:
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: 22px; "
            f"font-weight: bold; font-family: Consolas, monospace;"
        )