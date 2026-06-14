"""Tests for life prediction service."""

import pytest

from lenovo_tool.services.life_prediction import predict_life_months, get_life_level, LifeLevel


@pytest.mark.parametrize("raw,expected", [
    (1792, 36),   # Level 1
    (1800, 36),
    (65535, 36),
    (1536, 24),   # Level 2
    (1600, 24),
    (1791, 24),
    (1280, 12),   # Level 3
    (1400, 12),
    (1535, 12),
    (1024, 6),    # Level 4
    (1100, 6),
    (1279, 6),
    (0, 0),       # Level 0
    (500, 0),
    (1023, 0),
])
def test_predict_life_months(raw, expected):
    assert predict_life_months(raw) == expected


def test_get_life_level_36():
    level = get_life_level(36)
    assert level.months == 36
    assert level.label == "Excellent"


def test_get_life_level_0():
    level = get_life_level(0)
    assert level.months == 0
    assert level.label == "Critical"


def test_get_life_level_6():
    level = get_life_level(6)
    assert level.months == 6
