"""Buffered CSV export service for log data.

Ported from legacy Write2File.py with proper file lifecycle management.
"""

import csv
from pathlib import Path
from typing import Any


class CSVExportService:
    """Buffered CSV export for log data with proper file lifecycle."""

    def __init__(self, filepath: str | Path, delimiter: str = ",", encoding: str = "utf-8"):
        self._filepath = Path(filepath)
        self._delimiter = delimiter
        self._encoding = encoding
        self._file = None
        self._writer: csv.DictWriter | None = None
        self._header_written: bool = False

    def open(self) -> None:
        self._file = open(self._filepath, "a", newline="", encoding=self._encoding)

    def write_row(self, data: dict[str, Any]) -> None:
        if self._file is None:
            self.open()
        if not self._header_written:
            self._writer = csv.DictWriter(self._file, fieldnames=list(data.keys()))
            if self._file.tell() == 0:
                self._writer.writeheader()
            self._header_written = True
        self._writer.writerow(data)
        self._file.flush()

    def flush(self) -> None:
        if self._file:
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
            self._header_written = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
