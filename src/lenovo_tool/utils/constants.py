"""Application-wide constants."""

# SMBus slave address for battery EC
BATTERY_SLAVE_ADDR: int = 0x16

# SMBus command types
SMBUS_BLOCK_TYPE: int = 0
SMBUS_WORD_TYPE: int = 1

# Register addresses used by the main data worker
MAIN_DATA_REGISTERS: dict[str, int] = {
    "Temperature": 0x08,
    "RSOC": 0x0D,
    "SOH": 0x4F,
    "BatteryMode": 0x03,
    "Voltage": 0x09,
    "Current": 0x0A,
    "FCC": 0x10,
    "RM": 0x0F,
    "DC": 0x18,
    "DV": 0x19,
    "PL1": 0x60,
    "PL2": 0x61,
    "PL4": 0x62,
    "LifePrediction": 0x6A,
}

# Charge mode configuration
FAST_CHARGE_ADDR: int = 0x26
NIGHT_CHARGE_ADDR: int = 0x50

# Life prediction thresholds
LIFE_THRESHOLDS: dict[str, int] = {
    "LEVEL_1": 1792,  # 0x0700 — >36 months
    "LEVEL_2": 1536,  # 0x0600 — >24 months
    "LEVEL_3": 1280,  # 0x0500 — >12 months
    "LEVEL_4": 1024,  # 0x0400 — >6 months
}
