"""Application entry point — assembles all dependencies and launches the UI.

Usage:
    python -m lenovo_tool.main              # Real mode
    python -m lenovo_tool.main --demo       # Demo mode (mock data)
"""

import argparse
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from lenovo_tool.core.demo_datasource import DemoDLLInterface
from lenovo_tool.core.di_container import create_default_container
from lenovo_tool.core.exceptions import (
    ConfigurationError,
    DLLCommunicationError,
    DLLNotFoundError,
)
from lenovo_tool.core.dll_interface import DLLInterface
from lenovo_tool.ui.main_window import MainWindow
from lenovo_tool.utils.config_manager import ConfigManager
from lenovo_tool.utils.logger_setup import setup_logging

logger = logging.getLogger(__name__)


def _try_load_dlls(config):
    from lenovo_tool.core.dll_loader import DLLLoader

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


def build_container(config, args) -> tuple[any, bool]:
    """Build DI container with appropriate data source."""
    dll = None
    is_demo = args.demo

    if args.demo:
        logger.info("Running in DEMO mode with mock data")
        dll = DemoDLLInterface()
    else:
        try:
            dll = _try_load_dlls(config)
        except DLLNotFoundError as e:
            logger.warning("DLLs not found, falling back to demo mode: %s", e)
            dll = DemoDLLInterface()
            is_demo = True
        except DLLCommunicationError as e:
            logger.warning("DLL load failed (likely 32/64-bit mismatch): %s", e)
            dll = DemoDLLInterface()
            is_demo = True

    if dll is None:
        ok = _ask_demo_fallback(
            "DLL Not Found",
            "Required DLLs could not be loaded.\n\nRun in demo mode?",
        )
        if ok:
            dll = DemoDLLInterface()
            is_demo = True
        else:
            return None, False

    container = create_default_container(config, dll, is_demo)
    return container, is_demo


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

    container, is_demo = build_container(config, args)
    if container is None:
        return 1

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.window_title)

    window = MainWindow(container.data_source, config)
    window.setWindowTitle(
        f"{config.window_title} [DEMO]"
        if is_demo
        else config.window_title
    )
    window.show()

    logger.info("Application started (demo=%s)", is_demo)
    exit_code = app.exec()
    logger.info("Application exiting with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())