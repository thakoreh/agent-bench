"""SQLite storage for benchmark run history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .collector import RunMetrics

DEFAULT_DB_PATH = Path.home() / ".agent-bench" / "history.db"


class Storage:
    """SQLite-backed storage for benchmark results."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                task TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                exit_code INTEGER,
                duration_seconds REAL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost REAL,
                files_changed INTEGER,
                lines_added INTEGER,
                lines_removed INTEGER,
                test_pass INTEGER,
                test_total INTEGER,
                lint_errors INTEGER,
                lint_warnings INTEGER,
                quality_score REAL,
                quality_grade TEXT,
                stdout TEXT,
                stderr TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id);
            CREATE INDEX IF NOT EXISTS idx_results_run_id ON agent_results(run_id);
        """)

    def save_run(self, run_id: str, task: str, results: list[dict[str, Any]]) -> None:
        """Save a complete benchmark run."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO runs (run_id, timestamp, task) VALUES (?, ?, ?)",
            (run_id, now, task),
        )
        for r in results:
            conn.execute(
                """INSERT INTO agent_results
                (run_id, agent_name, exit_code, duration_seconds, tokens_in, tokens_out,
                 cost, files_changed, lines_added, lines_removed, test_pass, test_total,
                 lint_errors, lint_warnings, quality_score, quality_grade, stdout, stderr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, r.get("agent_name"), r.get("exit_code"),
                    r.get("duration_seconds"), r.get("tokens_in"), r.get("tokens_out"),
                    r.get("cost"), r.get("files_changed"), r.get("lines_added"),
                    r.get("lines_removed"), r.get("test_pass"), r.get("test_total"),
                    r.get("lint_errors"), r.get("lint_warnings"),
                    r.get("quality_score"), r.get("quality_grade"),
                    r.get("stdout", ""), r.get("stderr", ""),
                ),
            )
        conn.commit()

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """Get a specific run with its results."""
        conn = self._get_conn()
        run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not run:
            return None
        results = conn.execute(
            "SELECT * FROM agent_results WHERE run_id = ?", (run_id,)
        ).fetchall()
        return {
            "run_id": run["run_id"],
            "timestamp": run["timestamp"],
            "task": run["task"],
            "results": [dict(r) for r in results],
        }

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent runs."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {"run_id": r["run_id"], "timestamp": r["timestamp"], "task": r["task"]}
            for r in rows
        ]

    def get_latest_run(self) -> Optional[dict[str, Any]]:
        """Get the most recent run."""
        runs = self.list_runs(limit=1)
        if not runs:
            return None
        return self.get_run(runs[0]["run_id"])

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
