"""历史数据持久化仓库 - SQLite 本地存储。

提供电池采样数据的本地持久化与时间序列查询能力：
- 自动建表 + 索引（按 session_id/timestamp 优化查询）
- 内存缓冲批量写入（减少磁盘 I/O）
- 线程安全（互斥锁保护连接）
- 内置保留期清理策略

设计要点：
- 缓冲写入：单条 insert 只入内存 buffer，buffer 满或显式 flush 才落盘
- SQL 注入防护：所有查询使用参数化语句
- 无效数据容错：None / 转换异常自动跳过，不影响整体查询
"""

import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from lenovo_tool.core.data_models import BatterySnapshot

logger = logging.getLogger(__name__)


# 可查询的指标白名单（防止 SQL 注入）
_VALID_METRICS: frozenset[str] = frozenset(
    {
        "voltage", "current", "temperature", "rsoc", "soh",
        "fcc", "rm", "dc", "dv", "cell1", "cell2", "cell3", "cell4",
        "fet_temp", "pl1", "pl2", "pl4", "cycle_count",
        "predicted_life", "delay_ms",
    }
)


class HistoryRepository:
    """电池历史数据 SQLite 仓库。

    表结构：
    - battery_samples: 单次采样的所有字段，按 session_id 和 timestamp 建索引。
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS battery_samples (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL,
        timestamp   TEXT NOT NULL,
        voltage     INTEGER,
        current     INTEGER,
        temperature REAL,
        rsoc        INTEGER,
        soh         INTEGER,
        fcc         INTEGER,
        rm          INTEGER,
        dc          INTEGER,
        dv          INTEGER,
        cell1       INTEGER,
        cell2       INTEGER,
        cell3       INTEGER,
        cell4       INTEGER,
        fet_temp    REAL,
        pl1         INTEGER,
        pl2         INTEGER,
        pl4         INTEGER,
        cycle_count INTEGER,
        predicted_life INTEGER,
        delay_ms    REAL
    );
    CREATE INDEX IF NOT EXISTS idx_session_ts
        ON battery_samples(session_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_timestamp
        ON battery_samples(timestamp);
    """

    def __init__(
        self,
        db_path: str = "data/battery_history.db",
        buffer_size: int = 100,
    ) -> None:
        self._db_path: str = db_path
        self._buffer_size: int = max(1, int(buffer_size))
        self._buffer: list[tuple] = []
        # 使用 RLock 以支持在持锁状态下调用 _flush()（如 query_range / cleanup_old）
        self._lock = threading.RLock()
        # 确保父目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("HistoryRepository initialized at %s", db_path)

    def _init_db(self) -> None:
        """初始化表结构（仅创建缺失的表/索引）。"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.executescript(self.SCHEMA)
                conn.commit()
            finally:
                conn.close()

    def insert(
        self,
        snapshot: BatterySnapshot,
        session_id: str,
        delay_ms: float = 0.0,
    ) -> None:
        """插入单条数据，buffer 满时批量写入。

        Args:
            snapshot: 电池快照对象。
            session_id: 会话 ID（区分不同采集会话）。
            delay_ms: 该次采样的采集耗时（毫秒）。
        """
        row = self._to_row(snapshot, session_id, delay_ms)
        self._buffer.append(row)
        if len(self._buffer) >= self._buffer_size:
            self._flush()

    def _to_row(
        self, s: BatterySnapshot, sid: str, delay_ms: float
    ) -> tuple:
        """将 BatterySnapshot 转换为数据库行。"""
        cv = s.cell_voltages
        return (
            sid,
            s.timestamp.isoformat(),
            s.voltage, s.current, s.temperature, s.rsoc, s.soh,
            s.fcc, s.rm, s.dc, s.dv,
            cv.cell1 if cv else None,
            cv.cell2 if cv else None,
            cv.cell3 if cv else None,
            cv.cell4 if cv else None,
            s.temperature,  # fet_temp: 当前温度作为 FET 温度近似
            s.pl1, s.pl2, s.pl4,
            s.cycle_count, s.predicted_life_months,
            delay_ms,
        )

    def _flush(self) -> None:
        """将 buffer 中所有数据批量写入数据库。"""
        with self._lock:
            if not self._buffer:
                return
            conn = sqlite3.connect(self._db_path)
            try:
                conn.executemany(
                    """INSERT INTO battery_samples
                    (session_id, timestamp, voltage, current, temperature,
                     rsoc, soh, fcc, rm, dc, dv, cell1, cell2, cell3, cell4,
                     fet_temp, pl1, pl2, pl4, cycle_count, predicted_life, delay_ms)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    self._buffer,
                )
                conn.commit()
            except Exception as e:
                # 不抛出，避免阻塞采集；记录错误供诊断
                logger.error("DB flush failed: %s", e)
            finally:
                conn.close()
                self._buffer.clear()

    def query_range(
        self,
        start: datetime,
        end: datetime,
        metric: str = "voltage",
    ) -> list[tuple[datetime, float]]:
        """查询时间范围内某指标的数据点。

        Args:
            start: 起始时间（含）。
            end: 结束时间（含）。
            metric: 指标名，必须在白名单内。

        Returns:
            [(时间, 数值), ...] 列表，按时间升序。

        Raises:
            ValueError: 当 metric 不在白名单中。
        """
        if metric not in _VALID_METRICS:
            raise ValueError(f"Invalid metric: {metric}")
        with self._lock:
            # 查询前确保数据全部落盘
            self._flush()
            conn = sqlite3.connect(self._db_path)
            try:
                cur = conn.execute(
                    f"SELECT timestamp, {metric} FROM battery_samples "
                    f"WHERE timestamp BETWEEN ? AND ? "
                    f"ORDER BY timestamp",
                    (start.isoformat(), end.isoformat()),
                )
                results: list[tuple[datetime, float]] = []
                for ts_str, val in cur.fetchall():
                    if val is None:
                        continue
                    try:
                        results.append((datetime.fromisoformat(ts_str), float(val)))
                    except (ValueError, TypeError):
                        # 时间/数值格式异常时跳过该行
                        continue
                return results
            finally:
                conn.close()

    def get_session_ids(self) -> list[str]:
        """获取所有出现过的不重复 session_id 列表（倒序）。"""
        with self._lock:
            self._flush()
            conn = sqlite3.connect(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT DISTINCT session_id FROM battery_samples "
                    "ORDER BY session_id DESC"
                )
                return [row[0] for row in cur.fetchall()]
            finally:
                conn.close()

    def cleanup_old(self, days: int = 30) -> int:
        """删除 days 天前的数据。

        Args:
            days: 保留天数；早于该天数的数据将被删除。

        Returns:
            实际删除的记录数。
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock:
            self._flush()
            conn = sqlite3.connect(self._db_path)
            try:
                cur = conn.execute(
                    "DELETE FROM battery_samples WHERE timestamp < ?", (cutoff,)
                )
                conn.commit()
                count = cur.rowcount
                logger.info(
                    "Cleaned up %d old records (older than %d days)", count, days
                )
                return count
            finally:
                conn.close()

    def close(self) -> None:
        """关闭前确保数据全部落盘。"""
        self._flush()
