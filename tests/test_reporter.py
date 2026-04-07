"""Tests for reporter module."""

from agent_bench.reporter import format_table, format_json, format_history, _format_duration, _format_tokens, _test_status


def _sample_run():
    return {
        "run_id": "test-001",
        "task": "Add pagination",
        "timestamp": "2026-04-07T00:15:00",
        "results": [
            {"agent_name": "Claude", "duration_seconds": 134, "cost": 0.42, "tokens_in": 18200, "tokens_out": 8100, "test_pass": 8, "test_total": 8, "quality_score": 92, "quality_grade": "A"},
            {"agent_name": "Codex", "duration_seconds": 107, "cost": 0.31, "tokens_in": 14100, "tokens_out": 6200, "test_pass": 8, "test_total": 8, "quality_score": 88, "quality_grade": "A-"},
        ],
    }


class TestFormatDuration:
    def test_seconds(self):
        assert _format_duration(45) == "45s"

    def test_minutes(self):
        assert _format_duration(134) == "2m 14s"

    def test_zero(self):
        assert _format_duration(0) == "0s"


class TestFormatTokens:
    def test_thousands(self):
        assert _format_tokens(18200) == "18.2K"

    def test_millions(self):
        assert _format_tokens(1_500_000) == "1.5M"

    def test_small(self):
        assert _format_tokens(500) == "500"


class TestTestStatus:
    def test_all_pass(self):
        assert "✅" in _test_status(8, 8)

    def test_partial(self):
        assert "⚠️" in _test_status(5, 8)

    def test_fail(self):
        assert "❌" in _test_status(2, 8)

    def test_no_tests(self):
        assert _test_status(0, 0) == "—"


class TestFormatTable:
    def test_basic_output(self):
        output = format_table(_sample_run())
        assert "Claude" in output
        assert "Codex" in output
        assert "Add pagination" in output

    def test_empty_results(self):
        output = format_table({"task": "test", "results": []})
        assert "No results" in output

    def test_winner_shown(self):
        output = format_table(_sample_run())
        assert "Winner" in output
        assert "Fastest" in output
        assert "Cheapest" in output


class TestFormatJson:
    def test_valid_json(self):
        data = _sample_run()
        output = format_json(data)
        import json
        parsed = json.loads(output)
        assert parsed["task"] == "Add pagination"


class TestFormatHistory:
    def test_with_runs(self):
        runs = [{"run_id": "r1", "timestamp": "2026-04-07", "task": "test"}]
        output = format_history(runs)
        assert "r1" in output

    def test_empty(self):
        output = format_history([])
        assert "No benchmark" in output

    def test_long_task_truncated(self):
        runs = [{"run_id": "r1", "timestamp": "2026-04-07", "task": "a" * 50}]
        output = format_history(runs)
        assert "..." in output
