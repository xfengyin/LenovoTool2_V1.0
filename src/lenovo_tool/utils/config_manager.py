"""YAML-based configuration management with defaults fallback."""

import logging
from pathlib import Path

from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Loads configuration from YAML with defaults.

    Priority: config file > hardcoded defaults.
    """

    DEFAULT_PATH: Path = Path("config/settings.yaml")

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = Path(config_path) if config_path else self.DEFAULT_PATH
        self._config: AppConfig = self._load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def reload(self) -> None:
        self._config = self._load()

    def _load(self) -> AppConfig:
        data: dict = {}
        try:
            if self._path.is_file():
                import yaml  # noqa: F811 — optional dependency

                with open(self._path, "r", encoding="utf-8") as f:
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
                charts.get("voltage_y_range", [10000, 18000])  # type: ignore[arg-type]
            ),
            current_y_range=tuple(
                charts.get("current_y_range", [-4000, 8000])  # type: ignore[arg-type]
            ),
            fcc_y_range=tuple(
                charts.get("fcc_y_range", [3000, 12000])  # type: ignore[arg-type]
            ),
            rm_y_range=tuple(
                charts.get("rm_y_range", [3000, 12000])  # type: ignore[arg-type]
            ),
            gauge_min=int(gauge.get("min_value", 0)),
            gauge_max=int(gauge.get("max_value", 36)),
            gauge_title=str(
                gauge.get("title", "预计可用寿命（月）")
            ),
        )