"""Tests for v0.8.0 features: top command, cost-report, export-ranks, expanded pricing."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.storage import Storage
from agent_bench.pricing import get_pricing, estimate_cost, DEFAULT_PRICING, AGENT_DEFAULT_MODEL


def _seed_runs(storage: Storage) -> None:
    """Insert sample benchmark runs."""
    storage.save_run(
        run_id="run-001",
        task="sort an array",
        results=[
            {
                "agent_name": "claude-code",
                "quality_score": 92,
                "quality_grade": "A",
                "cost": 0.15,
                "duration_seconds": 45,
                "tokens_in": 5000,
                "tokens_out": 2000,
                "model": "claude-sonnet-4",
            },
            {
                "agent_name": "codex-cli",
                "quality_score": 85,
                "quality_grade": "B+",
                "cost": 0.08,
                "duration_seconds": 30,
                "tokens_in": 3000,
                "tokens_out": 1500,
                "model": "gpt-5.2-codex",
            },
        ],
    )
    storage.save_run(
        run_id="run-002",
        task="implement binary search",
        results=[
            {
                "agent_name": "gemini-cli",
                "quality_score": 88,
                "quality_grade": "A-",
                "cost": 0.03,
                "duration_seconds": 20,
                "tokens_in": 2000,
                "tokens_out": 1000,
                "model": "gemini-2.5-flash",
            },
            {
                "agent_name": "openclaw",
                "quality_score": 78,
                "quality_grade": "B",
                "cost": 0.01,
                "duration_seconds": 15,
                "tokens_in": 1500,
                "tokens_out": 800,
                "model": "glm-5",
            },
        ],
    )


class TestTopCommand:
    """Test the 'top' command."""

    def test_top_basic(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["top", "-n", "3"])
        assert result.exit_code == 0
        assert "claude-code" in result.output
        assert "92" in result.output

    def test_top_json(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["top", "--json", "-n", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["score"] >= data[1]["score"]

    def test_top_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))

        runner = CliRunner()
        result = runner.invoke(cli, ["top"])
        assert result.exit_code == 0
        assert "No benchmark runs" in result.output


class TestCostReport:
    """Test the 'cost-report' command."""

    def test_cost_report_basic(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["cost-report"])
        assert result.exit_code == 0
        assert "Total Cost" in result.output
        assert "claude-code" in result.output

    def test_cost_report_json(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["cost-report", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_cost" in data
        assert "by_agent" in data
        assert "by_model" in data
        assert data["total_runs"] == 4

    def test_cost_report_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))

        runner = CliRunner()
        result = runner.invoke(cli, ["cost-report"])
        assert result.exit_code == 0
        assert "No benchmark runs" in result.output


class TestExportRanks:
    """Test the 'export-ranks' command."""

    def test_export_json(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["export-ranks", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 4
        assert data[0]["quality_score"] >= data[-1]["quality_score"]

    def test_export_csv(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["export-ranks", "--format", "csv"])
        assert result.exit_code == 0
        assert "agent" in result.output
        assert "claude-code" in result.output

    def test_export_markdown(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["export-ranks", "--format", "markdown"])
        assert result.exit_code == 0
        assert "| 1 |" in result.output
        assert "claude-code" in result.output

    def test_export_to_file(self, tmp_path, monkeypatch):
        db_path = tmp_path / "bench.sqlite"
        out_path = str(tmp_path / "ranks.json")
        monkeypatch.setattr("agent_bench.cli.Storage", lambda **kw: Storage(path=db_path))
        storage = Storage(path=db_path)
        _seed_runs(storage)
        storage.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["export-ranks", "--format", "json", "-o", out_path])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert Path(out_path).exists()
        data = json.loads(Path(out_path).read_text())
        assert len(data) == 4


class TestExpandedPricing:
    """Test expanded model pricing data."""

    def test_new_anthropic_models(self):
        for model in ["claude-sonnet-4.5", "claude-opus-4.7", "claude-sonnet-5", "claude-haiku-5"]:
            p = get_pricing(model)
            assert p.input > 0
            assert p.output > 0

    def test_new_openai_models(self):
        for model in ["gpt-5.5", "gpt-5.5-instant", "gpt-6.5", "gpt-6.5-turbo"]:
            p = get_pricing(model)
            assert p.input > 0

    def test_new_google_models(self):
        for model in ["gemini-5.0-pro", "gemini-5.0-flash", "gemini-3.1-flash-lite"]:
            p = get_pricing(model)
            assert p.input > 0

    def test_new_xai_models(self):
        for model in ["grok-4.3", "grok-5", "grok-5-mini"]:
            p = get_pricing(model)
            assert p.input > 0

    def test_new_deepseek_models(self):
        for model in ["deepseek-v5", "deepseek-v5.5", "deepseek-r5"]:
            p = get_pricing(model)
            assert p.input > 0

    def test_new_providers(self):
        for model in ["subq-1m-preview", "zaya-1-8b", "cursor-pro", "phi-4"]:
            p = get_pricing(model)
            assert p.input > 0

    def test_new_agents_in_defaults(self):
        assert "kiro" in AGENT_DEFAULT_MODEL
        assert "nemoclaw" in AGENT_DEFAULT_MODEL
        assert "cursor" in AGENT_DEFAULT_MODEL

    def test_cost_calculation_new_models(self):
        cost = estimate_cost("kiro", 10000, 5000)
        assert cost > 0

        cost = estimate_cost("cursor", 10000, 5000)
        assert cost > 0

    def test_pricing_count_expanded(self):
        assert len(DEFAULT_PRICING) >= 80


class TestFmtDur:
    """Test the _fmt_dur helper."""

    def test_seconds(self):
        from agent_bench.cli import _fmt_dur
        assert _fmt_dur(30) == "30s"
        assert _fmt_dur(59) == "59s"

    def test_minutes(self):
        from agent_bench.cli import _fmt_dur
        assert _fmt_dur(90) == "1m 30s"
        assert _fmt_dur(3599) == "59m 59s"

    def test_hours(self):
        from agent_bench.cli import _fmt_dur
        assert _fmt_dur(3661) == "1h 1m"
        assert _fmt_dur(7325) == "2h 2m"
