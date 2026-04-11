"""Tests for model comparison functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agent_bench.cli import compare_models
from agent_bench.storage import Storage


def test_compare_models_basic():
    """Test basic model comparison functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        # Add some test runs with different models
        run_id_1 = "run_1"
        storage.save_run(run_id_1, "test task", [
            {
                "agent_name": "codex",
                "model": "gpt-4",
                "quality_score": 85.0,
                "duration_seconds": 120,
                "exit_code": 0,
                "stdout": "test output",
                "stderr": ""
            },
            {
                "agent_name": "codex", 
                "model": "gpt-4o",
                "quality_score": 92.0,
                "duration_seconds": 90,
                "exit_code": 0,
                "stdout": "better output",
                "stderr": ""
            }
        ])
        
        run_id_2 = "run_2" 
        storage.save_run(run_id_2, "another task", [
            {
                "agent_name": "codex",
                "model": "gpt-4",
                "quality_score": 78.0,
                "duration_seconds": 150,
                "exit_code": 0,
                "stdout": "output 2",
                "stderr": ""
            }
        ])
        
        # Test model comparison
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(compare_models, [
            '--agent', 'codex',
            '--models', 'gpt-4,gpt-4o',
            '--limit', '2'
        ])
        
        assert result.exit_code == 0
        assert "gpt-4" in result.output
        assert "gpt-4o" in result.output
        assert "Model Comparison: codex" in result.output
        
        storage.close()


def test_compare_models_no_results():
    """Test model comparison with no matching results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        # Add runs but no matches for the agent/models
        storage.save_run("run_1", "test task", [
            {
                "agent_name": "claude",
                "model": "claude-3",
                "quality_score": 90.0,
                "duration_seconds": 100,
                "exit_code": 0,
                "stdout": "output",
                "stderr": ""
            }
        ])
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(compare_models, [
            '--agent', 'codex',
            '--models', 'gpt-4,gpt-4o'
        ])
        
        assert result.exit_code == 0
        # Should show no results table rows
        assert "N/A" in result.output
        
        storage.close()


def test_compare_models_partial_results():
    """Test model comparison with partial results for some models."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(Path(tmpdir) / "test.db")
        
        # Add runs with partial matches
        run_id_1 = "run_1"
        storage.save_run(run_id_1, "test task", [
            {
                "agent_name": "codex",
                "model": "gpt-4",
                "quality_score": 85.0,
                "duration_seconds": 120,
                "exit_code": 0,
                "stdout": "test output",
                "stderr": ""
            }
        ])
        
        run_id_2 = "run_2"
        storage.save_run(run_id_2, "another task", [
            {
                "agent_name": "codex",
                "model": "gpt-4o-mini",
                "quality_score": 75.0,
                "duration_seconds": 80,
                "exit_code": 0,
                "stdout": "mini output",
                "stderr": ""
            }
        ])
        
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(compare_models, [
            '--agent', 'codex',
            '--models', 'gpt-4,gpt-4o,gpt-4o-mini'
        ])
        
        assert result.exit_code == 0
        assert "gpt-4" in result.output
        assert "gpt-4o-mini" in result.output
        # gpt-4o should show N/A since no results
        assert "N/A" in result.output
        
        storage.close()


def test_compare_models_invalid_params():
    """Test model comparison with invalid parameters."""
    from click.testing import CliRunner
    runner = CliRunner()
    
    # Missing required agent
    result = runner.invoke(compare_models, [
        '--models', 'gpt-4,gpt-4o'
    ])
    assert result.exit_code == 2  # Click validation error
    
    # Missing required models  
    result = runner.invoke(compare_models, [
        '--agent', 'codex'
    ])
    assert result.exit_code == 2  # Click validation error
    
    # Empty models - click allows empty strings, command handles gracefully
    result = runner.invoke(compare_models, [
        '--agent', 'codex',
        '--models', ''
    ])
    # Empty string splits to [''], which shows N/A results
    assert result.exit_code == 0