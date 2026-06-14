"""Background worker for comprehensive log data scanning."""

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from lenovo_tool.core.data_models import LogSnapshot
from lenovo_tool.services.log_data_service import LogDataService


class LogWorker(QThread):
    """Periodic comprehensive register scanning worker.

    Improvements over legacy WorkThread:
    - No multiple inheritance from UI class
    - Typed LogSnapshot signal
    - Proper error handling
    - Clean stop mechanism
    """

    data_ready = Signal(LogSnapshot)
    error_occurred = Signal(Exception)

    def __init__(self, service: LogDataService, interval_sec: float = 1.0, parent=None):
        super().__init__(parent)
        self._service = service
        self._interval = interval_sec
        self._active = False
        self._lock = QMutex()

    def run(self) -> None:
        self._active = True
        while self._active:
            with QMutexLocker(self._lock):
                try:
                    snapshot = self._service.fetch_log_snapshot()
                    self.data_ready.emit(snapshot)
                except Exception as e:
                    self.error_occurred.emit(e)
            self.msleep(int(self._interval * 1000))

    def stop(self) -> None:
        self._active = False
        self.wait(5000)

    def set_interval(self, interval_sec: float) -> None:
        self._interval = interval_sec
