"""SMBus register address constants and register catalog.

Consolidates the register dictionaries from legacy LogWord.py and LogBlock.py
into a single typed data structure.
"""

from dataclasses import dataclass
from enum import IntEnum, auto

from lenovo_tool.core.unit_definitions import (
    BLOCK_UNITS,
    CMD_HEX_UNITS,
    CMD_INT_UNITS,
    MODE_CHARGE_UNITS,
    PREDICTED_HEX_UNITS,
    SMBUS_MESSAGE_UNITS,
    TEMPERATURE_UNITS,
)


class RegisterCategory(IntEnum):
    WORD_INT = auto()
    WORD_NEG = auto()
    WORD_HEX = auto()
    TEMPERATURE = auto()
    MODE_BIT = auto()
    SMBUS_MESSAGE = auto()
    BLOCK_SUBFIELD = auto()
    SOH_CALCULATED = auto()
    PREDICTED_HEX = auto()


# Standard SBS word register addresses
class WordRegister(IntEnum):
    MANUFACTURER_ACCESS = 0x00
    REMAINING_CAP_ALARM = 0x01
    REMAINING_TIME_ALARM = 0x02
    BATTERY_MODE = 0x03
    AT_RATE = 0x04
    AT_RATE_TIME_TO_FULL = 0x05
    AT_RATE_TIME_TO_EMPTY = 0x06
    AT_RATE_OK = 0x07
    TEMPERATURE = 0x08
    VOLTAGE = 0x09
    CURRENT = 0x0A
    AVERAGE_CURRENT = 0x0B
    MAX_ERROR = 0x0C
    RSOC = 0x0D
    ABSOLUTE_SOC = 0x0E
    REMAINING_CAPACITY = 0x0F
    FULL_CHARGE_CAPACITY = 0x10
    RUN_TIME_TO_EMPTY = 0x11
    AVERAGE_TIME_TO_EMPTY = 0x12
    AVERAGE_TIME_TO_FULL = 0x13
    CHARGING_CURRENT = 0x14
    CHARGING_VOLTAGE = 0x15
    BATTERY_STATUS = 0x16
    CYCLE_COUNT = 0x17
    DESIGN_CAPACITY = 0x18
    DESIGN_VOLTAGE = 0x19
    TRUE_REM_CAP = 0x24
    TRUE_FCC = 0x25
    SMART_CHARGE_BIT = 0x26
    FET_TEMPERATURE = 0x3B
    OPT_COMMAND_2 = 0x3E
    OPT_COMMAND_1 = 0x3F
    FIRST_USAGE_TIME = 0x3F
    SOH = 0x4F
    LIGHT_CHARGE_BIT = 0x50
    PL1 = 0x60
    PL2 = 0x61
    PL4 = 0x62
    BATTERY_HEALTH_STATE = 0x6A
    BATTERY_LIFE_CYCLE = 0x6B
    BATTERY_LIFE_SPAN = 0x6C
    ENTRY_SHIP_MODE_COUNT = 0xA4
    ENTRY_EXIT_SHIP_CONDITION = 0xA5
    SHIP_MODE_TIMER = 0xA6


# Block register addresses
class BlockRegister(IntEnum):
    CELL_VOLTAGES = 0x23
    TOTAL_CHARGED = 0x30
    TTS_MODELS = 0x90


@dataclass(frozen=True, slots=True)
class RegisterInfo:
    """Immutable description of a single register field."""

    address: int
    name: str
    unit: str
    category: RegisterCategory
    block_offset: int = 0
    block_length: int = 2


def _build_register_catalog() -> dict[str, RegisterInfo]:
    """Build the complete register catalog."""
    catalog: dict[str, RegisterInfo] = {}

    # Word — Int registers
    int_words = {
        "RemainingCapacityAlarm": 0x01,
        "RemainingTimeAlarm": 0x02,
        "AtRate": 0x04,
        "AtRateTimeToFul": 0x05,
        "AtRateTimeToEmpty": 0x06,
        "AtRateOK": 0x07,
        "Voltage": 0x09,
        "Current": 0x0A,
        "AverageCurrent": 0x0B,
        "MaxError": 0x0C,
        "RSOC": 0x0D,
        "AbsoluteStateOfCharge": 0x0E,
        "RemainingCapacity": 0x0F,
        "FullChargeCapacity": 0x10,
        "RunTimeToEmpty": 0x11,
        "AverageTimeToEmpty": 0x12,
        "AverageTimeToFull": 0x13,
        "ChargingCurrent": 0x14,
        "ChargingVoltage": 0x15,
        "CycleCount": 0x17,
        "DesignVoltage": 0x19,
        "TrueRemCap": 0x24,
        "TrueFCC": 0x25,
        "EntryShipModeCount": 0xA4,
        "EntryExitShipCondition": 0xA5,
        "ShipModeTimer": 0xA6,
        "PL1": 0x60,
        "PL2": 0x61,
        "PL4": 0x62,
    }
    for name, addr in int_words.items():
        cat = RegisterCategory.WORD_HEX if name == "BatteryMode" else RegisterCategory.WORD_INT
        if name in ("PL1", "PL2", "PL4"):
            cat = RegisterCategory.WORD_NEG
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=CMD_INT_UNITS.get(name, "-"),
            category=cat,
        )

    # BatteryMode — special hex display
    catalog["BatteryMode"] = RegisterInfo(
        address=0x03,
        name="BatteryMode",
        unit="-",
        category=RegisterCategory.WORD_HEX,
    )

    # SOH — calculated
    catalog["SOH"] = RegisterInfo(
        address=0x4F,
        name="SOH",
        unit="%",
        category=RegisterCategory.SOH_CALCULATED,
    )

    # Predicted hex registers
    for name, addr in [
        ("BatteryHealthState", 0x6A),
        ("BatteryLifeCycle", 0x6B),
        ("BatteryLifeSpan", 0x6C),
    ]:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=PREDICTED_HEX_UNITS.get(name, "-"),
            category=RegisterCategory.PREDICTED_HEX,
        )

    # Hex word registers
    for name, addr in [
        ("ManufactuereAccess", 0x00),
        ("BatteryStatus", 0x16),
        ("EntryExitShipCondition", 0xA5),
        ("OptCommand2", 0x3E),
        ("OptCommand1", 0x3F),
    ]:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=CMD_HEX_UNITS.get(name, "-"),
            category=RegisterCategory.WORD_HEX,
        )

    # Temperature registers
    for name, addr in [
        ("Temperature", 0x08),
        ("FETTemperature", 0x3B),
    ]:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=TEMPERATURE_UNITS.get(name, "\u2103"),
            category=RegisterCategory.TEMPERATURE,
        )

    # Mode charge bit registers
    for name, addr in [
        ("SmartChargeBit", 0x26),
        ("LightChargeBit", 0x50),
    ]:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=MODE_CHARGE_UNITS.get(name, "byte"),
            category=RegisterCategory.MODE_BIT,
        )

    # SMBus message registers
    for name, addr in [("FirstUsageTime", 0x3F)]:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=SMBUS_MESSAGE_UNITS.get(name, "date"),
            category=RegisterCategory.SMBUS_MESSAGE,
        )

    # Block subfield registers
    block_entries = [
        ("Total Charged", 0x30, 0),
        ("Total F/W Run Time", 0x30, 2),
        ("HiVolt Time", 0x30, 4),
        ("HiTemp Time", 0x30, 6),
        ("HiTempVolt Time", 0x30, 8),
        ("cell1 voltage", 0x23, 4),
        ("cell2 voltage", 0x23, 6),
        ("cell3 voltage", 0x23, 8),
        ("cell4 voltage", 0x23, 10),
        ("TTS RT Model", 0x90, 0),
        ("TTS LS1-1 Model", 0x90, 2),
        ("TTS LS1-2 Model", 0x90, 4),
        ("TTS LS1-3 Model", 0x90, 6),
        ("TTS LS1-4 Model", 0x90, 8),
        ("TTS LS1-5 Model", 0x90, 10),
        ("TTS LS2 Model", 0x90, 12),
        ("TTS TLS1-1 Model", 0x90, 14),
        ("TTS TLS1-2 Model", 0x90, 16),
        ("TTS TLS1-3 Model", 0x90, 18),
        ("TTS TLS1-4 Model", 0x90, 20),
        ("TTS TLS1-5 Model", 0x90, 22),
        ("TTS PI Model", 0x90, 26),
        ("TTS Current Model", 0x90, 28),
    ]
    for name, addr, offset in block_entries:
        catalog[name] = RegisterInfo(
            address=addr,
            name=name,
            unit=BLOCK_UNITS.get(name, "-"),
            category=RegisterCategory.BLOCK_SUBFIELD,
            block_offset=offset,
        )

    return catalog


REGISTER_CATALOG: dict[str, RegisterInfo] = _build_register_catalog()