"""Real-time scrolling chart widget using pyqtgraph."""

import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from lenovo_tool.ui.styles.main_style import (
    BG_CARD, BG_PRIMARY, CHART_GRID, TEXT_LABEL,
)


class ChartWidget(QWidget):
    """Real-time scrolling chart for battery metrics with modern styling."""

    def __init__(
        self,
        title: str,
        y_range: tuple[float, float],
        y_label: str = "",
        line_color: str = "#00e5c8",
        history_seconds: int = 60,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._y_range = y_range
        self._y_label = y_label
        self._line_color = line_color
        self._history_seconds = history_seconds
        self._times: deque[float] = deque(maxlen=history_seconds)
        self._values: deque[float] = deque(maxlen=history_seconds)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title label
        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet(
            f"color: {TEXT_LABEL}; font-size: 11px; "
            f"font-weight: bold; padding: 4px 8px;"
        )
        layout.addWidget(title_lbl)

        self.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        # pyqtgraph plot
        pg.setConfigOptions(antialias=True)
        self._plot = pg.PlotWidget()
        self._plot.setBackground(BG_CARD)

        # Style the plot
        plot_item = self._plot.getPlotItem()
        if plot_item:
            plot_item.showGrid(
                x=True, y=True,
                alpha=0.15,
            )
            # Style axes
            for axis_name in ("bottom", "left"):
                axis = plot_item.getAxis(axis_name)
                axis.setPen(pg.mkPen(CHART_GRID, width=1))
                axis.setTextPen(pg.mkPen(TEXT_LABEL))

            # Hide top/right axes
            plot_item.hideAxis("top")
            plot_item.hideAxis("right")

        self._plot.setYRange(*self._y_range, padding=0.1)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()

        pen = pg.mkPen(
            self._line_color, width=2, style=pg.QtCore.Qt.SolidLine
        )
        self._curve = self._plot.plot(pen=pen, antialias=True)

        layout.addWidget(self._plot)

    def append(self, value: float) -> None:
        """Add a data point and update the curve."""
        now = time.time()
        self._times.append(now)
        self._values.append(value)
        self._curve.setData(
            list(self._times), list(self._values)
        )

    def clear(self) -> None:
        self._times.clear()
        self._values.clear()
        self._curve.clear()