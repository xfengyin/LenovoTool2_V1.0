"""Custom UI widgets."""

from lenovo_tool.ui.widgets.battery_data_panel import BatteryDataPanel
from lenovo_tool.ui.widgets.battery_icon_widget import BatteryIconWidget
from lenovo_tool.ui.widgets.chart_widget import ChartWidget
from lenovo_tool.ui.widgets.gauge_widget import GaugeWidget
from lenovo_tool.ui.widgets.half_gauge_widget import HalfGaugeWidget
from lenovo_tool.ui.widgets.lcd_display import LCDDisplay
from lenovo_tool.ui.widgets.life_prediction_widget import LifePredictionWidget
from lenovo_tool.ui.widgets.performance_limits import PerformanceLimitsWidget
from lenovo_tool.ui.widgets.ring_indicator import RingIndicator
from lenovo_tool.ui.widgets.sparkline_widget import SparklineWidget
from lenovo_tool.ui.widgets.status_badge import StatusBadge

__all__ = [
    "BatteryDataPanel",
    "BatteryIconWidget",
    "ChartWidget",
    "GaugeWidget",
    "HalfGaugeWidget",
    "LCDDisplay",
    "LifePredictionWidget",
    "PerformanceLimitsWidget",
    "RingIndicator",
    "SparklineWidget",
    "StatusBadge",
]