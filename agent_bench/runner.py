"""Run agents on tasks and collect results."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .collector import RunMetrics, collect_from_output
from .config import Config
from .pricing import estimate_cost
from .scorer import compute_quality_score
from .storage import Storage


class AgentRunner:
    """Runs a single agent on a task."""

    def __init__(self, config: Config, storage: Optional[Storage] = None) -> None:
        self.config = config
        self.storage = storage or Storage()

    def run_agent(
        self,
        agent_name: str,
        task: str,
        workdir: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run a single agent on a task and return results dict."""
        agent_cfg = self.config.get_agent_config(agent_name)
        if not agent_cfg:
            raise ValueError(f"Agent '{agent_name}' not found in config")

        command = agent_cfg.get("command", agent_name)
        args = agent_cfg.get("args", [])
        effective_timeout = timeout or self.config.timeout

        # Create isolated workspace
        source_dir = workdir or Path.cwd()
        tmp_dir = tempfile.mkdtemp(prefix=f"agent-bench-{agent_name}-")

        try:
            # Copy source to temp dir
            shutil.copytree(source_dir, tmp_dir, dirs_exist_ok=True)

            # Build command
            full_cmd = [command] + args + [task]

            start = datetime.now()
            try:
                proc = subprocess.run(
                    full_cmd,
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=effective_timeout,
                )
                exit_code = proc.returncode
                stdout = proc.stdout
                stderr = proc.stderr
            except subprocess.TimeoutExpired:
                exit_code = -1
                stdout = ""
                stderr = f"Timeout after {effective_timeout}s"
            except FileNotFoundError:
                exit_code = -2
                stdout = ""
                stderr = f"Agent command '{command}' not found"

            duration = (datetime.now() - start).total_seconds()

            # Get diff stats
            diff_stat = self._get_diff_stat(source_dir, Path(tmp_dir))

            # Run tests if enabled
            test_output = ""
            if self.config.run_tests:
                test_output = self._run_tests(tmp_dir)

            # Run lint if enabled
            lint_output = ""
            if self.config.run_lint:
                lint_output = self._run_lint(tmp_dir)

            # Collect metrics
            metrics = collect_from_output(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration=duration,
                diff_stat=diff_stat,
                test_output=test_output,
                lint_output=lint_output,
            )

            # Calculate cost
            metrics.cost = estimate_cost(agent_name, metrics.tokens_in, metrics.tokens_out)

            # Compute quality score
            quality_score, quality_grade = compute_quality_score(metrics)

            return {
                "agent_name": agent_name,
                "exit_code": metrics.exit_code,
                "duration_seconds": metrics.duration_seconds,
                "tokens_in": metrics.tokens_in,
                "tokens_out": metrics.tokens_out,
                "cost": metrics.cost,
                "files_changed": metrics.files_changed,
                "lines_added": metrics.lines_added,
                "lines_removed": metrics.lines_removed,
                "test_pass": metrics.test_pass,
                "test_total": metrics.test_total,
                "lint_errors": metrics.lint_errors,
                "lint_warnings": metrics.lint_warnings,
                "quality_score": quality_score,
                "quality_grade": quality_grade,
                "stdout": metrics.stdout[:10000],  # Truncate for storage
                "stderr": metrics.stderr[:5000],
            }

        finally:
            # Clean up temp dir
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def run_all(
        self,
        task: Optional[str] = None,
        agents: Optional[list[str]] = None,
        workdir: Optional[Path] = None,
    ) -> dict[str, Any]:
        """Run all (or specified) agents on a task."""
        effective_task = task or self.config.default_task
        if not effective_task:
            raise ValueError("No task specified and no default task configured")

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        agent_list = agents or list(self.config.agents.keys())

        results = []
        for agent_name in agent_list:
            print(f"Running {agent_name}...")
            result = self.run_agent(agent_name, effective_task, workdir)
            results.append(result)

        # Save to storage
        self.storage.save_run(run_id, effective_task, results)

        return {
            "run_id": run_id,
            "task": effective_task,
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }

    def _get_diff_stat(self, original: Path, modified: Path) -> str:
        """Get diff stat between original and modified directories."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", str(original), str(modified)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    def _run_tests(self, directory: str) -> str:
        """Run pytest in directory."""
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "--tb=no", "-q"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _run_lint(self, directory: str) -> str:
        """Run ruff or flake8 in directory."""
        for cmd in ["ruff", "flake8"]:
            try:
                result = subprocess.run(
                    [cmd, "check", "."],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.stdout + result.stderr
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return ""
        return ""
