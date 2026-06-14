"""Battery data display panel with progress bars for Temperature, RSOC, SOH."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel

from lenovo_tool.ui.styles.main_style import (
    STATUS_GOOD, STATUS_WARN, STATUS_BAD, TEXT_LABEL,
)


def _bar_color(name: str, value: float) -> str:
    """Return color based on metric name and value."""
    if name == "Temperature":
        if value > 60:
            return STATUS_BAD
        if value > 45:
            return STATUS_WARN
        return "#00e5c8"
    if name == "RSOC":
        if value < 20:
            return STATUS_BAD
        if value < 40:
            return STATUS_WARN
        return STATUS_GOOD
    if name == "SOH":
        if value < 50:
            return STATUS_BAD
        if value < 80:
            return STATUS_WARN
        return STATUS_GOOD
    return "#00e5c8"


class BatteryDataPanel(QWidget):
    """Panel displaying Temperature, RSOC, and SOH as labeled progress bars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: dict[str, QProgressBar] = {}
        self._labels: dict[str, QLabel] = {}
        self._values: dict[str, float] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for name, max_val in [
            ("Temperature", 100),
            ("RSOC", 100),
            ("SOH", 100),
        ]:
            # Row: label left, value right
            header = QHBoxLayout()
            label = QLabel(name)
            label.setObjectName("FieldLabel")
            value_lbl = QLabel("--")
            value_lbl.setObjectName("FieldLabel")
            value_lbl.setStyleSheet(
                f"color: #00e5c8; font-weight: bold;"
            )
            header.addWidget(label)
            header.addStretch()
            header.addWidget(value_lbl)

            bar = QProgressBar()
            bar.setRange(0, max_val)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #1a2a3a;
                    border: 1px solid #2a3f55;
                    border-radius: 4px;
                    min-height: 10px;
                    max-height: 10px;
                }}
                QProgressBar::chunk {{
                    background-color: #00e5c8;
                    border-radius: 3px;
                }}
            """)

            self._bars[name] = bar
            self._labels[name] = value_lbl
            self._values[name] = 0
            layout.addLayout(header)
            layout.addWidget(bar)

    def set_value(
        self, name: str, value: int | float, suffix: str = ""
    ) -> None:
        if name not in self._bars:
            return
        self._values[name] = float(value)
        self._bars[name].setValue(int(value))
        self._labels[name].setText(f"{value}{suffix}")

        color = _bar_color(name, float(value))
        self._bars[name].setStyleSheet(f"""
            QProgressBar {{
                background-color: #1a2a3a;
                border: 1px solid #2a3f55;
                border-radius: 4px;
                min-height: 10px;
                max-height: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        self._labels[name].setStyleSheet(
            f"color: {color}; font-weight: bold;"
        )

    def reset(self) -> None:
        for name in self._bars:
            self._bars[name].setValue(0)
            self._labels[name].setText("--")