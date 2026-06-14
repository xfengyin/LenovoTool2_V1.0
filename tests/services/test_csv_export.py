"""Tests for CSV export service."""

import tempfile
from pathlib import Path

from lenovo_tool.services.csv_export import CSVExportService


def test_write_row_creates_file():
    """Writing a row should create the file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        svc = CSVExportService(filepath)
        svc.write_row({"voltage": 12450, "current": -1500})
        svc.close()

        assert filepath.exists()
        content = filepath.read_text()
        assert "voltage" in content
        assert "12450" in content


def test_write_row_includes_header():
    """First write should include header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        svc = CSVExportService(filepath)
        svc.write_row({"a": 1, "b": 2})
        svc.close()

        content = filepath.read_text().strip()
        lines = content.splitlines()
        assert len(lines) >= 2
        assert "a" in lines[0]
        assert "b" in lines[0]


def test_append_multiple_rows():
    """Multiple rows should be appended."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        svc = CSVExportService(filepath)
        svc.write_row({"a": 1})
        svc.write_row({"a": 2})
        svc.write_row({"a": 3})
        svc.close()

        lines = filepath.read_text().strip().splitlines()
        # header + 3 data rows
        assert len(lines) == 4


def test_context_manager():
    """CSVExportService should work as context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test.csv"
        with CSVExportService(filepath) as svc:
            svc.write_row({"x": 100})
        assert filepath.exists()
