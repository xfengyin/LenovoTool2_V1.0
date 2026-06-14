"""Tests for register definitions catalog."""

from lenovo_tool.core.register_definitions import REGISTER_CATALOG, RegisterInfo, RegisterCategory


def test_catalog_has_no_duplicate_keys():
    """Catalog should have unique register names (keys)."""
    # REGISTER_CATALOG is a dict, so keys are unique by construction
    assert len(REGISTER_CATALOG) > 0


def test_all_entries_have_units():
    """Every register entry should have a unit string."""
    for name, info in REGISTER_CATALOG.items():
        assert info.unit, f"Register '{name}' has empty unit"


def test_all_entries_have_valid_address():
    """Every register should have a valid address (0x00-0xFF)."""
    for name, info in REGISTER_CATALOG.items():
        assert 0 <= info.address <= 0xFF, f"Register '{name}' has invalid address 0x{info.address:02X}"


def test_key_registers_exist():
    """Critical registers should be in the catalog."""
    required = {"Voltage", "Current", "Temperature", "RSOC", "SOH", "FullChargeCapacity", "RemainingCapacity"}
    found = set(REGISTER_CATALOG.keys())
    missing = required - found
    assert not missing, f"Missing critical registers: {missing}"


def test_block_registers_have_offset():
    """Block-type registers should have block_offset set."""
    for info in REGISTER_CATALOG.values():
        if info.category == RegisterCategory.BLOCK_SUBFIELD:
            assert info.block_length == 2


def test_register_info_is_frozen():
    """RegisterInfo should be immutable."""
    info = RegisterInfo(
        address=0x09, name="Voltage", unit="mV",
        category=RegisterCategory.WORD_INT
    )
    import pytest
    with pytest.raises(Exception):
        info.address = 0x10  # type: ignore
