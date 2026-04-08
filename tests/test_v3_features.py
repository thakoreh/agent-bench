"""Tests for v0.3.0: --parallel/--model CLI flags, delete command, trend command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.storage import Storage


# ── Storage: delete_run Tests ───────────────────────────────────────

class TestDeleteRun:
    def test_delete_existing_run(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("test-run-1", "fix the bug", [
            {"agent_name": "claude", "exit_code": 0, "duration_seconds": 10.0,
             "tokens_in": 1000, "tokens_out": 500, "cost": 0.01,
             "files_changed": 2, "lines_added": 10, "lines_removed": 3,
             "test_pass": 5, "test_total": 5, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 85.0, "quality_grade": "B", "stdout": "", "stderr": ""},
        ])
        assert storage.get_run("test-run-1") is not None
        result = storage.delete_run("test-run-1")
        assert result is True
        assert storage.get_run("test-run-1") is None
        storage.close()

    def test_delete_nonexistent_run(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        result = storage.delete_run("no-such-run")
        assert result is False
        storage.close()

    def test_delete_cleans_results(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-a", "task", [
            {"agent_name": "agent1", "exit_code": 0, "duration_seconds": 5.0,
             "tokens_in": 100, "tokens_out": 50, "cost": 0.01,
             "files_changed": 1, "lines_added": 5, "lines_removed": 2,
             "test_pass": 3, "test_total": 3, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 90.0, "quality_grade": "A-", "stdout": "", "stderr": ""},
            {"agent_name": "agent2", "exit_code": 0, "duration_seconds": 8.0,
             "tokens_in": 200, "tokens_out": 100, "cost": 0.02,
             "files_changed": 3, "lines_added": 15, "lines_removed": 5,
             "test_pass": 3, "test_total": 3, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 80.0, "quality_grade": "B", "stdout": "", "stderr": ""},
        ])
        storage.delete_run("run-a")
        data = storage.get_run("run-a")
        assert data is None
        storage.close()


# ── Storage: get_agent_history Tests ────────────────────────────────

class TestGetAgentHistory:
    def test_agent_history_basic(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-1", "task a", [
            {"agent_name": "claude", "exit_code": 0, "duration_seconds": 10.0,
             "tokens_in": 1000, "tokens_out": 500, "cost": 0.01,
             "files_changed": 2, "lines_added": 10, "lines_removed": 3,
             "test_pass": 5, "test_total": 5, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 85.0, "quality_grade": "B", "stdout": "", "stderr": ""},
        ])
        storage.save_run("run-2", "task b", [
            {"agent_name": "codex", "exit_code": 0, "duration_seconds": 12.0,
             "tokens_in": 800, "tokens_out": 400, "cost": 0.008,
             "files_changed": 1, "lines_added": 8, "lines_removed": 2,
             "test_pass": 4, "test_total": 4, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 90.0, "quality_grade": "A-", "stdout": "", "stderr": ""},
        ])
        # Claude should have 1 result
        claude_history = storage.get_agent_history("claude")
        assert len(claude_history) == 1
        assert claude_history[0]["agent_name"] == "claude"

        # Codex should have 1 result
        codex_history = storage.get_agent_history("codex")
        assert len(codex_history) == 1

        # Unknown agent should have 0 results
        unknown_history = storage.get_agent_history("unknown")
        assert len(unknown_history) == 0
        storage.close()


# ── CLI: delete command Tests ───────────────────────────────────────

class TestDeleteCLI:
    def test_delete_with_force(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("to-delete", "task", [
            {"agent_name": "agent1", "exit_code": 0, "duration_seconds": 5.0,
             "tokens_in": 100, "tokens_out": 50, "cost": 0.01,
             "files_changed": 1, "lines_added": 5, "lines_removed": 2,
             "test_pass": 3, "test_total": 3, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 90.0, "quality_grade": "A-", "stdout": "", "stderr": ""},
        ])
        storage.close()

        runner = CliRunner()
        with patch("agent_bench.cli.Storage", return_value=Storage(path=tmp_path / "test.db")):
            result = runner.invoke(cli, ["delete", "to-delete", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_not_found(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("agent_bench.cli.Storage", return_value=Storage(path=tmp_path / "test.db")):
            result = runner.invoke(cli, ["delete", "nonexistent", "--force"])
        assert "not found" in result.output


# ── CLI: trend command Tests ────────────────────────────────────────

class TestTrendCLI:
    def test_trend_no_runs(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("agent_bench.cli.Storage", return_value=Storage(path=tmp_path / "test.db")):
            result = runner.invoke(cli, ["trend"])
        assert result.exit_code == 0
        assert "No benchmark runs" in result.output

    def test_trend_with_data(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-1", "task a", [
            {"agent_name": "claude", "exit_code": 0, "duration_seconds": 10.0,
             "tokens_in": 1000, "tokens_out": 500, "cost": 0.01,
             "files_changed": 2, "lines_added": 10, "lines_removed": 3,
             "test_pass": 5, "test_total": 5, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 70.0, "quality_grade": "C", "stdout": "", "stderr": ""},
        ])
        storage.save_run("run-2", "task b", [
            {"agent_name": "claude", "exit_code": 0, "duration_seconds": 12.0,
             "tokens_in": 800, "tokens_out": 400, "cost": 0.008,
             "files_changed": 1, "lines_added": 8, "lines_removed": 2,
             "test_pass": 4, "test_total": 4, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 85.0, "quality_grade": "B", "stdout": "", "stderr": ""},
        ])
        storage.close()

        runner = CliRunner()
        with patch("agent_bench.cli.Storage", return_value=Storage(path=tmp_path / "test.db")):
            result = runner.invoke(cli, ["trend"])
        assert result.exit_code == 0
        assert "claude" in result.output

    def test_trend_json(self, tmp_path: Path) -> None:
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-1", "task a", [
            {"agent_name": "claude", "exit_code": 0, "duration_seconds": 10.0,
             "tokens_in": 1000, "tokens_out": 500, "cost": 0.01,
             "files_changed": 2, "lines_added": 10, "lines_removed": 3,
             "test_pass": 5, "test_total": 5, "lint_errors": 0, "lint_warnings": 0,
             "quality_score": 70.0, "quality_grade": "C", "stdout": "", "stderr": ""},
        ])
        storage.close()

        runner = CliRunner()
        with patch("agent_bench.cli.Storage", return_value=Storage(path=tmp_path / "test.db")):
            result = runner.invoke(cli, ["trend", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "claude" in data
        assert len(data["claude"]) == 1
        assert data["claude"][0]["score"] == 70.0


# ── CLI: run command flags ──────────────────────────────────────────

class TestRunFlags:
    def test_run_help_shows_parallel(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--parallel" in result.output

    def test_run_help_shows_model(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--model" in result.output


# ── Scorer: Additional Edge Cases ───────────────────────────────────

class TestScorerEdgeCases:
    def test_complexity_empty_code(self) -> None:
        from agent_bench.scorer import compute_complexity_score
        assert compute_complexity_score("") == 50.0

    def test_complexity_whitespace_only(self) -> None:
        from agent_bench.scorer import compute_complexity_score
        assert compute_complexity_score("   \n  \t  ") == 50.0

    def test_complexity_simple_code(self) -> None:
        from agent_bench.scorer import compute_complexity_score
        code = "def hello():\n    print('hello')\n"
        score = compute_complexity_score(code)
        assert 0 <= score <= 100

    def test_letter_grade_boundaries(self) -> None:
        from agent_bench.scorer import _letter_grade
        assert _letter_grade(100) == "A"
        assert _letter_grade(93) == "A"
        assert _letter_grade(92.9) == "A-"
        assert _letter_grade(90) == "A-"
        assert _letter_grade(50) == "F"
        assert _letter_grade(0) == "F"
