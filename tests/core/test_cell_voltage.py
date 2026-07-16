"""CellVoltage 数据类单元测试。

覆盖：spread / min_cell / max_cell / is_balanced / status 属性，
以及作为 frozen dataclass 的不变性。
"""

from dataclasses import FrozenInstanceError

import pytest

from lenovo_tool.core.data_models import CellVoltage


def _cells(c1: int, c2: int, c3: int, c4: int) -> CellVoltage:
    return CellVoltage(cell1=c1, cell2=c2, cell3=c3, cell4=c4)


class TestCellVoltageSpread:
    """spread 属性：返回 max - min（mV）。"""

    def test_spread_all_equal(self):
        cv = _cells(4000, 4000, 4000, 4000)
        assert cv.spread == 0

    def test_spread_two_extremes(self):
        cv = _cells(4100, 4150, 4200, 4250)
        assert cv.spread == 150

    def test_spread_negative_order(self):
        # 顺序不影响计算
        cv = _cells(4250, 4100, 4200, 4150)
        assert cv.spread == 150

    def test_spread_single_max(self):
        cv = _cells(3000, 3000, 3000, 4500)
        assert cv.spread == 1500

    def test_spread_min_in_middle(self):
        cv = _cells(4200, 4100, 4300, 4250)
        assert cv.spread == 200  # 4100 ~ 4300


class TestCellVoltageMinMax:
    """min_cell / max_cell 返回 (index, value)，index 从 1 开始。"""

    def test_min_cell_first(self):
        cv = _cells(4000, 4200, 4150, 4100)
        assert cv.min_cell == (1, 4000)

    def test_min_cell_last(self):
        cv = _cells(4200, 4150, 4100, 4050)
        assert cv.min_cell == (4, 4050)

    def test_min_cell_tie_keeps_first_occurrence(self):
        # min 取首次出现的最小值（Python min 语义）
        cv = _cells(4200, 4000, 4000, 4100)
        assert cv.min_cell == (2, 4000)

    def test_max_cell_first(self):
        cv = _cells(4300, 4200, 4150, 4100)
        assert cv.max_cell == (1, 4300)

    def test_max_cell_last(self):
        cv = _cells(4200, 4150, 4100, 4400)
        assert cv.max_cell == (4, 4400)

    def test_max_cell_tie_keeps_first_occurrence(self):
        cv = _cells(4400, 4400, 4300, 4200)
        assert cv.max_cell == (1, 4400)


class TestCellVoltageIsBalanced:
    """is_balanced = spread < 30 mV。"""

    @pytest.mark.parametrize("cells,expected", [
        ((4150, 4150, 4150, 4150), True),
        ((4150, 4155, 4152, 4148), True),   # spread=7
        ((4150, 4180, 4150, 4150), False),  # spread=30 -> 不平衡（< 30 严格）
        ((4100, 4150, 4200, 4250), False),  # spread=150
    ])
    def test_is_balanced_threshold(self, cells, expected):
        cv = _cells(*cells)
        assert cv.is_balanced is expected

    def test_is_balanced_boundary_29(self):
        # 严格小于 30 才平衡；spread=29 视为平衡
        cv = _cells(4150, 4150, 4150, 4179)
        assert cv.spread == 29
        assert cv.is_balanced is True

    def test_is_balanced_boundary_30(self):
        cv = _cells(4150, 4150, 4150, 4180)
        assert cv.spread == 30
        assert cv.is_balanced is False


class TestCellVoltageStatus:
    """status 状态：<30 normal, <100 warning, >=100 critical。"""

    def test_status_normal(self):
        cv = _cells(4150, 4155, 4152, 4148)
        assert cv.spread == 7
        assert cv.status == "normal"

    def test_status_warning(self):
        # spread=50 在 (30, 100) 区间 → warning
        cv = _cells(4150, 4200, 4150, 4150)
        assert cv.spread == 50
        assert cv.status == "warning"

    def test_status_warning_upper_boundary(self):
        # spread=99 < 100 仍然 warning
        cv = _cells(4100, 4100, 4100, 4199)
        assert cv.spread == 99
        assert cv.status == "warning"

    def test_status_critical(self):
        # spread=100 已是 critical（>= 100）
        cv = _cells(4100, 4100, 4100, 4200)
        assert cv.spread == 100
        assert cv.status == "critical"

    def test_status_critical_extreme(self):
        cv = _cells(3000, 4500, 3500, 4000)
        assert cv.spread == 1500
        assert cv.status == "critical"

    def test_status_all_equal(self):
        cv = _cells(4000, 4000, 4000, 4000)
        assert cv.spread == 0
        assert cv.status == "normal"


class TestCellVoltageImmutability:
    """CellVoltage 是 frozen dataclass，字段不可写。"""

    def test_cannot_modify_cell1(self):
        cv = _cells(4000, 4000, 4000, 4000)
        with pytest.raises(FrozenInstanceError):
            cv.cell1 = 5000  # type: ignore[misc]

    def test_cannot_modify_cell4(self):
        cv = _cells(4000, 4000, 4000, 4000)
        with pytest.raises(FrozenInstanceError):
            cv.cell4 = 5000  # type: ignore[misc]

    def test_equality_by_value(self):
        a = _cells(4000, 4100, 4200, 4300)
        b = _cells(4000, 4100, 4200, 4300)
        assert a == b

    def test_inequality(self):
        a = _cells(4000, 4100, 4200, 4300)
        b = _cells(4000, 4100, 4200, 4301)
        assert a != b


class TestCellVoltageInBatterySnapshot:
    """CellVoltage 作为 BatterySnapshot.cell_voltages 字段的集成测试。"""

    def test_battery_snapshot_default_none(self):
        from datetime import datetime
        from lenovo_tool.core.data_models import BatterySnapshot
        snap = BatterySnapshot(
            timestamp=datetime(2026, 7, 16, 12, 0, 0),
            voltage=12450, current=-1500, temperature=35.0,
            rsoc=75, soh=95, fcc=6000, rm=4500,
            dc=6200, dv=15500, battery_mode=0x6001,
            pl1=45, pl2=65, pl4=90,
        )
        # 默认值为 None，向后兼容
        assert snap.cell_voltages is None

    def test_battery_snapshot_with_cell_voltages(self):
        from datetime import datetime
        from lenovo_tool.core.data_models import BatterySnapshot
        cv = _cells(4150, 4152, 4147, 4151)
        snap = BatterySnapshot(
            timestamp=datetime(2026, 7, 16, 12, 0, 0),
            voltage=12450, current=-1500, temperature=35.0,
            rsoc=75, soh=95, fcc=6000, rm=4500,
            dc=6200, dv=15500, battery_mode=0x6001,
            pl1=45, pl2=65, pl4=90,
            cell_voltages=cv,
        )
        assert snap.cell_voltages is not None
        assert snap.cell_voltages.spread == 5
        assert snap.cell_voltages.status == "normal"
