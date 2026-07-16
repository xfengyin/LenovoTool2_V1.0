"""AlertEngine 单元测试。

覆盖：
- 10 条规则的触发与恢复
- 去抖（debounce）控制
- 阈值热更新
- 外部触发 / 恢复
- 清空与声音开关
"""

import sys
from datetime import datetime

import pytest
from PySide6.QtCore import QCoreApplication

from lenovo_tool.core.data_models import BatterySnapshot, CellVoltage
from lenovo_tool.services.alert_engine import ALERT_RULES, AlertEngine


def make_snapshot(**overrides):
    """构造一个默认健康（不触发任何告警）的 BatterySnapshot，可通过 kwargs 覆盖。

    默认电压 15500 mV：介于 15480*0.9 (13932) 与 15480*1.05 (16254) 之间，
    保证 ALM-05/06 不会因默认电压而误触发。
    """
    defaults = dict(
        timestamp=datetime.now(),
        voltage=15500,        # 落在 dv 0.9~1.05 范围内
        current=-320,
        temperature=42.0,     # 低于 60 阈值
        rsoc=66,              # 高于 20 阈值
        soh=92,               # 高于 50 阈值
        fcc=5000,
        rm=3300,
        dc=5000,
        dv=15480,
        battery_mode="0x00",
        pl1=45,
        pl2=65,
        pl4=80,
        predicted_life_months=24,  # 高于 6 阈值
        cycle_count=247,
        first_usage_time="2024-03-15",
        charge_state="charging",
        max_temperature=45.0,
        min_voltage=15200,
        max_voltage=16520,
        cell_voltages=CellVoltage(4128, 4132, 4125, 4130),  # spread=7 < 50
        fet_temperature=38.0,    # 低于 80 阈值
    )
    defaults.update(overrides)
    return BatterySnapshot(**defaults)


@pytest.fixture(scope="session")
def qapp():
    """共享 QCoreApplication，Qt Signal 需要事件循环对象存在。"""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


class TestAlertEngine:
    def test_init(self, qapp):
        engine = AlertEngine()
        assert engine.get_active_count() == 0
        assert engine.get_active() == []
        assert len(engine.get_thresholds()) == 10
        assert engine.is_sound_enabled() is True
        assert engine.has_critical() is False

    def test_all_rules_have_required_fields(self, qapp):
        """规则元数据完整性：确保没有遗漏字段。"""
        for rule in ALERT_RULES:
            assert rule["id"].startswith("ALM-")
            assert rule["level"] in ("critical", "warning")
            assert callable(rule["check"])
            assert isinstance(rule["default_threshold"], (int, float))
            assert isinstance(rule["message"], str)

    def test_temperature_alert_triggers(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        s = make_snapshot(temperature=70.0)
        engine.evaluate(s)
        assert engine.get_active_count() == 1
        assert triggered[0].alert_id == "ALM-01"
        assert triggered[0].level == "critical"
        assert triggered[0].current_value == 70.0
        assert triggered[0].threshold == 60.0
        assert engine.has_critical() is True

    def test_temperature_alert_recovers(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        s_hot = make_snapshot(temperature=70.0)
        s_cold = make_snapshot(temperature=30.0)
        engine.evaluate(s_hot)
        assert engine.get_active_count() == 1
        recovered = []
        engine.alert_recovered.connect(lambda aid, e: recovered.append(aid))
        engine.evaluate(s_cold)
        assert engine.get_active_count() == 0
        assert "ALM-01" in recovered

    def test_fet_temperature_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(fet_temperature=90.0))
        assert any(e.alert_id == "ALM-02" for e in triggered)

    def test_fet_temperature_none_skipped(self, qapp):
        """fet_temperature 为 None 时不应触发 ALM-02。"""
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(fet_temperature=None))
        assert not any(e.alert_id == "ALM-02" for e in triggered)

    def test_soh_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(soh=40))
        assert any(e.alert_id == "ALM-03" for e in triggered)

    def test_rsoc_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(rsoc=10))
        assert any(e.alert_id == "ALM-04" for e in triggered)

    def test_voltage_high_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(voltage=18000, dv=15480))
        assert any(e.alert_id == "ALM-05" for e in triggered)

    def test_voltage_low_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(voltage=13000, dv=15480))
        assert any(e.alert_id == "ALM-06" for e in triggered)

    def test_voltage_alert_skipped_when_dv_zero(self, qapp):
        """dv<=0 时不评估 ALM-05/06（保护避免除零/误报）。"""
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(voltage=99999, dv=0))
        assert not any(e.alert_id == "ALM-05" for e in triggered)
        assert not any(e.alert_id == "ALM-06" for e in triggered)

    def test_cell_spread_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(cell_voltages=CellVoltage(4000, 4150, 4050, 4100)))
        assert any(e.alert_id == "ALM-07" for e in triggered)

    def test_life_alert(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(predicted_life_months=3))
        assert any(e.alert_id == "ALM-10" for e in triggered)

    def test_debounce(self, qapp):
        engine = AlertEngine(debounce_seconds=10.0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        s = make_snapshot(temperature=70.0)
        engine.evaluate(s)
        engine.evaluate(s)
        engine.evaluate(s)
        assert len(triggered) == 1

    def test_threshold_change(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        engine.set_threshold("ALM-01", 30.0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.evaluate(make_snapshot(temperature=35.0))
        assert any(e.alert_id == "ALM-01" for e in triggered)

    def test_get_thresholds_returns_copy(self, qapp):
        """get_thresholds 返回副本，外部修改不影响内部状态。"""
        engine = AlertEngine()
        t = engine.get_thresholds()
        t["ALM-01"] = -999
        assert engine.get_thresholds()["ALM-01"] != -999

    def test_external_trigger(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        triggered = []
        engine.alert_triggered.connect(lambda e: triggered.append(e))
        engine.trigger_external("ALM-08", 250.0)
        assert engine.get_active_count() == 1
        assert triggered[0].alert_id == "ALM-08"
        assert triggered[0].current_value == 250.0

    def test_external_trigger_unknown_id(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        # 不存在的 id 应静默忽略
        engine.trigger_external("ALM-XX", 1.0)
        assert engine.get_active_count() == 0

    def test_external_recover(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        engine.trigger_external("ALM-08", 250.0)
        assert engine.get_active_count() == 1
        recovered = []
        engine.alert_recovered.connect(lambda aid, e: recovered.append(aid))
        engine.recover_external("ALM-08")
        assert engine.get_active_count() == 0
        assert "ALM-08" in recovered

    def test_external_recover_no_op_when_inactive(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        # 未触发的告警调用 recover_external 应为 no-op
        engine.recover_external("ALM-08")
        assert engine.get_active_count() == 0

    def test_external_debounce(self, qapp):
        engine = AlertEngine(debounce_seconds=10.0)
        engine.trigger_external("ALM-09", 5)
        engine.trigger_external("ALM-09", 5)
        engine.trigger_external("ALM-09", 5)
        assert engine.get_active_count() == 1

    def test_clear_all(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        engine.evaluate(make_snapshot(temperature=70.0, soh=30, predicted_life_months=3))
        assert engine.get_active_count() >= 2
        engine.clear_all()
        assert engine.get_active_count() == 0

    def test_sound_enabled_toggle(self, qapp):
        engine = AlertEngine()
        assert engine.is_sound_enabled() is True
        engine.set_sound_enabled(False)
        assert engine.is_sound_enabled() is False

    def test_active_alerts_changed_signal(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        changes = []
        engine.active_alerts_changed.connect(lambda lst: changes.append(list(lst)))
        engine.evaluate(make_snapshot(temperature=70.0, soh=30))
        assert len(changes) >= 1
        assert len(changes[-1]) == 2

    def test_recovery_event_has_recovery_time(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        engine.evaluate(make_snapshot(temperature=70.0))
        recovered_events = []
        engine.alert_recovered.connect(lambda aid, e: recovered_events.append(e))
        engine.evaluate(make_snapshot(temperature=30.0))
        assert recovered_events[0].recovered is True
        assert recovered_events[0].recovery_time is not None

    def test_get_active_ids(self, qapp):
        engine = AlertEngine(debounce_seconds=0)
        engine.evaluate(make_snapshot(temperature=70.0, soh=30))
        ids = engine.get_active_ids()
        assert "ALM-01" in ids
        assert "ALM-03" in ids
