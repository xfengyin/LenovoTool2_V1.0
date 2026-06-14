"""Unit strings for all SMBus registers. Single source of truth."""

CMD_INT_UNITS: dict[str, str] = {
    "RemainingCapacityAlarm": "10 mWh",
    "RemainingTimeAlarm": "min",
    "BatteryMode": "-",
    "AtRate": "10 mWh",
    "AtRateTimeToFul": "min",
    "AtRateTimeToEmpty": "min",
    "AtRateOK": "-",
    "Voltage": "mV",
    "Current": "mA",
    "AverageCurrent": "mA",
    "MaxError": "%",
    "RSOC": "%",
    "AbsoluteStateOfCharge": "%",
    "RemainingCapacity": "10 mWh",
    "FullChargeCapacity": "10 mWh",
    "RunTimeToEmpty": "min",
    "AverageTimeToEmpty": "min",
    "AverageTimeToFull": "min",
    "ChargingCurrent": "mA",
    "ChargingVoltage": "mV",
    "CycleCount": "cycles",
    "DesignVoltage": "mV",
    "TrueRemCap": "-",
    "TrueFCC": "-",
    "SOH": "%",
    "EntryShipModeCount": "-",
    "EntryExitShipCondition": "-",
    "ShipModeTimer": "h",
    "PL1": "W",
    "PL2": "W",
    "PL4": "W",
}

PREDICTED_HEX_UNITS: dict[str, str] = {
    "BatteryHealthState": "-",
    "BatteryLifeCycle": "-",
    "BatteryLifeSpan": "-",
}

CMD_HEX_UNITS: dict[str, str] = {
    "ManufactuereAccess": "-",
    "BatteryStatus": "-",
    "EntryExitShipCondition": "-",
    "OptCommand2": "-",
    "OptCommand1": "-",
}

TEMPERATURE_UNITS: dict[str, str] = {
    "Temperature": "℃",
    "FETTemperature": "℃",
}

MODE_CHARGE_UNITS: dict[str, str] = {
    "SmartChargeBit": "byte",
    "LightChargeBit": "byte",
}

SMBUS_MESSAGE_UNITS: dict[str, str] = {
    "FirstUsageTime": "date",
}

BLOCK_UNITS: dict[str, str] = {
    "Total Charged": "Wh",
    "Total F/W Run Time": "h",
    "HiVolt Time": "h",
    "HiTemp Time": "h",
    "HiTempVolt Time": "h",
    "cell1 voltage": "mV",
    "cell2 voltage": "mV",
    "cell3 voltage": "mV",
    "cell4 voltage": "mV",
    "TTS RT Model": "h",
    "TTS LS1-1 Model": "h",
    "TTS LS1-2 Model": "h",
    "TTS LS1-3 Model": "h",
    "TTS LS1-4 Model": "h",
    "TTS LS1-5 Model": "h",
    "TTS LS2 Model": "h",
    "TTS TLS1-1 Model": "h",
    "TTS TLS1-2 Model": "h",
    "TTS TLS1-3 Model": "h",
    "TTS TLS1-4 Model": "h",
    "TTS TLS1-5 Model": "h",
    "TTS PI Model": "h",
    "TTS Current Model": "h",
}

ALL_UNITS: dict[str, str] = {
    **CMD_INT_UNITS,
    **PREDICTED_HEX_UNITS,
    **CMD_HEX_UNITS,
    **TEMPERATURE_UNITS,
    **MODE_CHARGE_UNITS,
    **SMBUS_MESSAGE_UNITS,
    **BLOCK_UNITS,
}
