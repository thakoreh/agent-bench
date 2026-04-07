"""Tests for storage module."""

import json
from pathlib import Path

import pytest

from agent_bench.storage import Storage


@pytest.fixture
def storage(tmp_path):
    return Storage(path=tmp_path / "test.db")


def _sample_result(agent_name="test-agent", **kwargs):
    defaults = dict(
        agent_name=agent_name, exit_code=0, duration_seconds=60.0,
        tokens_in=1000, tokens_out=500, cost=0.05,
        files_changed=3, lines_added=20, lines_removed=5,
        test_pass=8, test_total=8, lint_errors=0, lint_warnings=0,
        quality_score=92.0, quality_grade="A", stdout="", stderr="",
    )
    defaults.update(kwargs)
    return defaults


def test_save_and_get_run(storage):
    results = [_sample_result("agent-a"), _sample_result("agent-b")]
    storage.save_run("run-1", "test task", results)
    run = storage.get_run("run-1")
    assert run is not None
    assert run["task"] == "test task"
    assert len(run["results"]) == 2


def test_list_runs(storage):
    storage.save_run("run-1", "task 1", [_sample_result()])
    storage.save_run("run-2", "task 2", [_sample_result()])
    runs = storage.list_runs()
    assert len(runs) == 2


def test_list_runs_limit(storage):
    for i in range(5):
        storage.save_run(f"run-{i}", f"task {i}", [_sample_result()])
    runs = storage.list_runs(limit=3)
    assert len(runs) == 3


def test_get_latest_run(storage):
    storage.save_run("run-1", "old", [_sample_result()])
    storage.save_run("run-2", "new", [_sample_result()])
    latest = storage.get_latest_run()
    assert latest["task"] == "new"


def test_get_nonexistent_run(storage):
    assert storage.get_run("nonexistent") is None


def test_get_latest_empty(storage):
    assert storage.get_latest_run() is None


def test_db_created(storage):
    assert storage.path.exists()


def test_close(storage):
    storage.close()
    # Should be reusable after close
    storage.save_run("run-1", "task", [_sample_result()])
    assert storage.get_run("run-1") is not None
