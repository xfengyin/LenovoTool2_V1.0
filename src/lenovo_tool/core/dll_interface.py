"""Thread-safe wrapper around SWD_EC.dll and Sunwoda.dll.

All DLL calls are:
- Protected by threading.RLock for thread safety
- Wrapped in try/except with proper error types
- Validated with explicit ctypes argtypes/restype

Implements BatteryDataSource interface for DI compatibility.
"""

import logging
import threading
import time
from ctypes import CDLL, c_char, c_int, c_short, pointer
from typing import Dict

from lenovo_tool.core.interfaces import BatteryDataSource
from lenovo_tool.core.dll_loader import DLLPaths
from lenovo_tool.core.exceptions import DLLCommunicationError, SMBusError
from lenovo_tool.core.register_definitions import WordRegister
from lenovo_tool.services.life_prediction import predict_life_months

logger = logging.getLogger(__name__)


class DLLInterface(BatteryDataSource):
    """Thread-safe interface to battery EC via SWD_EC.dll and Sunwoda.dll."""

    def __init__(self, dll_paths: DLLPaths) -> None:
        self._lock = threading.RLock()
        self._swd_ec = self._load_swd_ec(dll_paths.swd_ec_path)
        self._sunwoda = self._load_sunwoda(dll_paths.sunwoda_path)
        self._setup_signatures()

    def _load_swd_ec(self, path: object) -> object:
        try:
            dll = CDLL(str(path))
        except OSError as e:
            raise DLLCommunicationError(
                f"Failed to load SWD_EC.dll: {e}"
            ) from e
        return dll

    def _load_sunwoda(self, path: object) -> object:
        try:
            dll = CDLL(str(path))
        except OSError as e:
            raise DLLCommunicationError(
                f"Failed to load Sunwoda.dll: {e}"
            ) from e
        return dll

    def _setup_signatures(self) -> None:
        self._swd_ec.Smbus_ReadIntWord.argtypes = [c_int]
        self._swd_ec.Smbus_ReadIntWord.restype = c_int

        self._swd_ec.Smbus_ReadWord.argtypes = [c_int]
        self._swd_ec.Smbus_ReadWord.restype = c_short

        self._swd_ec.Smbus_ReadBlock.argtypes = [c_int, c_int, c_int]
        self._swd_ec.Smbus_ReadBlock.restype = c_int

        self._sunwoda.SMBusWrite.argtypes = [
            c_int, c_char, pointer(c_char * 32), c_char,
        ]
        self._sunwoda.SMBusWrite.restype = None

        self._sunwoda.SMBusRead.argtypes = [
            c_int, c_short, pointer(c_char * 32), c_short,
        ]
        self._sunwoda.SMBusRead.restype = None

    # -- Word reads ----------------------------------------------------------

    def read_int_word(self, addr: int) -> int:
        """Read unsigned 16-bit value from register address."""
        with self._lock:
            try:
                return self._swd_ec.Smbus_ReadIntWord(addr)
            except OSError as e:
                raise DLLCommunicationError(
                    f"SMBus read failed at 0x{addr:02X}: {e}"
                ) from e

    def read_neg_word(self, addr: int) -> int:
        """Read signed 16-bit value from register address."""
        with self._lock:
            try:
                return self._swd_ec.Smbus_ReadWord(addr)
            except OSError as e:
                raise DLLCommunicationError(
                    f"SMBus read failed at 0x{addr:02X}: {e}"
                ) from e

    # -- Block reads ---------------------------------------------------------

    def read_block(self, addr: int, start: int, length: int) -> int:
        """Read a block of data from the EC."""
        with self._lock:
            try:
                result = self._swd_ec.Smbus_ReadBlock(addr, start, length)
            except OSError as e:
                raise DLLCommunicationError(
                    f"SMBus block read failed at 0x{addr:02X}: {e}"
                ) from e
        time.sleep(0.005)
        return result

    # -- SMBus write/read ----------------------------------------------------

    def write_smbus(
        self, type_: int, addr: int, slave: int, mode_state: bool
    ) -> None:
        """Write a command to the EC via SMBus.

        Args:
            type_: 0 = block, 1 = word
            addr: register address
            slave: slave address (typically 0x16)
            mode_state: True = mode on, False = mode off
        """
        char_buffer = (c_char * 32)()
        char_buffer[0] = 0x01 if mode_state is False else 0x03
        with self._lock:
            try:
                self._sunwoda.SMBusWrite(
                    c_int(type_),
                    c_char(bytes([addr])),
                    pointer(char_buffer),
                    c_char(bytes([slave])),
                )
            except OSError as e:
                raise DLLCommunicationError(
                    f"SMBus write failed at 0x{addr:02X}, "
                    f"slave=0x{slave:02X}: {e}"
                ) from e

    def read_smbus(
        self, type_: int, addr: int, byte_length: int, slave: int
    ) -> Dict[str, str]:
        """Read data from the EC via SMBus.

        Args:
            type_: 0 = block, 1 = word
            addr: register address
            byte_length: number of bytes to read
            slave: slave address
        """
        if type_ not in (0, 1):
            raise ValueError("type_ must be 0 (block) or 1 (word)")

        data: dict[str, str] = {}
        char_type = c_char if type_ == 0 else c_short
        array_type = char_type * 32
        char_buffer = array_type()

        with self._lock:
            try:
                self._sunwoda.SMBusRead(
                    c_int(type_),
                    c_short(addr),
                    pointer(char_buffer),
                    c_short(slave),
                )
            except OSError as e:
                raise SMBusError(
                    f"SMBus read failed at 0x{addr:02X}: {e}"
                ) from e

        if type_ == 0:
            for i in range(byte_length):
                data[f"byte{i}"] = f"{char_buffer[i][0]:02x}"
        else:
            for i in range(byte_length):
                data[f"word{i}"] = str(char_buffer[i])

        return data

    # -- Derived calculations ------------------------------------------------

    def get_temperature(self, addr: int = 0x08) -> float:
        """Read temperature in Kelvin and convert to Celsius."""
        raw = self.read_int_word(addr)
        return raw / 10.0 - 273.15

    def get_first_usage_time(self, addr: int = 0x3F) -> str:
        """Decode BCD-encoded first usage date."""
        raw = self.read_int_word(addr)
        year = raw // 512 + 1980
        month = (raw - (year - 1980) * 512) // 32
        day = raw - (year - 1980) * 512 - month * 32
        return f"{year}-{month}-{day}"

    def life_prediction(self, addr: int = WordRegister.BATTERY_HEALTH_STATE.value) -> int:
        """Predict remaining battery life in months from register 0x6A.

        委托给 :func:`lenovo_tool.services.life_prediction.predict_life_months`
        以保证算法实现唯一。
        """
        raw = self.read_int_word(addr)
        return predict_life_months(raw)

    def read_soh(self) -> int:
        """Calculate State of Health from FCC / Design Capacity."""
        fcc = self.read_neg_word(0x10)
        dc = self.read_neg_word(0x18)
        if dc <= 0:
            return 0
        soh = int(fcc / dc * 100)
        return min(soh, 100)

    # -- Atomic snapshot (for DataAcquisitionService) ------------------------

    def read_all_main_registers(self) -> Dict[str, int | float]:
        """Read all main data registers under a single lock.

        Returns a dict with keys: voltage, current, temperature, rsoc, soh,
        fcc, rm, dc, dv, battery_mode, pl1, pl2, pl4, life_raw,
        cycle_count, cell_voltages.
        """
        with self._lock:
            voltage = self.read_int_word(WordRegister.VOLTAGE.value)
            current = self.read_neg_word(WordRegister.CURRENT.value)
            temperature = self.get_temperature(WordRegister.TEMPERATURE.value)
            rsoc = self.read_int_word(WordRegister.RSOC.value)
            soh = self.read_soh()
            fcc = self.read_int_word(WordRegister.FULL_CHARGE_CAPACITY.value)
            rm = self.read_int_word(WordRegister.REMAINING_CAPACITY.value)
            dc = self.read_int_word(WordRegister.DESIGN_CAPACITY.value)
            dv = self.read_int_word(WordRegister.DESIGN_VOLTAGE.value)
            battery_mode = self.read_int_word(WordRegister.BATTERY_MODE.value)
            pl1 = self.read_neg_word(WordRegister.PL1.value)
            pl2 = self.read_neg_word(WordRegister.PL2.value)
            pl4 = self.read_neg_word(WordRegister.PL4.value)
            life_raw = self.read_int_word(
                WordRegister.BATTERY_HEALTH_STATE.value
            )
            # 0x17 CycleCount — 真实硬件下循环次数，缺失会导致恒为 0
            cycle_count = self.read_int_word(WordRegister.CYCLE_COUNT.value)

        # Cell voltage block (0x23) - 4 芯 × 2 字节 big-endian
        # 优先使用 read_smbus 读取块字节；旧式 read_block 只返回 int
        cell_voltages: object = None
        try:
            block_data = self.read_smbus(0, 0x23, 8, 0x16)
            from lenovo_tool.core.data_models import CellVoltage
            if block_data and len(block_data) >= 8:
                c1 = (int(block_data["byte0"], 16) << 8) | int(block_data["byte1"], 16)
                c2 = (int(block_data["byte2"], 16) << 8) | int(block_data["byte3"], 16)
                c3 = (int(block_data["byte4"], 16) << 8) | int(block_data["byte5"], 16)
                c4 = (int(block_data["byte6"], 16) << 8) | int(block_data["byte7"], 16)
                cell_voltages = CellVoltage(c1, c2, c3, c4)
            else:
                cell_voltages = None
        except Exception as e:
            logger.debug("Cell voltage read failed: %s", e)
            cell_voltages = None

        return {
            "voltage": voltage,
            "current": current,
            "temperature": temperature,
            "rsoc": rsoc,
            "soh": soh,
            "fcc": fcc,
            "rm": rm,
            "dc": dc,
            "dv": dv,
            "battery_mode": battery_mode,
            "pl1": pl1,
            "pl2": pl2,
            "pl4": pl4,
            "life_raw": life_raw,
            "cycle_count": cycle_count,
            "cell_voltages": cell_voltages,
        }