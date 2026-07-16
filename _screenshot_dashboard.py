"""Offscreen screenshot: launch MainWindow in demo mode and capture a screenshot."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from lenovo_tool.core.demo_datasource import DemoDLLInterface
from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.ui.main_window import MainWindow

app = QApplication(sys.argv)
config = AppConfig(window_width=1440, window_height=880)
dll = DemoDLLInterface()
window = MainWindow(dll, config)
window.setWindowTitle("Lenovo Battery Monitor Dashboard")
window.show()

window._start_monitoring()

def capture():
    app.processEvents()
    pixmap = window.grab()
    pixmap.save("/workspace/screenshot_dashboard.png")
    print(f"Screenshot saved: {pixmap.width()}x{pixmap.height()}")
    window._stop_monitoring()
    app.quit()

QTimer.singleShot(2500, capture)
app.exec()
