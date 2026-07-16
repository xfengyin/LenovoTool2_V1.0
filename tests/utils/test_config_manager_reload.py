"""Tests for config manager reload and watch functionality."""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from lenovo_tool.utils.config_manager import ConfigManager


def test_get_method_with_nested_key():
    """ConfigManager.get should support nested key paths."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Test App
  window_width: 800
polling:
  main_interval_ms: 2000
"""
        )

        mgr = ConfigManager(config_path=config_path)

        assert mgr.get("app.title") == "Test App"
        assert mgr.get("app.window_width") == 800
        assert mgr.get("polling.main_interval_ms") == 2000
        assert mgr.get("nonexistent.key", "default") == "default"


def test_get_method_with_default():
    """ConfigManager.get should return default for missing keys."""
    mgr = ConfigManager(config_path="nonexistent.yaml")

    assert mgr.get("app.title") == "Lenovo Battery Tool"
    assert mgr.get("nonexistent.key") is None
    assert mgr.get("nonexistent.key", "fallback") == "fallback"


def test_reload_updates_config():
    """ConfigManager.reload should update config from file."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Original Title
"""
        )

        mgr = ConfigManager(config_path=config_path)
        assert mgr.config.window_title == "Original Title"

        config_path.write_text(
            """app:
  title: Updated Title
"""
        )

        mgr.reload()
        assert mgr.config.window_title == "Updated Title"


def test_watch_callback_triggered_on_change():
    """ConfigManager.watch should trigger callback on file change."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Initial Title
"""
        )

        mgr = ConfigManager(config_path=config_path)
        callback_called = []

        def callback():
            callback_called.append(True)

        mgr.watch(callback)

        time.sleep(0.1)

        config_path.write_text(
            """app:
  title: Changed Title
"""
        )

        time.sleep(2.5)

        mgr.unwatch(callback)

        assert len(callback_called) >= 1
        assert mgr.config.window_title == "Changed Title"


def test_watch_multiple_callbacks():
    """ConfigManager should support multiple callbacks."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Initial
"""
        )

        mgr = ConfigManager(config_path=config_path)
        callback1_count = [0]
        callback2_count = [0]

        def callback1():
            callback1_count[0] += 1

        def callback2():
            callback2_count[0] += 1

        mgr.watch(callback1)
        mgr.watch(callback2)

        time.sleep(0.1)

        config_path.write_text(
            """app:
  title: Changed
"""
        )

        time.sleep(2.5)

        mgr.unwatch(callback1)
        mgr.unwatch(callback2)

        assert callback1_count[0] >= 1
        assert callback2_count[0] >= 1


def test_unwatch_stops_callback():
    """ConfigManager.unwatch should stop callback from being called."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: First
"""
        )

        mgr = ConfigManager(config_path=config_path)
        callback_count = [0]

        def callback():
            callback_count[0] += 1

        mgr.watch(callback)

        time.sleep(0.1)

        config_path.write_text(
            """app:
  title: Second
"""
        )

        time.sleep(2.5)
        first_count = callback_count[0]

        mgr.unwatch(callback)

        config_path.write_text(
            """app:
  title: Third
"""
        )

        time.sleep(2.5)

        assert callback_count[0] == first_count


def test_reload_notifies_callbacks():
    """ConfigManager.reload should notify callbacks when config changes."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Before
"""
        )

        mgr = ConfigManager(config_path=config_path)
        callback_called = []

        def callback():
            callback_called.append(True)

        mgr.watch(callback)

        config_path.write_text(
            """app:
  title: After
"""
        )

        mgr.reload()

        mgr.unwatch(callback)

        assert len(callback_called) >= 1


def test_no_callback_on_unchanged_reload():
    """ConfigManager should not notify callbacks when config unchanged."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.yaml"
        config_path.write_text(
            """app:
  title: Same
"""
        )

        mgr = ConfigManager(config_path=config_path)
        callback_called = []

        def callback():
            callback_called.append(True)

        mgr.watch(callback)

        mgr.reload()

        mgr.unwatch(callback)

        assert len(callback_called) == 0


def test_watch_with_nonexistent_file():
    """ConfigManager.watch should not start thread for nonexistent file."""
    mgr = ConfigManager(config_path="nonexistent_file.yaml")
    callback_called = []

    def callback():
        callback_called.append(True)

    mgr.watch(callback)

    assert mgr._watch_thread is None
    mgr.unwatch(callback)


def test_conforms_to_config_provider_protocol():
    """ConfigManager should conform to ConfigProvider protocol."""
    from lenovo_tool.core.interfaces import ConfigProvider

    mgr = ConfigManager(config_path="nonexistent.yaml")

    assert hasattr(mgr, "get")
    assert hasattr(mgr, "reload")
    assert hasattr(mgr, "watch")
    assert hasattr(mgr, "unwatch")
    assert hasattr(mgr, "config")
