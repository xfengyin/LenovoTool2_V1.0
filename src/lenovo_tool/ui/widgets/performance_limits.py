"""Performance limit display (PL1, PL2, PL4) as compact value cards."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)

from lenovo_tool.ui.styles.main_style import TEXT_LABEL, TEXT_VALUE


class PerformanceLimitsWidget(QWidget):
    """Displays PL1, PL2, PL4 processor power limits in a compact row."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: dict[str, QLabel] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        for name, desc in [
            ("PL1", "长时功耗"),
            ("PL2", "短时功耗"),
            ("PL4", "极限功耗"),
        ]:
            block = QVBoxLayout()
            block.setSpacing(2)

            label = QLabel(name)
            label.setStyleSheet(
                f"color: {TEXT_LABEL}; font-size: 11px; "
                f"font-weight: bold;"
            )

            val_lbl = QLabel("-- W")
            val_lbl.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 18px; "
                f"font-weight: bold; font-family: Consolas, monospace;"
            )

            sub = QLabel(desc)
            sub.setStyleSheet(
                f"color: {TEXT_LABEL}; font-size: 10px;"
            )

            block.addWidget(label)
            block.addWidget(val_lbl)
            block.addWidget(sub)
            layout.addLayout(block)

            self._values[name] = val_lbl

        layout.addStretch()

    def set_value(self, name: str, value: int) -> None:
        if name in self._values:
            self._values[name].setText(f"{value} W")

    def reset(self) -> None:
        for lbl in self._values.values():
            lbl.setText("-- W")