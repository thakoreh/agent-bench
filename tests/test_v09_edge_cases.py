"""Tests for v0.9.0: edge cases for CLI commands, storage, and scorer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.storage import Storage
from agent_bench.scorer import (
    compute_quality_score,
    compute_complexity_score,
    compute_docstring_coverage,
    compute_type_hint_coverage,
    compute_comment_density,
    _count_import_issues,
    _count_unused_imports,
    _code_cleanliness_penalty,
    _letter_grade,
    compute_quality_score_weighted,
    get_scoring_weights,
)
from agent_bench.collector import RunMetrics
from agent_bench.pricing import get_pricing, estimate_cost


def _make_metrics(**overrides) -> RunMetrics:
    """Create a RunMetrics with sensible defaults."""
    defaults = dict(
        exit_code=0,
        duration_seconds=30.0,
        tokens_in=1000,
        tokens_out=500,
        cost=0.05,
        files_changed=3,
        lines_added=50,
        lines_removed=10,
        test_pass=10,
        test_total=10,
        lint_errors=0,
        lint_warnings=0,
        stdout="def hello():\n    pass\n",
        stderr="",
    )
    defaults.update(overrides)
    return RunMetrics(**defaults)


# ── Storage edge cases ────────────────────────────────────────────────────

class TestStorageEdgeCases:
    """Edge cases for storage operations."""

    def test_get_nonexistent_run(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        assert s.get_run("nonexistent") is None
        s.close()

    def test_delete_nonexistent_run(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        assert s.delete_run("nonexistent") is False
        s.close()

    def test_get_latest_run_empty(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        assert s.get_latest_run() is None
        s.close()

    def test_empty_results_run(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        s.save_run("run-empty", "test task", [])
        data = s.get_run("run-empty")
        assert data is not None
        assert data["results"] == []
        s.close()

    def test_special_chars_in_task(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        task = "Fix bug #123: handle 'quotes' & \"doubles\" <tags>"
        s.save_run("run-special", task, [])
        data = s.get_run("run-special")
        assert data is not None
        assert data["task"] == task
        s.close()

    def test_concurrent_runs(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        for i in range(10):
            s.save_run(f"run-{i:03d}", f"task {i}", [
                {"agent_name": f"agent-{i}", "quality_score": 50 + i * 5, "model": "test"}
            ])
        runs = s.list_runs(limit=5)
        assert len(runs) == 5
        total = s.get_run_count()
        assert total == 10
        s.close()

    def test_agent_stats_no_runs(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        stats = s.get_agent_stats("nonexistent-agent")
        assert stats["run_count"] == 0
        s.close()

    def test_list_runs_default_limit(self, tmp_path):
        s = Storage(path=tmp_path / "test.db")
        for i in range(25):
            s.save_run(f"run-lst-{i:03d}", f"task {i}", [])
        runs = s.list_runs()
        assert len(runs) == 20  # default limit
        s.close()


# ── Scorer edge cases ─────────────────────────────────────────────────────

class TestScorerEdgeCases:
    """Edge cases for scoring calculations."""

    def test_perfect_score(self):
        m = _make_metrics(
            exit_code=0, duration_seconds=10, test_pass=10, test_total=10,
            lint_errors=0, lint_warnings=0, lines_added=30, lines_removed=10,
            stdout='def hello(name: str) -> str:\n    """Greet."""\n    return f"Hello {name}"\n',
        )
        score, grade = compute_quality_score(m)
        assert score >= 80, f"Expected >=80, got {score}"
        assert grade in ("A", "A-", "B+", "B")

    def test_zero_tests(self):
        m = _make_metrics(test_pass=0, test_total=0)
        score, grade = compute_quality_score(m)
        assert score > 0  # should get neutral points

    def test_all_failures(self):
        m = _make_metrics(exit_code=1, test_pass=0, test_total=10, lint_errors=20, duration_seconds=999)
        score, grade = compute_quality_score(m)
        assert score < 50
        assert grade in ("D", "F")

    def test_complexity_empty_code(self):
        assert compute_complexity_score("") == 50.0

    def test_complexity_syntax_error(self):
        assert compute_complexity_score("def ( broken {") == 50.0

    def test_complexity_simple_code(self):
        code = "def add(a, b):\n    return a + b\n"
        score = compute_complexity_score(code)
        assert score >= 50  # radon may not be installed, neutral default

    def test_docstring_empty(self):
        assert compute_docstring_coverage("") == 50.0

    def test_docstring_syntax_error(self):
        assert compute_docstring_coverage("def (") == 50.0

    def test_docstring_fully_documented(self):
        code = '"""Module."""\n\ndef foo():\n    """Doc."""\n    pass\n'
        score = compute_docstring_coverage(code)
        assert score == 100.0

    def test_type_hints_empty(self):
        assert compute_type_hint_coverage("") == 50.0

    def test_type_hints_fully_annotated(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        score = compute_type_hint_coverage(code)
        assert score == 100.0

    def test_type_hints_no_annotations(self):
        code = "def add(a, b):\n    return a + b\n"
        score = compute_type_hint_coverage(code)
        assert score < 50

    def test_comment_density_empty(self):
        assert compute_comment_density("") == 0.15

    def test_comment_density_ideal(self):
        code = "# header\ndef foo():\n    x = 1\n    y = 2\n    return x + y\n# end\n"
        density = compute_comment_density(code)
        assert density > 0  # any comments detected

    def test_import_issues_none(self):
        assert _count_import_issues("", "") == 0

    def test_import_issues_detected(self):
        out = "ImportError: no module\nfrom os import *\n"
        assert _count_import_issues(out, "") == 2

    def test_unused_imports(self):
        # "F401" matches and "unused import" also matches = 2 total
        assert _count_unused_imports("F401 unused import") >= 1

    def test_cleanliness_clean(self):
        assert _code_cleanliness_penalty("all good", "") == 0.0

    def test_cleanliness_crash(self):
        assert _code_cleanliness_penalty("Traceback", "RuntimeError") == 3.0

    def test_cleanliness_severe(self):
        out = "Traceback\nSyntaxError\nRuntimeError\nsegfault\ncore dumped"
        assert _code_cleanliness_penalty(out, "") == 5.0

    def test_letter_grades(self):
        assert _letter_grade(95) == "A"
        assert _letter_grade(91) == "A-"
        assert _letter_grade(88) == "B+"
        assert _letter_grade(85) == "B"
        assert _letter_grade(81) == "B-"
        assert _letter_grade(78) == "C+"
        assert _letter_grade(75) == "C"
        assert _letter_grade(71) == "C-"
        assert _letter_grade(65) == "D"
        assert _letter_grade(50) == "F"

    def test_weighted_score_defaults(self):
        m = _make_metrics()
        score, grade = compute_quality_score_weighted(m)
        assert 0 <= score <= 100

    def test_weighted_score_custom_weights(self):
        m = _make_metrics()
        weights = {"test_pass_rate": 1.0}
        score, grade = compute_quality_score_weighted(m, weights)
        # Only test pass rate matters, all others weight=0
        assert score == 100.0  # 10/10 tests pass * 100 * 1.0

    def test_get_scoring_weights_default(self):
        w = get_scoring_weights()
        assert "test_pass_rate" in w
        assert abs(sum(w.values()) - 1.0) < 0.01

    def test_get_scoring_weights_custom(self):
        config = {"scoring_weights": {"test_pass_rate": 0.5}}
        w = get_scoring_weights(config)
        assert w["test_pass_rate"] == 0.5
        # Others should still have defaults


# ── Pricing edge cases ────────────────────────────────────────────────────

class TestPricingEdgeCases:
    """Edge cases for pricing calculations."""



    def test_estimate_unknown_model(self):
        cost = estimate_cost("unknown-model-xyz", 1000, 500)
        assert cost == 0.0  # Unknown models have 0 pricing

    def test_get_known_model(self):
        p = get_pricing("gpt-4o")
        assert p.input > 0
        assert p.output > 0


# ── CLI edge cases ────────────────────────────────────────────────────────

class TestCLIEdgeCases:
    """Edge cases for CLI commands."""

    def test_history_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0

    def test_history_json_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["history", "--json"])
        assert result.exit_code == 0

    def test_results_nonexistent_run(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["results", "--run-id", "nonexistent"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "No results" in result.output

    def test_agents_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["agents"])
        assert result.exit_code == 0

    def test_delete_nonexistent(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["delete", "nonexistent", "--force"])
        assert result.exit_code == 0

    def test_trend_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["trend"])
        assert result.exit_code == 0
        assert "No benchmark runs" in result.output

    def test_weights_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["weights"])
        assert result.exit_code == 0
        assert "test_pass_rate" in result.output

    def test_weights_reset(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["weights", "--reset"])
        assert result.exit_code == 0

    def test_leaderboard_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["leaderboard"])
        assert result.exit_code == 0

    def test_compare_models_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["compare-models", "-a", "claude-code", "-m", "gpt-4o"])
        assert result.exit_code == 0

    def test_export_ranks_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["export-ranks"])
        assert result.exit_code == 0
        assert "No runs" in result.output
