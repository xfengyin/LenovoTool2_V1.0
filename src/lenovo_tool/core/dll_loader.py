"""Safe DLL path resolution and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from lenovo_tool.core.exceptions import DLLNotFoundError


@dataclass(frozen=True, slots=True)
class DLLPaths:
    """Resolved paths to required DLLs."""

    swd_ec_path: Path
    sunwoda_path: Path


class DLLLoader:
    """Handles DLL path resolution and loading validation."""

    REQUIRED_DLLS: ClassVar[tuple[str, str]] = ("SWD_EC.dll", "Sunwoda.dll")
    MIN_SIZES: ClassVar[dict[str, int]] = {
        "SWD_EC.dll": 1024,     # At least 1KB
        "Sunwoda.dll": 1024,
    }

    def __init__(self, search_paths: list[str] | None = None):
        self._search_paths = [Path(p) for p in (search_paths or ["./resources/dlls", "./"])]

    def find_dlls(self) -> DLLPaths:
        """Resolve paths to required DLLs. Raises DLLNotFoundError if any missing."""
        swd_ec = self._find("SWD_EC.dll")
        sunwoda = self._find("Sunwoda.dll")
        return DLLPaths(swd_ec_path=swd_ec, sunwoda_path=sunwoda)

    def _find(self, name: str) -> Path:
        for base in self._search_paths:
            candidate = (base / name).resolve()
            if candidate.is_file() and candidate.stat().st_size >= self.MIN_SIZES.get(name, 0):
                return candidate
        raise DLLNotFoundError(
            f"Required DLL '{name}' not found in search paths: "
            f"{[str(p) for p in self._search_paths]}"
        )
