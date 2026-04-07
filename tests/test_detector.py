"""Tests for detector module."""

from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess
import pytest

from agent_bench.detector import detect_agent, detect_all, detect_from_config, AgentInfo


class TestDetectAgent:
    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    def test_installed_agent(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(stdout="claude 1.0.0", stderr="")
        info = detect_agent("claude-code")
        assert info.installed
        assert info.path == "/usr/bin/claude"
        assert "1.0.0" in info.version

    @patch("shutil.which", return_value=None)
    def test_not_installed(self, mock_which):
        info = detect_agent("claude-code")
        assert not info.installed

    @patch("shutil.which", return_value="/usr/bin/codex")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="test", timeout=10))
    def test_version_fails(self, mock_run, mock_which):
        info = detect_agent("codex-cli")
        assert info.installed
        assert info.version == ""


class TestDetectAll:
    @patch("shutil.which", return_value=None)
    def test_returns_all_agents(self, mock_which):
        results = detect_all()
        assert len(results) > 0
        assert all(isinstance(r, AgentInfo) for r in results)


class TestDetectFromConfig:
    @patch("shutil.which", return_value=None)
    def test_config_agents(self, mock_which):
        config = {"claude-code": {"command": "claude"}, "codex-cli": {"command": "codex"}}
        results = detect_from_config(config)
        assert len(results) == 2


class TestAgentInfo:
    def test_str_installed(self):
        info = AgentInfo(name="test", installed=True, path="/usr/bin/test", version="1.0")
        assert "1.0" in str(info)

    def test_str_not_installed(self):
        info = AgentInfo(name="test")
        assert "not found" in str(info)
