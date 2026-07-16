"""Immutable data transfer objects for the application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Dict


@dataclass(frozen=True, slots=True)
class BatterySnapshot:
    """A single complete battery reading at a point in time.

    Immutable and thread-safe.
    """

    timestamp: datetime
    voltage: int           # mV
    current: int           # mA (negative = discharge)
    temperature: float     # Celsius
    rsoc: int              # Relative State of Charge, 0-100%
    soh: int               # State of Health, 0-100%
    fcc: int               # Full Charge Capacity, mAh
    rm: int                # Remaining Capacity, mAh
    dc: int                # Design Capacity, mAh
    dv: int                # Design Voltage, mV
    battery_mode: int      # Raw mode bits (hex)
    pl1: int               # Power Limit 1, W
    pl2: int               # Power Limit 2, W
    pl4: int               # Power Limit 4, W
    predicted_life_months: int = 0
    cycle_count: int = 0           # Charge cycle count
    first_usage_time: str = ""     # e.g. "2023-06-15"
    charge_state: str = "idle"     # charging / discharging / idle / full
    max_temperature: float = 0.0   # Session peak temperature
    min_voltage: int = 0           # Session low voltage
    max_voltage: int = 0           # Session high voltage


@dataclass(frozen=True, slots=True)
class LogSnapshot:
    """Comprehensive log data with all SMBus registers."""

    timestamp: datetime
    values: dict[str, int | float | str]
    units: dict[str, str]


@dataclass(frozen=True, slots=True)
class ChargeMode:
    """Charge mode state."""

    FAST_CHARGE_ADDR: ClassVar[int] = 0x26
    NIGHT_CHARGE_ADDR: ClassVar[int] = 0x50
    SLAVE_ADDR: ClassVar[int] = 0x16

    fast_charge_enabled: bool = False
    night_charge_enabled: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application configuration with sensible defaults."""

    poll_interval_ms: int = 4000
    chart_history_seconds: int = 60
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8"
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_file: str | None = None
    window_title: str = "Lenovo Battery Tool"
    window_width: int = 1400
    window_height: int = 820
    window_fixed_size: bool = True
    temperature_warning_threshold: float = 60.0
    soh_warning_threshold: int = 20
    dll_search_paths: tuple[str, ...] = ("./resources/dlls", "./")
    voltage_y_range: tuple[int, int] = (10000, 18000)
    current_y_range: tuple[int, int] = (-4000, 8000)
    fcc_y_range: tuple[int, int] = (3000, 12000)
    rm_y_range: tuple[int, int] = (3000, 12000)
    gauge_min: int = 0
    gauge_max: int = 36
    gauge_title: str = "预计可用寿命（月）"


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Performance metrics for monitoring service health."""

    sample_count: int = 0
    total_delay_ms: float = 0.0
    max_delay_ms: float = 0.0
    min_delay_ms: float = float("inf")
    error_count: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    uptime_seconds: float = 0.0