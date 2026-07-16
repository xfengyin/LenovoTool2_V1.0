"""历史数据后台写入 Worker - 避免阻塞采集线程。

通过 Queue 解耦采集线程与数据库 I/O 线程：
- 采集线程调用 enqueue() 即可返回（不阻塞）
- 后台线程从 Queue 消费并写入 SQLite
- 退前自动 flush，保证数据完整性
"""

import logging
from queue import Empty, Queue

from PySide6.QtCore import QThread, Signal

from lenovo_tool.core.data_models import BatterySnapshot
from lenovo_tool.services.history_repository import HistoryRepository

logger = logging.getLogger(__name__)


class HistoryWorker(QThread):
    """后台消费 BatterySnapshot 并写入 SQLite。"""

    error_occurred = Signal(str)

    def __init__(
        self, repository: HistoryRepository, session_id: str, parent=None
    ):
        super().__init__(parent)
        self._repo = repository
        self._session_id = session_id
        self._queue: Queue = Queue()
        self._running = False

    def enqueue(self, snapshot: BatterySnapshot, delay_ms: float = 0.0) -> None:
        """非阻塞入队。队列满/异常时记录日志但不抛出，避免影响采集。"""
        try:
            self._queue.put_nowait((snapshot, delay_ms))
        except Exception as e:
            logger.error("Failed to enqueue: %s", e)

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                # 空闲时继续循环，直到 stop() 置 _running=False
                continue
            if item is None:
                # 哨兵：stop() 注入，触发退出
                break
            snapshot, delay_ms = item
            try:
                self._repo.insert(snapshot, self._session_id, delay_ms)
            except Exception as e:
                # 单条写入失败不应中断整个 worker
                self.error_occurred.emit(str(e))
                logger.error("HistoryWorker insert error: %s", e)
        # 退出前 flush，保证数据全部落盘
        try:
            self._repo.close()
        except Exception as e:
            logger.warning("HistoryWorker close error: %s", e)

    def stop(self) -> None:
        """优雅停止：先置标志位，再投递哨兵唤醒阻塞的 get()。"""
        self._running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            # 极端情况下注入失败也无妨，run() 超时后会自然退出
            pass
