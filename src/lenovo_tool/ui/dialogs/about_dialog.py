"""About dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

from lenovo_tool import __version__


class AboutDialog(QDialog):
    """Application about dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Lenovo Battery Tool")
        self.setFixedSize(360, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Lenovo Battery Tool")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignCenter)

        version = QLabel(f"Version {__version__}")
        version.setStyleSheet("font-size: 13px; color: #BDC8E2;")
        version.setAlignment(Qt.AlignCenter)

        desc = QLabel("Battery Intelligent Platform\nMonitor, diagnose, and predict battery health")
        desc.setStyleSheet("font-size: 12px; color: #888;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E3648; color: white;
                border: 1px solid aqua; border-radius: 6px;
                padding: 6px 24px; font-size: 13px;
            }
            QPushButton:hover { background-color: aqua; color: black; }
        """)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(desc)
        layout.addStretch()
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
