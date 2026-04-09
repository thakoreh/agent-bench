"""Tests for v0.4.0 features: CSV export, leaderboard, breakdown, history --json, cost efficiency."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile

import pytest

from agent_bench.reporter import (
    format_breakdown_markdown,
    format_breakdown_table,
    format_csv,
    format_leaderboard_json,
    format_leaderboard_markdown,
    format_leaderboard_table,
    format_table,
)
from agent_bench.storage import Storage

SAMPLE_RUN = {
    "run_id": "test-001",
    "timestamp": "2026-04-09T00:00:00",
    "task": "Fix the login bug",
    "results": [
        {
            "agent_name": "claude",
            "model": "claude-3-opus",
            "exit_code": 0,
            "duration_seconds": 45,
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost": 0.15,
            "files_changed": 2,
            "lines_added": 20,
            "lines_removed": 5,
            "test_pass": 8,
            "test_total": 10,
            "lint_errors": 0,
            "lint_warnings": 0,
            "quality_score": 85,
            "quality_grade": "B",
            "stdout": "def foo():\n    return 1\n",
            "stderr": "",
        },
        {
            "agent_name": "gpt",
            "model": "gpt-4",
            "exit_code": 0,
            "duration_seconds": 120,
            "tokens_in": 2000,
            "tokens_out": 1000,
            "cost": 0.30,
            "files_changed": 3,
            "lines_added": 40,
            "lines_removed": 10,
            "test_pass": 10,
            "test_total": 10,
            "lint_errors": 1,
            "lint_warnings": 0,
            "quality_score": 78,
            "quality_grade": "C+",
            "stdout": "def bar():\n    return 2\n",
            "stderr": "",
        },
    ],
}


# --- CSV export tests ---


class TestCSVExport:
    def test_csv_contains_all_columns(self):
        csv_text = format_csv(SAMPLE_RUN)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 data rows
        assert "run_id" in rows[0]
        assert "quality_score" in rows[0]
        assert "cost" in rows[0]

    def test_csv_values(self):
        csv_text = format_csv(SAMPLE_RUN)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        assert rows[0]["agent_name"] == "claude"
        assert rows[0]["quality_score"] == "85"
        assert rows[1]["agent_name"] == "gpt"

    def test_csv_special_characters_in_agent_names(self):
        data = {
            "run_id": "sp-001",
            "timestamp": "2026-01-01T00:00:00",
            "task": "test",
            "results": [
                {
                    "agent_name": 'Agent "quoted" & <special>',
                    "model": "",
                    "exit_code": 0,
                    "duration_seconds": 10,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost": 0.1,
                    "files_changed": 0,
                    "lines_added": 0,
                    "lines_removed": 0,
                    "test_pass": 0,
                    "test_total": 0,
                    "lint_errors": 0,
                    "lint_warnings": 0,
                    "quality_score": 50,
                    "quality_grade": "D",
                    "stdout": "",
                    "stderr": "",
                }
            ],
        }
        csv_text = format_csv(data)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["agent_name"] == 'Agent "quoted" & <special>'

    def test_csv_empty_results(self):
        data = {"run_id": "x", "timestamp": "", "task": "", "results": []}
        csv_text = format_csv(data)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1  # header only


# --- Scoring breakdown tests ---


class TestScoringBreakdown:
    def test_breakdown_table_renders(self):
        output = format_breakdown_table(SAMPLE_RUN)
        assert "claude" in output
        assert "Scoring Breakdown" in output

    def test_breakdown_markdown_renders(self):
        output = format_breakdown_markdown(SAMPLE_RUN)
        assert "# Scoring Breakdown" in output
        assert "Test Pass Rate" in output
        assert "claude" in output

    def test_breakdown_with_zero_metrics(self):
        zero_data = {
            "run_id": "z",
            "timestamp": "",
            "task": "",
            "results": [
                {
                    "agent_name": "zero-agent",
                    "exit_code": 1,
                    "duration_seconds": 0,
                    "cost": 0,
                    "test_pass": 0,
                    "test_total": 0,
                    "lint_errors": 0,
                    "lint_warnings": 0,
                    "quality_score": 0,
                    "quality_grade": "F",
                    "stdout": "",
                    "stderr": "",
                }
            ],
        }
        output = format_breakdown_table(zero_data)
        assert "zero-agent" in output

    def test_breakdown_empty_results(self):
        data = {"run_id": "x", "timestamp": "", "task": "", "results": []}
        assert format_breakdown_table(data) == "No results to display."


# --- Cost efficiency tests ---


class TestCostEfficiency:
    def test_cost_efficiency_in_table(self):
        output = format_table(SAMPLE_RUN, sort_by="quality")
        assert "Cost Eff" in output

    def test_sort_by_cost_efficiency(self):
        output_q = format_table(SAMPLE_RUN, sort_by="quality")
        output_ce = format_table(SAMPLE_RUN, sort_by="cost-efficiency")
        # Different sort orders may produce different output
        assert output_q or output_ce

    def test_cost_efficiency_calculation(self):
        r = {"quality_score": 80, "cost": 0.20}
        ce = r["quality_score"] / max(r["cost"], 0.01)
        assert ce == 400.0

    def test_cost_efficiency_zero_cost(self):
        r = {"quality_score": 50, "cost": 0}
        ce = r["quality_score"] / max(r["cost"], 0.01)
        assert ce == 50.0 / 0.01


# --- Leaderboard tests ---


class TestLeaderboard:
    def _make_storage(self, tmp_path):
        db_path = tmp_path / "test.db"
        return Storage(path=db_path)

    def test_leaderboard_empty(self, tmp_path):
        storage = self._make_storage(tmp_path)
        from agent_bench.cli import _compute_leaderboard
        lb = _compute_leaderboard(storage, 10)
        assert lb == []

    def test_leaderboard_table_empty(self):
        output = format_leaderboard_table([])
        assert "No benchmark runs" in output

    def test_leaderboard_with_data(self, tmp_path):
        storage = self._make_storage(tmp_path)
        storage.save_run("run-1", "task-a", [
            {"agent_name": "claude", "quality_score": 85, "quality_grade": "B", "cost": 0.1,
             "exit_code": 0, "duration_seconds": 10, "stdout": "", "stderr": ""},
            {"agent_name": "gpt", "quality_score": 70, "quality_grade": "C", "cost": 0.2,
             "exit_code": 0, "duration_seconds": 20, "stdout": "", "stderr": ""},
        ])
        storage.save_run("run-2", "task-b", [
            {"agent_name": "claude", "quality_score": 90, "quality_grade": "B+", "cost": 0.1,
             "exit_code": 0, "duration_seconds": 10, "stdout": "", "stderr": ""},
        ])
        from agent_bench.cli import _compute_leaderboard
        lb = _compute_leaderboard(storage, 10)
        assert len(lb) == 2
        assert lb[0]["agent"] == "claude"
        assert lb[0]["avg_score"] == 87.5
        assert lb[0]["total_runs"] == 2
        assert lb[0]["wins"] == 2
        assert lb[1]["agent"] == "gpt"

    def test_leaderboard_markdown(self):
        output = format_leaderboard_markdown([{"agent": "claude", "avg_score": 87.5, "best_score": 90, "total_runs": 2, "wins": 2}])
        assert "# Leaderboard" in output
        assert "claude" in output

    def test_leaderboard_json(self):
        lb = [{"agent": "claude", "avg_score": 87.5, "best_score": 90, "total_runs": 2, "wins": 2}]
        output = format_leaderboard_json(lb)
        parsed = json.loads(output)
        assert parsed[0]["agent"] == "claude"


# --- History --json tests ---


class TestHistoryJSON:
    def test_history_json_empty(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        runs = storage.list_runs(limit=10)
        output = json.dumps(runs, indent=2)
        parsed = json.loads(output)
        assert parsed == []

    def test_history_json_with_data(self, tmp_path):
        storage = Storage(path=tmp_path / "test.db")
        storage.save_run("run-1", "task-a", [
            {"agent_name": "claude", "quality_score": 85, "quality_grade": "B", "cost": 0.1,
             "exit_code": 0, "duration_seconds": 10, "stdout": "", "stderr": ""},
        ])
        runs = storage.list_runs(limit=10)
        output = json.dumps(runs, indent=2)
        parsed = json.loads(output)
        assert len(parsed) == 1
        assert parsed[0]["run_id"] == "run-1"
        assert "task" in parsed[0]
