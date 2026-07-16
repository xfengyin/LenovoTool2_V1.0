"""YAML-based configuration management with defaults fallback and watch support."""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Loads configuration from YAML with defaults and dynamic reload.

    Priority: config file > hardcoded defaults.
    Supports watching config file for changes.
    """

    DEFAULT_PATH: Path = Path("config/settings.yaml")
    DEFAULT_WATCH_INTERVAL: float = 2.0

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = Path(config_path) if config_path else self.DEFAULT_PATH
        self._config: AppConfig = self._load()
        self._callbacks: set[Callable[[], None]] = set()
        self._watch_thread: threading.Thread | None = None
        self._watch_running: bool = False
        self._last_modified: float = self._get_file_modified_time()

    @property
    def config(self) -> AppConfig:
        return self._config

    _KEY_MAP: ClassVar[dict[str, str]] = {
        "app.title": "window_title",
        "app.window_width": "window_width",
        "app.window_height": "window_height",
        "app.window_fixed_size": "window_fixed_size",
        "polling.main_interval_ms": "poll_interval_ms",
        "charts.history_seconds": "chart_history_seconds",
        "charts.voltage_y_range": "voltage_y_range",
        "charts.current_y_range": "current_y_range",
        "charts.fcc_y_range": "fcc_y_range",
        "charts.rm_y_range": "rm_y_range",
        "csv.delimiter": "csv_delimiter",
        "csv.encoding": "csv_encoding",
        "logging.level": "log_level",
        "logging.format": "log_format",
        "logging.file": "log_file",
        "thresholds.temperature_warning": "temperature_warning_threshold",
        "thresholds.soh_warning": "soh_warning_threshold",
        "dll.search_paths": "dll_search_paths",
        "gauge.min_value": "gauge_min",
        "gauge.max_value": "gauge_max",
        "gauge.title": "gauge_title",
    }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path.

        Args:
            key: Configuration key path (e.g., 'app.title')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        if key in self._KEY_MAP:
            key = self._KEY_MAP[key]

        parts = key.split(".")
        value: Any = self._config

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def reload(self) -> None:
        """Reload configuration from source and notify watchers."""
        old_config = self._config
        self._config = self._load()
        self._last_modified = self._get_file_modified_time()

        if self._config != old_config:
            self._notify_callbacks()

    def watch(self, callback: Callable[[], None]) -> None:
        """Register a callback for configuration change events.

        Args:
            callback: Function to call when configuration changes
        """
        self._callbacks.add(callback)
        if not self._watch_running and self._path.exists():
            self._start_watch_thread()

    def unwatch(self, callback: Callable[[], None]) -> None:
        """Unregister a callback from configuration change events.

        Args:
            callback: Function to unregister
        """
        self._callbacks.discard(callback)
        if not self._callbacks and self._watch_running:
            self._stop_watch_thread()

    def _start_watch_thread(self) -> None:
        """Start background thread to monitor config file changes."""
        if self._watch_running:
            return

        self._watch_running = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="ConfigWatcher",
        )
        self._watch_thread.start()

    def _stop_watch_thread(self) -> None:
        """Stop the background watch thread."""
        self._watch_running = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5.0)
            self._watch_thread = None

    def _watch_loop(self) -> None:
        """Background loop to check for config file modifications."""
        while self._watch_running:
            try:
                current_modified = self._get_file_modified_time()
                if current_modified > self._last_modified:
                    logger.info(f"Config file changed: {self._path}")
                    self.reload()
            except Exception as e:
                logger.error(f"Error watching config file: {e}")
            time.sleep(self.DEFAULT_WATCH_INTERVAL)

    def _get_file_modified_time(self) -> float:
        """Get the last modified time of the config file.

        Returns:
            Unix timestamp of last modification, or 0 if file doesn't exist
        """
        try:
            return self._path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return 0.0

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks about configuration changes."""
        for callback in list(self._callbacks):
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")

    def _load(self) -> AppConfig:
        data: dict[str, Any] = {}
        try:
            if self._path.is_file():
                import yaml  # noqa: F811 — optional dependency

                with open(self._path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load config from {self._path}: {e}"
            ) from e

        app = data.get("app", {})
        polling = data.get("polling", {})
        charts = data.get("charts", {})
        gauge = data.get("gauge", {})
        logging_cfg = data.get("logging", {})
        csv_cfg = data.get("csv", {})
        dll_cfg = data.get("dll", {})
        thresholds = data.get("thresholds", {})

        return AppConfig(
            window_title=str(
                app.get("title", "Lenovo Battery Tool")
            ),
            window_width=int(app.get("window_width", 1200)),
            window_height=int(app.get("window_height", 676)),
            window_fixed_size=bool(
                app.get("window_fixed_size", True)
            ),
            poll_interval_ms=int(
                polling.get("main_interval_ms", 4000)
            ),
            chart_history_seconds=int(
                charts.get("history_seconds", 60)
            ),
            csv_delimiter=str(csv_cfg.get("delimiter", ",")),
            csv_encoding=str(csv_cfg.get("encoding", "utf-8")),
            log_level=str(logging_cfg.get("level", "INFO")),
            log_format=str(
                logging_cfg.get(
                    "format",
                    "%(asctime)s [%(levelname)s] "
                    "%(name)s: %(message)s",
                )
            ),
            log_file=logging_cfg.get("file"),
            temperature_warning_threshold=float(
                thresholds.get("temperature_warning", 60.0)
            ),
            soh_warning_threshold=int(
                thresholds.get("soh_warning", 20)
            ),
            dll_search_paths=tuple(
                dll_cfg.get(
                    "search_paths", ["./resources/dlls", "./"]
                )
            ),
            voltage_y_range=tuple(
                charts.get("voltage_y_range", (10000, 18000))
            ),
            current_y_range=tuple(
                charts.get("current_y_range", (-4000, 8000))
            ),
            fcc_y_range=tuple(
                charts.get("fcc_y_range", (3000, 12000))
            ),
            rm_y_range=tuple(
                charts.get("rm_y_range", (3000, 12000))
            ),
            gauge_min=int(gauge.get("min_value", 0)),
            gauge_max=int(gauge.get("max_value", 36)),
            gauge_title=str(
                gauge.get("title", "预计可用寿命（月）")
            ),
        )
