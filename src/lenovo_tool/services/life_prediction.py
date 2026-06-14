"""Battery life prediction service.

Algorithm from Lenovo engineering spec, register 0x6A bits 11:8:
  level1 (0111): >36 months, SOH >= 90%
  level2 (0110): >24 months, SOH >= 80%
  level3 (0101): >12 months
  level4 (0100): >6 months
  level5 (0011): Battery damage (PF set)
  level0: Capacity degradation, SOH < 40%
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LifeLevel:
    """Description of a predicted life level."""
    months: int
    label: str
    description: str


LIFE_LEVELS: tuple[LifeLevel, ...] = (
    LifeLevel(36, "Excellent", "Predicted lifespan > 36 months, SOH >= 90%"),
    LifeLevel(24, "Good", "Predicted lifespan > 24 months, SOH >= 80%"),
    LifeLevel(12, "Fair", "Predicted lifespan > 12 months"),
    LifeLevel(6, "Poor", "Predicted lifespan > 6 months"),
    LifeLevel(0, "Critical", "Battery damage or capacity degradation, SOH < 40%"),
)


THRESHOLD_LEVEL1: int = 1792  # 0x0700
THRESHOLD_LEVEL2: int = 1536  # 0x0600
THRESHOLD_LEVEL3: int = 1280  # 0x0500
THRESHOLD_LEVEL4: int = 1024  # 0x0400


def predict_life_months(raw_value: int) -> int:
    """Predict remaining battery life in months from register 0x6A raw value."""
    if raw_value >= THRESHOLD_LEVEL1:
        return 36
    elif raw_value >= THRESHOLD_LEVEL2:
        return 24
    elif raw_value >= THRESHOLD_LEVEL3:
        return 12
    elif raw_value >= THRESHOLD_LEVEL4:
        return 6
    else:
        return 0


def get_life_level(months: int) -> LifeLevel:
    """Get the LifeLevel description for a given month value."""
    for level in LIFE_LEVELS:
        if months >= level.months:
            return level
    return LIFE_LEVELS[-1]


class LifePredictionService:
    """Service for battery life prediction."""

    def predict(self, raw_value: int) -> int:
        """Return predicted lifespan in months."""
        return predict_life_months(raw_value)

    def get_level(self, months: int) -> LifeLevel:
        """Return life level description."""
        return get_life_level(months)
