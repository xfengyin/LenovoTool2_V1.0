"""Mock DLL with realistic battery simulation for demo mode.

Implements the same interface as BatteryDataSource for seamless switching.
"""

import random
import threading
import time

from lenovo_tool.core.data_models import CellVoltage


class DemoDLLInterface:
    """Mock DLL with realistic battery simulation.

    Implements the same interface as DLLInterface for seamless switching.
    """

    _lock = threading.RLock()

    def __init__(self) -> None:
        self._soh = random.randint(90, 98)
        self._last_soh_tick = time.monotonic()
        self._rsoc = random.randint(60, 95)
        self._rsoc_dir = -1
        self._cycle_count = random.randint(50, 200)
        self._tick = 0

    def read_int_word(self, addr: int) -> int:
        return self._mock_value(addr)

    def read_neg_word(self, addr: int) -> int:
        val = self._mock_value(addr)
        if addr in (0x0A, 0x60, 0x61, 0x62):
            return -abs(val) % 8000
        return val

    def read_block(self, addr: int, start: int, length: int) -> int:
        return int(random.uniform(100, 5000))

    def write_smbus(self, type_: int, addr: int, slave: int, mode_state: bool) -> None:
        return None

    def read_smbus(self, type_: int, addr: int, byte_length: int, slave: int) -> dict[str, str]:
        return {f"byte{i}": f"{random.randint(0, 255):02x}" for i in range(byte_length)}

    def get_temperature(self, addr: int = 0x08) -> float:
        return round(random.uniform(28.0, 45.0), 1)

    def get_first_usage_time(self, addr: int = 0x3F) -> str:
        return "2023-06-15"

    def life_prediction(self, addr: int = 0x6A) -> int:
        if self._soh >= 90:
            return 36
        elif self._soh >= 80:
            return 24
        elif self._soh >= 60:
            return 12
        elif self._soh >= 40:
            return 6
        return 0

    def read_soh(self) -> int:
        now = time.monotonic()
        if now - self._last_soh_tick > 30:
            self._last_soh_tick = now
            if random.random() < 0.3:
                self._soh = max(40, self._soh - 1)
        return self._soh

    def read_all_main_registers(self) -> dict[str, int | float]:
        voltage = self.read_int_word(0x09)
        current = self.read_neg_word(0x0A)
        temperature = self.get_temperature(0x08)

        self._rsoc += self._rsoc_dir * random.randint(1, 3)
        if self._rsoc <= 15:
            self._rsoc_dir = 1
        elif self._rsoc >= 98:
            self._rsoc_dir = -1
        self._rsoc = max(0, min(100, self._rsoc))

        soh = self.read_soh()
        dc = self.read_int_word(0x18)
        fcc = int(dc * soh / 100)
        rm = int(fcc * self._rsoc / 100)

        if random.random() < 0.05:
            self._cycle_count += 1

        # 模拟 4 芯电压（围绕基础值波动，4125-4175 范围）
        self._tick += 1
        base = 4150 + (self._tick % 50) - 25
        cell_voltages = CellVoltage(
            cell1=base + 0,
            cell2=base + 2,
            cell3=base - 3,
            cell4=base + 1,
        )

        # 模拟 FET 温度（比电池温度高 3~8℃），与 chart_window 联动
        fet_temperature = round(
            temperature + random.uniform(3.0, 8.0), 1
        )

        return {
            "voltage": voltage,
            "current": current,
            "temperature": temperature,
            "rsoc": self._rsoc,
            "soh": soh,
            "fcc": fcc,
            "rm": rm,
            "dc": dc,
            "dv": self.read_int_word(0x19),
            "battery_mode": self.read_int_word(0x03),
            "pl1": self.read_neg_word(0x60),
            "pl2": self.read_neg_word(0x61),
            "pl4": self.read_neg_word(0x62),
            "life_raw": self.read_int_word(0x6A),
            "cycle_count": self._cycle_count,
            "cell_voltages": cell_voltages,
            "fet_temperature": fet_temperature,
        }

    @staticmethod
    def _mock_value(addr: int) -> int:
        values: dict[int, int] = {
            0x09: int(random.uniform(12000, 17000)),
            0x0A: int(random.uniform(-3000, 5000)),
            0x0D: random.randint(30, 100),
            0x0F: random.randint(1000, 7000),
            0x10: random.randint(3000, 8000),
            0x18: random.randint(6000, 6500),
            0x19: random.randint(14000, 16000),
            0x03: 0x6001,
            0x60: int(random.uniform(15, 65)),
            0x61: int(random.uniform(30, 90)),
            0x62: int(random.uniform(50, 130)),
            0x6A: random.choice([1792, 1536, 1280, 1024, 500]),
            0x4F: random.randint(80, 100),
        }
        return values.get(addr, int(random.uniform(0, 65535)))