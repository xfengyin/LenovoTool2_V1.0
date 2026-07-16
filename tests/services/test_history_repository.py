"""Tests for HistoryRepository - SQLite 持久化与查询。"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lenovo_tool.core.data_models import BatterySnapshot, CellVoltage
from lenovo_tool.services.history_repository import HistoryRepository


# ----------------------- Fixtures -----------------------

@pytest.fixture()
def repo(tmp_path: Path) -> HistoryRepository:
    """为每个用例创建独立的临时 SQLite 数据库。"""
    db = tmp_path / "history.db"
    return HistoryRepository(db_path=str(db), buffer_size=10)


def _make_snapshot(
    timestamp: datetime,
    *,
    voltage: int = 12000,
    current: int = -1500,
    temperature: float = 30.0,
    rsoc: int = 80,
    soh: int = 95,
    fcc: int = 4500,
    rm: int = 3600,
    dc: int = 4800,
    dv: int = 14400,
    cell1: int = 3600,
    cell2: int = 3610,
    cell3: int = 3620,
    cell4: int = 3630,
    pl1: int = 45,
    pl2: int = 65,
    pl4: int = 90,
    cycle_count: int = 100,
    predicted_life_months: int = 24,
) -> BatterySnapshot:
    """构造一个测试用的 BatterySnapshot。"""
    return BatterySnapshot(
        timestamp=timestamp,
        voltage=voltage,
        current=current,
        temperature=temperature,
        rsoc=rsoc,
        soh=soh,
        fcc=fcc,
        rm=rm,
        dc=dc,
        dv=dv,
        battery_mode=0x6000,
        pl1=pl1,
        pl2=pl2,
        pl4=pl4,
        predicted_life_months=predicted_life_months,
        cycle_count=cycle_count,
        first_usage_time="2024-01-01",
        charge_state="discharging",
        max_temperature=temperature,
        min_voltage=voltage,
        max_voltage=voltage,
        cell_voltages=CellVoltage(
            cell1=cell1, cell2=cell2, cell3=cell3, cell4=cell4
        ),
    )


# ----------------------- Construction -----------------------

def test_init_creates_db_and_tables(tmp_path: Path):
    """初始化时应自动建库、建表、建索引。"""
    db = tmp_path / "history.db"
    assert not db.exists()
    HistoryRepository(db_path=str(db))
    assert db.exists()
    conn = sqlite3.connect(str(db))
    try:
        # 验证表存在
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='battery_samples'"
        )
        assert cur.fetchone() is not None
        # 验证索引存在
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name IN ('idx_session_ts', 'idx_timestamp')"
        )
        names = {row[0] for row in cur.fetchall()}
        assert {"idx_session_ts", "idx_timestamp"}.issubset(names)
    finally:
        conn.close()


def test_init_creates_parent_directory(tmp_path: Path):
    """初始化时应自动创建父目录。"""
    nested = tmp_path / "a" / "b" / "c" / "history.db"
    HistoryRepository(db_path=str(nested))
    assert nested.exists()


# ----------------------- insert & buffer -----------------------

def test_insert_flushes_when_buffer_full(repo: HistoryRepository):
    """当缓冲达到 buffer_size 时应自动落盘。"""
    ts = datetime(2025, 1, 1, 10, 0, 0)
    # buffer_size=10，第 10 条触发 flush
    for i in range(10):
        repo.insert(
            _make_snapshot(
                ts + timedelta(minutes=i),
                voltage=12000 + i,
            ),
            session_id="s1",
        )
    # 验证数据已落盘
    results = repo.query_range(
        ts - timedelta(minutes=1),
        ts + timedelta(hours=1),
        "voltage",
    )
    assert len(results) == 10
    assert results[0][1] == 12000.0
    assert results[-1][1] == 12009.0


def test_explicit_close_flushes_buffer(repo: HistoryRepository):
    """close() 应将剩余缓冲数据落盘。"""
    ts = datetime(2025, 1, 1, 10, 0, 0)
    # buffer_size=10，只插入 3 条（未触发 flush）
    for i in range(3):
        repo.insert(
            _make_snapshot(ts + timedelta(minutes=i)),
            session_id="s1",
        )
    # close 前查询：应通过 flush 后看到数据
    repo.close()
    results = repo.query_range(
        ts - timedelta(minutes=1),
        ts + timedelta(hours=1),
        "voltage",
    )
    assert len(results) == 3


def test_insert_with_multiple_sessions(repo: HistoryRepository):
    """多 session 数据应能被区分。"""
    ts = datetime(2025, 1, 1, 10, 0, 0)
    repo.insert(_make_snapshot(ts, voltage=12000), session_id="s1")
    repo.insert(_make_snapshot(ts, voltage=13000), session_id="s2")
    repo.close()

    sids = repo.get_session_ids()
    assert set(sids) == {"s1", "s2"}


# ----------------------- query_range -----------------------

def test_query_range_filters_by_time(repo: HistoryRepository):
    """应只返回时间范围内的数据。"""
    base = datetime(2025, 1, 1, 10, 0, 0)
    # 写入 10 条连续数据
    for i in range(10):
        repo.insert(
            _make_snapshot(
                base + timedelta(minutes=i),
                voltage=12000 + i,
            ),
            session_id="s1",
        )
    repo.close()
    # 只查 3-6 分钟
    start = base + timedelta(minutes=3)
    end = base + timedelta(minutes=6)
    results = repo.query_range(start, end, "voltage")
    assert len(results) == 4  # minute 3, 4, 5, 6
    assert results[0][1] == 12003.0
    assert results[-1][1] == 12006.0


def test_query_range_invalid_metric_raises(repo: HistoryRepository):
    """非法指标名应抛出 ValueError（防 SQL 注入）。"""
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 1, 1, 0, 0)
    with pytest.raises(ValueError, match="Invalid metric"):
        repo.query_range(start, end, "DROP TABLE battery_samples")
    with pytest.raises(ValueError, match="Invalid metric"):
        repo.query_range(start, end, "evil_field")


def test_query_range_supports_all_metrics(repo: HistoryRepository):
    """应能查询所有白名单指标。"""
    base = datetime(2025, 1, 1, 10, 0, 0)
    repo.insert(
        _make_snapshot(
            base,
            voltage=12000,
            current=-1500,
            temperature=33.5,
            rsoc=85,
            soh=92,
            fcc=4500,
            rm=3800,
            cycle_count=120,
            predicted_life_months=18,
            cell1=3601, cell2=3602, cell3=3603, cell4=3604,
        ),
        session_id="s1",
    )
    repo.close()
    start = base - timedelta(seconds=1)
    end = base + timedelta(seconds=1)
    for metric, expected in [
        ("voltage", 12000.0),
        ("current", -1500.0),
        ("temperature", 33.5),
        ("rsoc", 85.0),
        ("soh", 92.0),
        ("fcc", 4500.0),
        ("rm", 3800.0),
        ("cell1", 3601.0),
        ("cell2", 3602.0),
        ("cell3", 3603.0),
        ("cell4", 3604.0),
        ("cycle_count", 120.0),
        ("predicted_life", 18.0),
    ]:
        results = repo.query_range(start, end, metric)
        assert len(results) == 1, f"metric={metric}"
        assert results[0][1] == expected, f"metric={metric}"


def test_query_range_empty(repo: HistoryRepository):
    """空数据库查询应返回空列表。"""
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 1, 1, 0, 0)
    assert repo.query_range(start, end, "voltage") == []


# ----------------------- get_session_ids -----------------------

def test_get_session_ids_returns_distinct(
    repo: HistoryRepository,
):
    """应返回不重复的 session_id。"""
    ts = datetime(2025, 1, 1, 10, 0, 0)
    for sid in ["s1", "s1", "s2", "s3", "s2"]:
        repo.insert(_make_snapshot(ts), session_id=sid)
    repo.close()
    sids = repo.get_session_ids()
    assert sorted(sids) == ["s1", "s2", "s3"]


def test_get_session_ids_empty(repo: HistoryRepository):
    """空数据库应返回空列表。"""
    assert repo.get_session_ids() == []


# ----------------------- cleanup_old -----------------------

def test_cleanup_old_removes_old_data(repo: HistoryRepository):
    """应删除早于指定天数的数据。"""
    now = datetime.now()
    old_ts = now - timedelta(days=10)
    new_ts = now - timedelta(hours=1)
    repo.insert(_make_snapshot(old_ts, voltage=12000), session_id="s1")
    repo.insert(_make_snapshot(new_ts, voltage=13000), session_id="s1")
    repo.close()

    # 清理 5 天前的数据
    deleted = repo.cleanup_old(days=5)
    assert deleted == 1

    # 仅剩新数据
    results = repo.query_range(
        now - timedelta(days=30), now + timedelta(days=1), "voltage"
    )
    assert len(results) == 1
    assert results[0][1] == 13000.0


def test_cleanup_old_no_old_data(repo: HistoryRepository):
    """无旧数据时返回 0。"""
    now = datetime.now()
    repo.insert(_make_snapshot(now), session_id="s1")
    repo.close()
    assert repo.cleanup_old(days=30) == 0


def test_cleanup_old_returns_count(repo: HistoryRepository):
    """应返回实际删除的条数。"""
    now = datetime.now()
    old_ts = now - timedelta(days=100)
    for i in range(5):
        repo.insert(
            _make_snapshot(old_ts + timedelta(minutes=i)),
            session_id="s1",
        )
    repo.close()
    assert repo.cleanup_old(days=30) == 5


# ----------------------- 并发安全 -----------------------

def test_concurrent_inserts_are_thread_safe(tmp_path: Path):
    """多线程并发 insert 不应损坏数据。"""
    import threading

    db = tmp_path / "concurrent.db"
    # buffer_size=1 强制每次都 flush，增加竞争概率
    repo = HistoryRepository(db_path=str(db), buffer_size=1)
    base = datetime(2025, 1, 1, 10, 0, 0)

    def worker(sid: str, count: int) -> None:
        for i in range(count):
            repo.insert(
                _make_snapshot(
                    base + timedelta(seconds=i),
                    voltage=12000 + i,
                ),
                session_id=sid,
            )

    threads = [
        threading.Thread(target=worker, args=(f"s{i}", 20))
        for i in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    repo.close()

    # 总条数应为 100
    results = repo.query_range(
        base - timedelta(seconds=1),
        base + timedelta(minutes=10),
        "voltage",
    )
    assert len(results) == 100
