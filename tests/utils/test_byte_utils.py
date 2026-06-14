"""Tests for byte utility functions."""

import pytest

from lenovo_tool.utils.byte_utils import swap_bytes, to_signed, to_unsigned, kelvin_to_celsius


def test_swap_bytes_simple():
    assert swap_bytes(0x1234) == 0x3412


def test_swap_bytes_zeros():
    assert swap_bytes(0x0000) == 0x0000


def test_swap_bytes_ff():
    assert swap_bytes(0x00FF) == 0xFF00


def test_to_unsigned_positive():
    assert to_unsigned(0x1234) == 0x1234


def test_to_unsigned_negative():
    assert to_unsigned(0xFFFF) == 0xFFFF


def test_to_signed_positive():
    assert to_signed(0x1234) == 0x1234


def test_to_signed_negative():
    assert to_signed(0xFFFF) == -1


def test_to_signed_boundary():
    assert to_signed(0x8000) == -32768


def test_kelvin_to_celsius_freezing():
    assert kelvin_to_celsius(2732) == pytest.approx(0.0, abs=0.1)


def test_kelvin_to_celsius_room_temp():
    assert kelvin_to_celsius(2982) == pytest.approx(25.0, abs=0.5)


def test_kelvin_to_celsius_battery_temp():
    assert kelvin_to_celsius(3082) == pytest.approx(35.0, abs=0.5)
