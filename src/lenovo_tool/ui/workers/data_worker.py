"""Background worker for periodic main data acquisition."""

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from lenovo_tool.core.data_models import BatterySnapshot
from lenovo_tool.services.data_acquisition import DataAcquisitionService


class DataWorker(QThread):
    """Periodic data fetching worker thread.

    Improvements over legacy Worker:
    - Emits typed BatterySnapshot instead of dict
    - Proper error signal instead of silent crash
    - Configurable interval
    """

    data_ready = Signal(BatterySnapshot)
    error_occurred = Signal(Exception)

    def __init__(self, service: DataAcquisitionService, interval_ms: int = 4000, parent=None):
        super().__init__(parent)
        self._service = service
        self._interval = interval_ms
        self._active = False
        self._lock = QMutex()

    def run(self) -> None:
        self._active = True
        while self._active:
            with QMutexLocker(self._lock):
                try:
                    snapshot = self._service.fetch_snapshot()
                    self.data_ready.emit(snapshot)
                except Exception as e:
                    self.error_occurred.emit(e)
            self.msleep(self._interval)

    def stop(self) -> None:
        self._active = False
        self.wait(5000)
