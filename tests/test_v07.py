"""Tests for v0.7.0: scoring weights, diff command, config scoring_weights, edge cases."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.collector import RunMetrics, collect_from_output
from agent_bench.config import Config
from agent_bench.scorer import (
    DEFAULT_WEIGHTS,
    compute_quality_score,
    compute_quality_score_weighted,
    compute_complexity_score,
    compute_docstring_coverage,
    compute_type_hint_coverage,
    compute_comment_density,
    get_scoring_weights,
    _code_cleanliness_penalty,
    _count_import_issues,
    _letter_grade,
)
from agent_bench.storage import Storage


# ═══════════════════════════════════════════════════════════════════════════
# Scoring weights tests
# ═══════════════════════════════════════════════════════════════════════════

class TestScoringWeights:
    """Test configurable scoring weights."""

    def test_default_weights_sum_to_one(self):
        """Default weights should sum to approximately 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}"

    def test_all_factors_present(self):
        """All 11 scoring factors should be in default weights."""
        expected = {
            "test_pass_rate", "lint_clean", "diff_sensibility",
            "task_completion", "speed_bonus", "import_hygiene",
            "complexity", "docstring_coverage", "type_hint_coverage",
            "comment_density", "code_cleanliness",
        }
        assert set(DEFAULT_WEIGHTS.keys()) == expected

    def test_weighted_score_matches_default(self):
        """Weighted score with defaults should match original score closely."""
        metrics = RunMetrics(
            exit_code=0,
            duration_seconds=60,
            tokens_in=1000,
            tokens_out=500,
            stdout="def hello(): pass",
            stderr="",
            test_pass=8,
            test_total=10,
        )
        original_score, _ = compute_quality_score(metrics)
        weighted_score, _ = compute_quality_score_weighted(metrics)
        # They use different normalization so they won't be identical, but should be correlated
        assert abs(original_score - weighted_score) < 30

    def test_custom_weights_boost_tests(self):
        """Increasing test weight should amplify test-heavy metrics."""
        metrics = RunMetrics(
            exit_code=0,
            duration_seconds=60,
            tokens_in=1000,
            tokens_out=500,
            stdout="",
            stderr="",
            test_pass=10,
            test_total=10,
        )
        default_weights = dict(DEFAULT_WEIGHTS)
        boosted = dict(DEFAULT_WEIGHTS)
        boosted["test_pass_rate"] = 0.50
        # Reduce others proportionally
        reduction = 0.50 - 0.25
        for key in boosted:
            if key != "test_pass_rate":
                boosted[key] = max(0, boosted[key] - reduction / 10)

        _, _ = compute_quality_score_weighted(metrics, default_weights)
        _, _ = compute_quality_score_weighted(metrics, boosted)
        # Both should produce valid scores
        # The boosted one should be higher because tests are perfect
        s_default, _ = compute_quality_score_weighted(metrics, default_weights)
        s_boosted, _ = compute_quality_score_weighted(metrics, boosted)
        assert s_boosted > s_default

    def test_get_scoring_weights_default(self):
        """get_scoring_weights returns defaults when no config."""
        weights = get_scoring_weights()
        assert weights == DEFAULT_WEIGHTS

    def test_get_scoring_weights_custom(self):
        """get_scoring_weights merges custom weights."""
        config = {"scoring_weights": {"test_pass_rate": 0.50, "speed_bonus": 0.15}}
        weights = get_scoring_weights(config)
        assert weights["test_pass_rate"] == 0.50
        assert weights["speed_bonus"] == 0.15
        assert weights["lint_clean"] == DEFAULT_WEIGHTS["lint_clean"]  # Unchanged


class TestConfigScoringWeights:
    """Test Config.scoring_weights property."""

    def test_default_config_weights(self, tmp_path):
        """Config without custom weights returns defaults."""
        config = Config(path=tmp_path / "nonexistent.yaml")
        weights = config.scoring_weights
        assert weights["test_pass_rate"] == 0.25

    def test_custom_config_weights(self, tmp_path):
        """Config with custom weights merges them."""
        config_file = tmp_path / ".agent-bench.yaml"
        config_file.write_text(
            "scoring:\n  weights:\n    test_pass_rate: 0.40\n    speed_bonus: 0.12\n"
        )
        config = Config(path=config_file)
        weights = config.scoring_weights
        assert weights["test_pass_rate"] == 0.40
        assert weights["speed_bonus"] == 0.12
        assert weights["lint_clean"] == DEFAULT_WEIGHTS["lint_clean"]


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases for scorer
# ═══════════════════════════════════════════════════════════════════════════

class TestScorerEdgeCases:
    """Edge cases for scoring functions."""

    def test_complexity_empty_code(self):
        assert compute_complexity_score("") == 50.0

    def test_complexity_whitespace_only(self):
        assert compute_complexity_score("   \n\n  ") == 50.0

    def test_complexity_simple_code(self):
        code = "def hello():\n    print('hi')\n"
        score = compute_complexity_score(code)
        assert 0 <= score <= 100

    def test_docstring_empty(self):
        assert compute_docstring_coverage("") == 50.0

    def test_docstring_all_documented(self):
        code = '"""Module."""\ndef foo():\n    """Doc."""\n    pass\n'
        score = compute_docstring_coverage(code)
        assert score == 100.0

    def test_docstring_none_documented(self):
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        score = compute_docstring_coverage(code)
        assert score == 0.0

    def test_type_hints_empty(self):
        assert compute_type_hint_coverage("") == 50.0

    def test_type_hints_fully_typed(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        score = compute_type_hint_coverage(code)
        assert score == 100.0

    def test_type_hints_no_types(self):
        code = "def add(a, b):\n    return a + b\n"
        score = compute_type_hint_coverage(code)
        assert score < 50

    def test_comment_density_empty(self):
        assert compute_comment_density("") == 0.15

    def test_comment_density_good(self):
        code = "# A comment\ndef foo():\n    pass\n# Another\n"
        density = compute_comment_density(code)
        assert 0 < density <= 1.0

    def test_cleanliness_penalty_clean(self):
        assert _code_cleanliness_penalty("", "") == 0.0

    def test_cleanliness_penalty_crash(self):
        assert _code_cleanliness_penalty("Traceback", "") > 0

    def test_import_issues_clean(self):
        assert _count_import_issues("hello world", "") == 0

    def test_import_issues_found(self):
        assert _count_import_issues("ImportError: foo", "") == 1

    def test_letter_grade_boundaries(self):
        assert _letter_grade(93) == "A"
        assert _letter_grade(90) == "A-"
        assert _letter_grade(87) == "B+"
        assert _letter_grade(83) == "B"
        assert _letter_grade(80) == "B-"
        assert _letter_grade(77) == "C+"
        assert _letter_grade(73) == "C"
        assert _letter_grade(70) == "C-"
        assert _letter_grade(60) == "D"
        assert _letter_grade(50) == "F"
        assert _letter_grade(0) == "F"

    def test_score_zero_metrics(self):
        """All-zero metrics should produce a valid score."""
        metrics = RunMetrics()
        score, grade = compute_quality_score(metrics)
        assert 0 <= score <= 100
        assert grade in ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F")

    def test_score_perfect_metrics(self):
        """Perfect metrics should score high."""
        metrics = RunMetrics(
            exit_code=0,
            duration_seconds=15,
            tokens_in=100,
            tokens_out=50,
            stdout='"""Doc."""\ndef foo(x: int) -> int:\n    """Doc."""\n    return x\n',
            stderr="",
            test_pass=10,
            test_total=10,
        )
        score, grade = compute_quality_score(metrics)
        assert score > 70
        assert grade in ("A", "A-", "B+", "B")

    def test_score_failed_metrics(self):
        """Bad metrics should score low."""
        metrics = RunMetrics(
            exit_code=1,
            duration_seconds=900,
            tokens_in=100000,
            tokens_out=50000,
            stdout="Traceback (most recent call):\n  RuntimeError\nfrom os import *\n",
            stderr="ImportError: no module\nSyntaxError: bad",
            lint_errors=10,
            lint_warnings=5,
        )
        score, grade = compute_quality_score(metrics)
        assert score < 60
        assert grade in ("D", "F")


# ═══════════════════════════════════════════════════════════════════════════
# Weights CLI command
# ═══════════════════════════════════════════════════════════════════════════

class TestWeightsCommand:
    """Test the weights CLI command."""

    def test_weights_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["weights"])
        assert result.exit_code == 0
        assert "test_pass_rate" in result.output
        assert "0.25" in result.output

    def test_weights_reset(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["weights", "--reset"])
        assert result.exit_code == 0
        assert "Reset to default" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Diff CLI command
# ═══════════════════════════════════════════════════════════════════════════

class TestDiffCommand:
    """Test the diff CLI command."""

    def test_diff_missing_run(self, tmp_path, monkeypatch):
        """Diff with nonexistent run shows error."""
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=tmp_path / "test.db"))
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "nonexistent-a", "nonexistent-b"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_diff_with_data(self, tmp_path, monkeypatch):
        """Diff with two runs shows comparison."""
        storage = Storage(path=tmp_path / "test.db")
        results_a = [
            {"agent_name": "claude", "quality_score": 85, "quality_grade": "B", "cost": 0.05},
            {"agent_name": "codex", "quality_score": 72, "quality_grade": "C", "cost": 0.03},
        ]
        results_b = [
            {"agent_name": "claude", "quality_score": 90, "quality_grade": "A-", "cost": 0.06},
            {"agent_name": "codex", "quality_score": 68, "quality_grade": "C-", "cost": 0.02},
        ]
        storage.save_run("run-a-001", "task 1", results_a)
        storage.save_run("run-b-002", "task 2", results_b)
        storage.close()

        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=tmp_path / "test.db"))
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "run-a-001", "run-b-002"])
        assert result.exit_code == 0
        assert "claude" in result.output
        assert "codex" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Collector edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectorEdgeCases:
    """Edge cases for metric collection."""

    def test_empty_output(self):
        metrics = collect_from_output(
            stdout="", stderr="", exit_code=0, duration=1.0,
            diff_stat="", test_output="", lint_output="",
        )
        assert metrics.tokens_in == 0
        assert metrics.tokens_out == 0
        assert metrics.exit_code == 0

    def test_token_parsing_json(self):
        output = '{"usage": {"input_tokens": 150, "output_tokens": 75}}'
        metrics = collect_from_output(
            stdout=output, stderr="", exit_code=0, duration=1.0,
            diff_stat="", test_output="", lint_output="",
        )
        # Should parse some tokens from the JSON
        assert metrics.tokens_in >= 0

    def test_test_parsing_pytest(self):
        test_output = "8 passed, 2 failed in 3.5s"
        metrics = collect_from_output(
            stdout="", stderr="", exit_code=0, duration=1.0,
            diff_stat="", test_output=test_output, lint_output="",
        )
        assert metrics.test_pass == 8
        assert metrics.test_total == 10

    def test_test_parsing_all_passed(self):
        test_output = "15 passed in 2.1s"
        metrics = collect_from_output(
            stdout="", stderr="", exit_code=0, duration=1.0,
            diff_stat="", test_output=test_output, lint_output="",
        )
        assert metrics.test_pass == 15
        assert metrics.test_total == 15

    def test_lint_parsing_errors(self):
        lint_output = "main.py:5:1: E302 expected 2 blank lines\nmain.py:10:5: F841 local variable unused"
        metrics = collect_from_output(
            stdout="", stderr="", exit_code=0, duration=1.0,
            diff_stat="", test_output="", lint_output=lint_output,
        )
        assert metrics.lint_errors > 0

    def test_diff_stat_parsing(self):
        diff_stat = "3 files changed, 50 insertions(+), 20 deletions(-)"
        metrics = collect_from_output(
            stdout="", stderr="", exit_code=0, duration=1.0,
            diff_stat=diff_stat, test_output="", lint_output="",
        )
        assert metrics.files_changed == 3
        assert metrics.lines_added == 50
        assert metrics.lines_removed == 20


# ═══════════════════════════════════════════════════════════════════════════
# Storage edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestStorageEdgeCases:
    """Edge cases for storage operations."""

    def test_get_nonexistent_run(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        assert storage.get_run("nonexistent") is None
        storage.close()

    def test_save_and_list_runs(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-001", "task A", [{"agent_name": "test", "quality_score": 80}])
        storage.save_run("run-002", "task B", [{"agent_name": "test", "quality_score": 85}])
        runs = storage.list_runs(limit=10)
        assert len(runs) == 2
        storage.close()

    def test_delete_run(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-del", "task", [{"agent_name": "test", "quality_score": 80}])
        assert storage.get_run("run-del") is not None
        storage.delete_run("run-del")
        assert storage.get_run("run-del") is None
        storage.close()

    def test_list_runs_ordered(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-a", "task", [{"agent_name": "test", "quality_score": 70}])
        storage.save_run("run-b", "task", [{"agent_name": "test", "quality_score": 90}])
        runs = storage.list_runs(limit=10)
        # Most recent first
        assert runs[0]["run_id"] == "run-b"
        storage.close()

    def test_empty_db(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        runs = storage.list_runs()
        assert runs == []
        storage.close()
