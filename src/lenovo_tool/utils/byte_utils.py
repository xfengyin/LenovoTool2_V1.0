"""Byte swapping, type conversion, and encoding utilities.

Ported from legacy DataHtoDataL.py with type hints and edge-case handling.
Consolidates all byte/data transformation helpers into a single module.
"""

from binascii import a2b_hex


def swap_bytes(value: int) -> int:
    """Swap high byte and low byte of a 16-bit value."""
    high = (value & 0xFF00) >> 8
    low = value & 0xFF
    return (low << 8) | high


def to_unsigned(value: int) -> int:
    """Convert 16-bit signed short to unsigned."""
    return value & 0xFFFF


def to_signed(value: int) -> int:
    """Convert 16-bit unsigned to signed short."""
    return value if value < 0x8000 else value - 0x10000


def kelvin_to_celsius(raw: int) -> float:
    """Convert raw temperature (Kelvin * 10) to Celsius."""
    return raw / 10.0 - 273.15


def hex_to_ascii(value: int) -> str:
    """Convert 16-bit hex value to ASCII string."""
    hex_str = f"{value:04x}"
    raw = bytes(hex_str, "utf-8")
    return a2b_hex(raw).decode()


def format_hex(value: int) -> str:
    """Format integer as zero-padded 4-digit hex string."""
    return f"{value & 0xFFFF:04x}"