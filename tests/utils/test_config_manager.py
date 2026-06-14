"""Tests for configuration manager."""

from lenovo_tool.core.data_models import AppConfig
from lenovo_tool.utils.config_manager import ConfigManager


def test_config_defaults_when_no_file():
    """ConfigManager should use defaults when config file doesn't exist."""
    mgr = ConfigManager(config_path="nonexistent.yaml")
    cfg = mgr.config
    assert isinstance(cfg, AppConfig)
    assert cfg.poll_interval_ms == 4000
    assert cfg.window_title == "Lenovo Battery Tool"


def test_config_property_returns_app_config():
    mgr = ConfigManager(config_path="nonexistent.yaml")
    assert isinstance(mgr.config, AppConfig)


def test_config_reload():
    mgr = ConfigManager(config_path="nonexistent.yaml")
    cfg1 = mgr.config
    mgr.reload()
    cfg2 = mgr.config
    assert cfg1 == cfg2
