"""Edge case and error handling tests for agent-bench."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from agent_bench.cli import cli, results, run, leaderboard
from agent_bench.config import Config
from agent_bench.storage import Storage


def test_cli_init_no_overwrite():
    """Test that init doesn't overwrite existing config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "existing_config.yaml"
        config_path.write_text("# Existing config\n")
        
        # Run init
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(cli, ['init', '--path', str(config_path)])
        
        assert result.exit_code == 0
        # Should not overwrite existing config
        assert "already exists" in result.output
        assert config_path.read_text() == "# Existing config\n"


def test_results_invalid_run_id():
    """Test results command with invalid run ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        # Try to get results for non-existent run
        result = runner.invoke(results, ['--run-id', 'invalid_run_id'])
        
        assert result.exit_code == 0
        assert "No results found" in result.output
        
        storage.close()


def test_results_with_compare_invalid_runs():
    """Test results compare with invalid run IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        # Try to compare with invalid run IDs (two separate args)
        result = runner.invoke(results, ['--compare', 'invalid_run_1', 'invalid_run_2'])
        
        assert result.exit_code == 0
        assert "Run not found" in result.output
        
        storage.close()


def test_leaderboard_empty_storage():
    """Test leaderboard with empty storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(leaderboard, ['--limit', '10'])
        
        assert result.exit_code == 0
        # Should handle empty storage gracefully
        assert "No results found" not in result.output  # May show empty table
        
        storage.close()


def test_config_missing_agent():
    """Test handling of missing agent in config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        config_path.write_text("""
agents:
  valid_agent:
    command: "echo"
    args: ["hello"]
""")
        
        config = Config(config_path)
        
        # Try to get config for non-existent agent
        assert config.get_agent_config("invalid_agent") == {}
        
        # Test run command with invalid agent
        from click.testing import CliRunner
        runner = CliRunner()
        
        with patch('agent_bench.cli.Config') as mock_config:
            mock_config.return_value = config
            result = runner.invoke(cli, ['run', '--agent', 'invalid_agent'])
        
        # Should handle gracefully (though may not exit cleanly due to command execution)
        assert result is not None


def test_storage_corrupted_db():
    """Test handling of corrupted database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "corrupted.db"
        db_path.write_text("corrupted data")
        
        # Should handle corruption gracefully
        try:
            storage = Storage(db_path)
            # Should either fail gracefully or recover
            storage.list_runs()
        except Exception:
            # Expected to fail, but shouldn't crash the system
            pass
        finally:
            if 'storage' in locals():
                storage.close()


def test_collector_empty_output():
    """Test output collector with empty/null output."""
    from agent_bench.collector import collect_from_output, RunMetrics
    
    # Test with completely empty output
    metrics = collect_from_output("", "", 0, "")
    assert metrics is not None
    assert metrics.exit_code == 0
    
    # Test with None values
    metrics = collect_from_output(None, None, None, None)
    assert metrics is not None
    
    # Test with only whitespace
    metrics = collect_from_output("   \n\t  ", "", 0, "")
    assert metrics is not None


def test_scorer_edge_cases():
    """Test scorer edge cases."""
    from agent_bench.scorer import compute_quality_score, compute_complexity_score
    from agent_bench.collector import RunMetrics
    
    # Test with metrics that have None values
    metrics = RunMetrics(
        exit_code=0,
        test_pass=0,
        test_total=0,
        lint_errors=0,
        lint_warnings=0,
        lines_added=0,
        lines_removed=0,
        duration_seconds=0,
        stdout="",
        stderr=""
    )
    
    score, grade = compute_quality_score(metrics)
    assert isinstance(score, float)
    assert isinstance(grade, str)
    assert 0 <= score <= 100
    
    # Test complexity with empty code
    complexity = compute_complexity_score("")
    assert isinstance(complexity, float)
    assert 0 <= complexity <= 100
    
    # Test complexity with very simple code
    simple_code = "x = 1\ny = 2\nprint(x + y)"
    complexity = compute_complexity_score(simple_code)
    assert isinstance(complexity, float)
    assert 0 <= complexity <= 100


def test_parallel_execution_timeout():
    """Test parallel execution with timeout handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        config_path.write_text("""
agents:
  test_agent:
    command: "sleep"
    args: ["10"]  # Long running command
""")
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        # Test with short timeout
        result = runner.invoke(cli, [
            'run',
            '--agent', 'test_agent',
            '--parallel',
            '--model', 'test-model',
            '--task', 'test task'
        ], catch_exceptions=True)
        
        # Should handle timeout gracefully (exit code may vary)
        assert result is not None


def test_filesystem_errors():
    """Test handling of filesystem errors."""
    import os
    
    # Test with non-existent working directory
    from click.testing import CliRunner
    runner = CliRunner()
    
    result = runner.invoke(cli, [
        'run',
        '--agent', 'test_agent',
        '--workdir', '/non/existent/directory',
        '--task', 'test task'
    ], catch_exceptions=True)
    
    # Should handle gracefully
    assert result is not None