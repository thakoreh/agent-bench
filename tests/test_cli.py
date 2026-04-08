"""Tests for CLI module."""

from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from agent_bench.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestInit:
    def test_init_creates_config(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_init_existing_config(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"])
            result = runner.invoke(cli, ["init"])
            assert "already exists" in result.output


class TestAgents:
    @patch("agent_bench.cli.detect_all")
    def test_agents_lists(self, mock_detect, runner):
        from agent_bench.detector import AgentInfo
        mock_detect.return_value = [
            AgentInfo(name="claude-code", installed=True, path="/usr/bin/claude"),
            AgentInfo(name="codex-cli", installed=False),
        ]
        result = runner.invoke(cli, ["agents"])
        assert result.exit_code == 0
        assert "claude-code" in result.output


class TestResults:
    @patch("agent_bench.cli.Storage")
    def test_no_results(self, mock_storage_cls, runner):
        mock_storage = MagicMock()
        mock_storage.get_latest_run.return_value = None
        mock_storage_cls.return_value = mock_storage
        result = runner.invoke(cli, ["results"])
        assert "No results found" in result.output


class TestHistory:
    @patch("agent_bench.cli.Storage")
    def test_no_history(self, mock_storage_cls, runner):
        mock_storage = MagicMock()
        mock_storage.list_runs.return_value = []
        mock_storage_cls.return_value = mock_storage
        result = runner.invoke(cli, ["history"])
        assert "No benchmark" in result.output


class TestVersion:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert "0.3.0" in result.output
