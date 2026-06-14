"""Application entry point — assembles all dependencies and launches the UI.

Usage:
    python -m lenovo_tool.main              # Real mode
    python -m lenovo_tool.main --demo       # Demo mode (mock data)
"""

import argparse
import logging
import random
import sys
import threading
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from lenovo_tool.core.exceptions import (
    ConfigurationError,
    DLLCommunicationError,
    DLLNotFoundError,
)
from lenovo_tool.ui.main_window import MainWindow
from lenovo_tool.utils.config_manager import ConfigManager
from lenovo_tool.utils.logger_setup import setup_logging

logger = logging.getLogger(__name__)


class DemoDLLInterface:
    """Mock DLL with realistic battery simulation."""

    _lock = threading.RLock()

    def __init__(self) -> None:
        self._soh = random.randint(90, 98)
        self._last_soh_tick = time.monotonic()
        self._rsoc = random.randint(60, 95)
        self._rsoc_dir = -1
        self._cycle_count = random.randint(50, 200)

    def read_int_word(self, addr: int) -> int:
        return self._mock_value(addr)

    def read_neg_word(self, addr: int) -> int:
        val = self._mock_value(addr)
        if addr in (0x0A, 0x60, 0x61, 0x62):
            return -abs(val) % 8000
        return val

    def read_block(self, addr: int, start: int, length: int) -> int:
        return int(random.uniform(100, 5000))

    def write_smbus(self, type_: int, addr: int, slave: int, mode_state: bool) -> None:
        return None

    def read_smbus(self, type_: int, addr: int, byte_length: int, slave: int) -> dict[str, str]:
        return {f"byte{i}": f"{random.randint(0, 255):02x}" for i in range(byte_length)}

    def get_temperature(self, addr: int = 0x08) -> float:
        return round(random.uniform(28.0, 45.0), 1)

    def get_first_usage_time(self, addr: int = 0x3F) -> str:
        return "2023-06-15"

    def life_prediction(self, addr: int = 0x6A) -> int:
        if self._soh >= 90:
            return 36
        elif self._soh >= 80:
            return 24
        elif self._soh >= 60:
            return 12
        elif self._soh >= 40:
            return 6
        return 0

    def read_soh(self) -> int:
        now = time.monotonic()
        if now - self._last_soh_tick > 30:
            self._last_soh_tick = now
            if random.random() < 0.3:
                self._soh = max(40, self._soh - 1)
        return self._soh

    def read_all_main_registers(self) -> dict[str, int | float]:
        voltage = self.read_int_word(0x09)
        current = self.read_neg_word(0x0A)
        temperature = self.get_temperature(0x08)

        self._rsoc += self._rsoc_dir * random.randint(1, 3)
        if self._rsoc <= 15:
            self._rsoc_dir = 1
        elif self._rsoc >= 98:
            self._rsoc_dir = -1
        self._rsoc = max(0, min(100, self._rsoc))

        soh = self.read_soh()
        dc = self.read_int_word(0x18)
        fcc = int(dc * soh / 100)
        rm = int(fcc * self._rsoc / 100)

        if random.random() < 0.05:
            self._cycle_count += 1

        return {
            "voltage": voltage,
            "current": current,
            "temperature": temperature,
            "rsoc": self._rsoc,
            "soh": soh,
            "fcc": fcc,
            "rm": rm,
            "dc": dc,
            "dv": self.read_int_word(0x19),
            "battery_mode": self.read_int_word(0x03),
            "pl1": self.read_neg_word(0x60),
            "pl2": self.read_neg_word(0x61),
            "pl4": self.read_neg_word(0x62),
            "life_raw": self.read_int_word(0x6A),
            "cycle_count": self._cycle_count,
        }

    @staticmethod
    def _mock_value(addr: int) -> int:
        values: dict[int, int] = {
            0x09: int(random.uniform(12000, 17000)),
            0x0A: int(random.uniform(-3000, 5000)),
            0x0D: random.randint(30, 100),
            0x0F: random.randint(1000, 7000),
            0x10: random.randint(3000, 8000),
            0x18: random.randint(6000, 6500),
            0x19: random.randint(14000, 16000),
            0x03: 0x6001,
            0x60: int(random.uniform(15, 65)),
            0x61: int(random.uniform(30, 90)),
            0x62: int(random.uniform(50, 130)),
            0x6A: random.choice([1792, 1536, 1280, 1024, 500]),
            0x4F: random.randint(80, 100),
        }
        return values.get(addr, int(random.uniform(0, 65535)))


def _try_load_dlls(config):
    from lenovo_tool.core.dll_loader import DLLLoader
    from lenovo_tool.core.dll_interface import DLLInterface

    dll_loader = DLLLoader(search_paths=list(config.dll_search_paths))
    dll_paths = dll_loader.find_dlls()
    dll = DLLInterface(dll_paths)
    logger.info("DLLs loaded: SWD_EC=%s, Sunwoda=%s", dll_paths.swd_ec_path, dll_paths.sunwoda_path)
    return dll


def _ask_demo_fallback(title: str, message: str) -> bool:
    reply = QMessageBox.question(
        None, title, message,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
    )
    return reply == QMessageBox.Yes


def main() -> int:
    parser = argparse.ArgumentParser(description="Lenovo Battery Tool")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode with mock data")
    args = parser.parse_args()

    try:
        config_mgr = ConfigManager()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    config = config_mgr.config

    setup_logging(level=config.log_level, fmt=config.log_format, log_file=config.log_file)

    dll = None
    if args.demo:
        logger.info("Running in DEMO mode with mock data")
        dll = DemoDLLInterface()
    else:
        try:
            dll = _try_load_dlls(config)
        except DLLNotFoundError as e:
            logger.warning("DLLs not found, falling back to demo mode: %s", e)
        except DLLCommunicationError as e:
            logger.warning("DLL load failed (likely 32/64-bit mismatch): %s", e)

    if dll is None:
        ok = _ask_demo_fallback(
            "DLL Not Found",
            "Required DLLs could not be loaded.\n\nRun in demo mode?",
        )
        if ok:
            dll = DemoDLLInterface()
        else:
            return 1

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.window_title)

    window = MainWindow(dll, config)
    window.setWindowTitle(
        f"{config.window_title} [DEMO]"
        if isinstance(dll, DemoDLLInterface)
        else config.window_title
    )
    window.show()

    logger.info("Application started")
    exit_code = app.exec()
    logger.info("Application exiting with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())