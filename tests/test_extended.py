"""Extended tests for web_reporter, edge cases, and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.collector import RunMetrics, parse_tokens, parse_test_results, parse_lint_results, collect_from_output
from agent_bench.scorer import compute_quality_score, _letter_grade, compute_complexity_score
from agent_bench.web_reporter import generate_html, _bar_svg
from agent_bench.storage import Storage


# ── Web Reporter Tests ──

def _sample_run():
    return {
        "run_id": "test-001",
        "task": "Add pagination",
        "timestamp": "2026-04-07T00:15:00",
        "results": [
            {"agent_name": "Claude", "duration_seconds": 134, "cost": 0.42, "tokens_in": 18200,
             "tokens_out": 8100, "test_pass": 8, "test_total": 8, "quality_score": 92, "quality_grade": "A"},
            {"agent_name": "Codex", "duration_seconds": 107, "cost": 0.31, "tokens_in": 14100,
             "tokens_out": 6200, "test_pass": 8, "test_total": 8, "quality_score": 88, "quality_grade": "A-"},
        ],
    }


class TestWebReporter:
    def test_basic_html(self):
        html = generate_html(_sample_run())
        assert "<!DOCTYPE html>" in html
        assert "Claude" in html
        assert "Codex" in html
        assert "Add pagination" in html

    def test_empty_results(self):
        html = generate_html({"task": "test", "results": []})
        assert "No results" in html

    def test_single_agent(self):
        data = {"run_id": "r1", "task": "t", "timestamp": "", "results": [
            {"agent_name": "Solo", "duration_seconds": 10, "cost": 0.1, "tokens_in": 100,
             "tokens_out": 50, "test_pass": 5, "test_total": 5, "quality_score": 95, "quality_grade": "A"}
        ]}
        html = generate_html(data)
        assert "Solo" in html
        assert "Winner" in html

    def test_many_agents(self):
        results = []
        for i in range(20):
            results.append({
                "agent_name": f"Agent-{i}", "duration_seconds": 10 + i, "cost": 0.1 + i * 0.01,
                "tokens_in": 100, "tokens_out": 50, "test_pass": 5, "test_total": 5,
                "quality_score": 90 - i, "quality_grade": "A"
            })
        html = generate_html({"run_id": "r", "task": "t", "timestamp": "", "results": results})
        assert "Agent-0" in html
        assert "Agent-19" in html

    def test_html_escaping(self):
        data = {"run_id": "r", "task": "<script>alert('xss')</script>", "timestamp": "", "results": [
            {"agent_name": "A&B", "duration_seconds": 10, "cost": 0.1, "tokens_in": 100,
             "tokens_out": 50, "test_pass": 0, "test_total": 0, "quality_score": 50, "quality_grade": "C"}
        ]}
        html = generate_html(data)
        assert "<script>" not in html
        assert "&amp;" in html or "A&amp;B" in html

    def test_comparison_section(self):
        baseline = {"run_id": "base", "task": "t", "timestamp": "", "results": [
            {"agent_name": "Claude", "quality_score": 80, "quality_grade": "B", "cost": 0.5}
        ]}
        html = generate_html(_sample_run(), comparison_data=baseline)
        assert "Comparison" in html
        assert "Delta" in html

    def test_bar_svg(self):
        svg = _bar_svg(50, 100)
        assert "<svg" in svg
        assert "50.0</text>" in svg

    def test_bar_svg_zero_max(self):
        svg = _bar_svg(0, 0)
        assert "<svg" in svg


# ── Scorer Edge Cases ──

class TestScorerEdgeCases:
    def _make_metrics(self, **kwargs) -> RunMetrics:
        defaults = dict(
            exit_code=0, duration_seconds=60, tokens_in=1000, tokens_out=500,
            files_changed=2, lines_added=20, lines_removed=5,
            test_pass=8, test_total=8, lint_errors=0, lint_warnings=0,
        )
        defaults.update(kwargs)
        return RunMetrics(**defaults)

    def test_zero_duration(self):
        m = self._make_metrics(duration_seconds=0)
        score, _ = compute_quality_score(m)
        assert score >= 90  # Should get max speed bonus

    def test_all_tests_passing(self):
        m = self._make_metrics(test_pass=100, test_total=100)
        score, grade = compute_quality_score(m)
        assert score >= 90

    def test_all_tests_failing(self):
        m = self._make_metrics(test_pass=0, test_total=10)
        score, grade = compute_quality_score(m)
        assert score < 80
        assert grade in ("C", "C-", "D", "F")

    def test_very_high_complexity(self):
        # Lots of import issues to drive score down
        m = self._make_metrics(stdout="ImportError ImportError ImportError ImportError ImportError ImportError")
        score, _ = compute_quality_score(m)
        assert score < 95

    def test_very_high_duration(self):
        m = self._make_metrics(duration_seconds=99999)
        score, _ = compute_quality_score(m)
        assert score < 95

    def test_negative_exit_code(self):
        m = self._make_metrics(exit_code=-1)
        score, _ = compute_quality_score(m)
        assert score < 90

    def test_many_lint_errors(self):
        m = self._make_metrics(lint_errors=50)
        score, _ = compute_quality_score(m)
        assert score < 85  # 50 lint errors maxes out penalty at 14 points but floor is 0

    def test_complexity_empty_code(self):
        score = compute_complexity_score("")
        assert score == 50.0

    def test_complexity_simple_code(self):
        code = "x = 1\ny = 2\n"
        score = compute_complexity_score(code)
        assert 0 <= score <= 100

    def test_letter_grade_all_boundaries(self):
        assert _letter_grade(100) == "A"
        assert _letter_grade(93) == "A"
        assert _letter_grade(92.9) == "A-"
        assert _letter_grade(0) == "F"
        assert _letter_grade(59.9) == "F"
        assert _letter_grade(60) == "D"


# ── Collector Edge Cases ──

class TestCollectorEdgeCases:
    def test_empty_output(self):
        m = collect_from_output("", "", 0, 0.0)
        assert m.tokens_in == 0
        assert m.tokens_out == 0

    def test_partial_token_match(self):
        # Only input, no output
        inp, out = parse_tokens("15000 input tokens here")
        assert inp == 0  # Should not match without output pair

    def test_mixed_format_tokens(self):
        inp, out = parse_tokens("Usage: 1,500 input, 2,300 output")
        assert inp == 1500
        assert out == 2300

    def test_zero_cost(self):
        m = collect_from_output("", "", 0, 0.0)
        assert m.cost == 0.0

    def test_parse_test_only_passed(self):
        p, t = parse_test_results("10 passed in 2.5s")
        assert p == 10
        assert t == 10

    def test_parse_test_passed_failed_error(self):
        p, t = parse_test_results("3 passed, 2 failed, 1 error")
        assert p == 3
        assert t == 6

    def test_parse_lint_empty(self):
        e, w = parse_lint_results("")
        assert e == 0
        assert w == 0


# ── Reporter Edge Cases ──

class TestReporterEdgeCases:
    def test_markdown_single_agent(self):
        from agent_bench.reporter import format_markdown
        data = {"run_id": "r1", "task": "test", "timestamp": "", "results": [
            {"agent_name": "Solo", "duration_seconds": 10, "cost": 0.1, "tokens_in": 100,
             "tokens_out": 50, "test_pass": 5, "test_total": 5, "quality_score": 95, "quality_grade": "A"}
        ]}
        md = format_markdown(data)
        assert "Solo" in md
        assert "| Agent |" in md

    def test_markdown_escaping(self):
        from agent_bench.reporter import format_markdown
        # Markdown with pipe characters in agent name
        data = {"run_id": "r1", "task": "test|pipe", "timestamp": "", "results": [
            {"agent_name": "Agent|Name", "duration_seconds": 10, "cost": 0.1, "tokens_in": 100,
             "tokens_out": 50, "test_pass": 0, "test_total": 0, "quality_score": 50, "quality_grade": "C"}
        ]}
        md = format_markdown(data)
        assert "Agent|Name" in md

    def test_baseline_markdown(self):
        from agent_bench.reporter import format_baseline_markdown
        current = {"run_id": "c1", "timestamp": "", "results": [
            {"agent_name": "A", "quality_score": 90, "quality_grade": "A", "cost": 0.5}
        ]}
        baseline = {"run_id": "b1", "timestamp": "", "results": [
            {"agent_name": "A", "quality_score": 80, "quality_grade": "B", "cost": 0.3}
        ]}
        md = format_baseline_markdown(current, baseline)
        assert "+10" in md

    def test_baseline_table(self):
        from agent_bench.reporter import format_baseline_table
        current = {"run_id": "c1", "timestamp": "", "results": [
            {"agent_name": "A", "quality_score": 70, "quality_grade": "C", "cost": 0.5, "duration_seconds": 60}
        ]}
        baseline = {"run_id": "b1", "timestamp": "", "results": [
            {"agent_name": "A", "quality_score": 80, "quality_grade": "B", "cost": 0.3, "duration_seconds": 30}
        ]}
        output = format_baseline_table(current, baseline)
        assert "Current vs Baseline" in output


# ── Storage Edge Cases ──

class TestStorageEdgeCases:
    def test_corrupt_db(self, tmp_path):
        db_path = tmp_path / "corrupt.db"
        db_path.write_text("not a database")
        # Remove corrupt file and re-init
        db_path.unlink()
        s = Storage(path=db_path)
        s.save_run("r1", "task", [self._sample_result()])
        assert s.get_run("r1") is not None
        s.close()

    def test_very_large_result_set(self, tmp_path):
        s = Storage(path=tmp_path / "big.db")
        results = [self._sample_result(f"agent-{i}") for i in range(100)]
        s.save_run("big-run", "big task", results)
        run = s.get_run("big-run")
        assert run is not None
        assert len(run["results"]) == 100
        s.close()

    def test_concurrent_writes(self, tmp_path):
        import threading
        errors = []

        def write_run(idx):
            try:
                s = Storage(path=tmp_path / "concurrent.db")
                s.save_run(f"run-{idx}", f"task {idx}", [self._sample_result(f"agent-{idx}")])
                s.close()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_run, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        s = Storage(path=tmp_path / "concurrent.db")
        assert len(s.list_runs(limit=20)) == 10
        s.close()

    def _sample_result(self, name="test-agent", **kwargs):
        defaults = dict(
            agent_name=name, exit_code=0, duration_seconds=60.0,
            tokens_in=1000, tokens_out=500, cost=0.05,
            files_changed=3, lines_added=20, lines_removed=5,
            test_pass=8, test_total=8, lint_errors=0, lint_warnings=0,
            quality_score=92.0, quality_grade="A", stdout="", stderr="",
        )
        defaults.update(kwargs)
        return defaults


# ── CLI Tests ──

@pytest.fixture
def runner():
    return CliRunner()


class TestCLIReport:
    @patch("agent_bench.cli.Storage")
    def test_report_no_results(self, mock_cls, runner):
        mock = MagicMock()
        mock.get_latest_run.return_value = None
        mock_cls.return_value = mock
        result = runner.invoke(cli, ["report"])
        assert "No results" in result.output

    @patch("agent_bench.cli.Storage")
    def test_report_html_to_file(self, mock_cls, runner, tmp_path):
        mock = MagicMock()
        mock.get_latest_run.return_value = _sample_run()
        mock_cls.return_value = mock
        output_file = str(tmp_path / "report.html")
        result = runner.invoke(cli, ["report", "--html", "-o", output_file])
        assert result.exit_code == 0
        assert Path(output_file).exists()
        content = Path(output_file).read_text()
        assert "Claude" in content

    @patch("agent_bench.cli.Storage")
    def test_results_html_flag(self, mock_cls, runner):
        mock = MagicMock()
        mock.get_latest_run.return_value = _sample_run()
        mock_cls.return_value = mock
        result = runner.invoke(cli, ["results", "--html"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output


class TestCLIVersion:
    def test_version_bumped(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert "0.2.0" in result.output
