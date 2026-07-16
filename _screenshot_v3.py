"""最终验证：截图 V3.0 大屏效果。"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from lenovo_tool.core.demo_datasource import DemoDLLInterface
from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.ui.main_window import MainWindow

app = QApplication(sys.argv)
config = AppConfig(window_width=1600, window_height=900)
dll = DemoDLLInterface()
window = MainWindow(dll, config)
window.setWindowTitle("Lenovo Battery Monitor Dashboard V3.0")
window.show()
window._start_monitoring()

def capture():
    # 触发几次快照让所有面板都有数据
    for _ in range(5):
        app.processEvents()
    pixmap = window.grab()
    pixmap.save("/workspace/screenshot_v3.png")
    print(f"Screenshot saved: {pixmap.width()}x{pixmap.height()}")
    window._stop_monitoring()
    app.quit()

QTimer.singleShot(3000, capture)
app.exec()
