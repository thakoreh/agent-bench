"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from agent_bench.config import Config, DEFAULT_CONFIG


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temp config file."""
    cfg = tmp_path / ".agent-bench.yaml"
    cfg.write_text(yaml.dump(DEFAULT_CONFIG))
    return cfg


def test_load_config(tmp_config):
    config = Config(path=tmp_config)
    assert "claude-code" in config.agents
    assert config.default_task


def test_default_config_when_no_file():
    config = Config(path=Path("/nonexistent"))
    assert "claude-code" in config.agents


def test_save_config(tmp_path):
    config = Config(path=Path("/nonexistent"))
    target = tmp_path / "test.yaml"
    saved = config.save(target)
    assert saved.exists()
    data = yaml.safe_load(saved.read_text())
    assert "agents" in data


def test_timeout_property(tmp_config):
    config = Config(path=tmp_config)
    assert config.timeout == 300


def test_run_tests_property(tmp_config):
    config = Config(path=tmp_config)
    assert config.run_tests is True


def test_run_lint_property(tmp_config):
    config = Config(path=tmp_config)
    assert config.run_lint is True


def test_get_agent_config(tmp_config):
    config = Config(path=tmp_config)
    cfg = config.get_agent_config("claude-code")
    assert cfg["command"] == "claude"


def test_get_missing_agent(tmp_config):
    config = Config(path=tmp_config)
    assert config.get_agent_config("nonexistent") == {}


def test_data_property(tmp_config):
    config = Config(path=tmp_config)
    d = config.data
    assert isinstance(d, dict)
    assert "agents" in d


def test_custom_task_in_config(tmp_path):
    cfg = tmp_path / "custom.yaml"
    cfg.write_text(yaml.dump({"default-task": "custom task", "agents": {}, "scoring": {}}))
    config = Config(path=cfg)
    assert config.default_task == "custom task"


def test_partial_config_merges_defaults(tmp_path):
    cfg = tmp_path / "partial.yaml"
    cfg.write_text(yaml.dump({"default-task": "partial"}))
    config = Config(path=cfg)
    assert config.default_task == "partial"
    assert "agents" in config.data
