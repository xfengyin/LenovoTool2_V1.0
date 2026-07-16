"""Background worker for periodic main data acquisition."""

import time

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from lenovo_tool.core.data_models import BatterySnapshot, CommMetrics
from lenovo_tool.services.data_acquisition import DataAcquisitionService
from lenovo_tool.services.metrics_service import MetricsService


# 告警阈值（与 AlertEngine.ALERT_RULES 默认值保持一致）
ALM_08_LATENCY_THRESHOLD_MS = 200.0  # 采样延迟阈值
ALM_09_CONSEC_FAILURES_THRESHOLD = 3  # 连续失败次数阈值


class DataWorker(QThread):
    """Periodic data fetching worker thread.

    Improvements over legacy Worker:
    - Emits typed BatterySnapshot instead of dict
    - Proper error signal instead of silent crash
    - Configurable interval
    - Wraps fetch with perf_counter() to record sample latency
    - Emits CommMetrics for the communications diagnostics panel
    - Emits alert_external_trigger Signal 让主线程的 AlertEngine 触发 ALM-08/09
    """

    data_ready = Signal(BatterySnapshot)
    comm_metrics_ready = Signal(CommMetrics)
    error_occurred = Signal(Exception)
    # 跨线程告警触发：主线程收到信号后调用 alert_engine.trigger_external
    alert_external_trigger = Signal(str, float)
    # 跨线程告警恢复
    alert_external_recover = Signal(str)

    def __init__(self, service: DataAcquisitionService, interval_ms: int = 4000, parent=None):
        super().__init__(parent)
        self._service = service
        self._interval = interval_ms
        self._active = False
        self._lock = QMutex()
        # 通信指标采集器：线程安全，可被多个 worker 共享
        self._metrics = MetricsService()
        # ALM-08/09 跟踪：是否处于已触发状态
        self._alm08_active = False
        self._alm09_active = False

    @property
    def metrics(self) -> MetricsService:
        """暴露 MetricsService 以便外部读取/重置。"""
        return self._metrics

    def run(self) -> None:
        self._active = True
        while self._active:
            with QMutexLocker(self._lock):
                t0 = time.perf_counter()
                try:
                    snapshot = self._service.fetch_snapshot()
                    delay_ms = (time.perf_counter() - t0) * 1000
                    self._metrics.record_sample(delay_ms, success=True)
                    self.data_ready.emit(snapshot)
                    # 每次成功采样都广播最新通信指标
                    comm = self._metrics.get_comm_metrics()
                    self.comm_metrics_ready.emit(comm)
                    # 检查 ALM-08/09 状态变化
                    self._check_alerts(comm)
                except Exception as e:
                    delay_ms = (time.perf_counter() - t0) * 1000
                    # 失败采样同样记录耗时（失败前等待时长）
                    self._metrics.record_sample(
                        delay_ms, success=False, error=e
                    )
                    self.error_occurred.emit(e)
                    # 失败也推送指标，便于 UI 实时反映掉线
                    comm = self._metrics.get_comm_metrics()
                    self.comm_metrics_ready.emit(comm)
                    # 检查 ALM-08/09 状态变化
                    self._check_alerts(comm)
            self.msleep(self._interval)

    def _check_alerts(self, comm: CommMetrics) -> None:
        """根据 CommMetrics 触发/恢复 ALM-08（采样延迟）和 ALM-09（连续失败）。"""
        # ALM-08：采样延迟过高（仅在成功样本上判断，避免把失败等待误判为延迟）
        if comm.max_delay_ms >= ALM_08_LATENCY_THRESHOLD_MS and not self._alm08_active:
            self._alm08_active = True
            self.alert_external_trigger.emit("ALM-08", comm.max_delay_ms)
        elif comm.max_delay_ms < ALM_08_LATENCY_THRESHOLD_MS and self._alm08_active:
            self._alm08_active = False
            self.alert_external_recover.emit("ALM-08")

        # ALM-09：通信连续失败
        if (
            comm.consecutive_failures >= ALM_09_CONSEC_FAILURES_THRESHOLD
            and not self._alm09_active
        ):
            self._alm09_active = True
            self.alert_external_trigger.emit(
                "ALM-09", float(comm.consecutive_failures)
            )
        elif (
            comm.consecutive_failures == 0 and self._alm09_active
        ):
            self._alm09_active = False
            self.alert_external_recover.emit("ALM-09")

    def stop(self) -> None:
        self._active = False
        self.wait(5000)
