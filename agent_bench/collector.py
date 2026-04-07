"""Collect metrics from agent runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RunMetrics:
    """Metrics collected from a single agent run."""
    exit_code: int = -1
    duration_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    stdout: str = ""
    stderr: str = ""
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    test_pass: int = 0
    test_total: int = 0
    lint_errors: int = 0
    lint_warnings: int = 0
    cost: float = 0.0


# Token parsing patterns for different agents
TOKEN_PATTERNS: list[re.Pattern[str]] = [
    # Claude Code: "Token usage: X input, Y output"
    re.compile(r"(?:input|in)\s*[:\s]+(\d[\d,]*).*?(?:output|out)\s*[:\s]+(\d[\d,]*)", re.I | re.S),
    # Generic: "tokens: X in, Y out"
    re.compile(r"(\d[\d,]*)\s*(?:input|in)\s*.*?(\d[\d,]*)\s*(?:output|out)", re.I),
    # "X/Y tokens" or "used X tokens"
    re.compile(r"(\d[\d,]*)\s*tokens?\s*(?:in|input)?[,\s]+(\d[\d,]*)\s*tokens?\s*(?:out|output)?", re.I),
]


def parse_tokens(output: str) -> tuple[int, int]:
    """Parse token usage from agent output."""
    for pattern in TOKEN_PATTERNS:
        match = pattern.search(output)
        if match:
            tokens_in = int(match.group(1).replace(",", ""))
            tokens_out = int(match.group(2).replace(",", ""))
            return tokens_in, tokens_out
    return 0, 0


def parse_test_results(output: str) -> tuple[int, int]:
    """Parse test results from pytest output. Returns (passed, total)."""
    # pytest: "X passed, Y failed" or "X passed"
    passed = 0
    total = 0

    # Match "X passed"
    m = re.search(r"(\d+)\s+passed", output)
    if m:
        passed = int(m.group(1))

    # Match "X failed"
    failed = 0
    m = re.search(r"(\d+)\s+failed", output)
    if m:
        failed = int(m.group(1))

    # Match "X error" / "X errors"
    m = re.search(r"(\d+)\s+error", output)
    if m:
        failed += int(m.group(1))

    total = passed + failed
    if total == 0 and passed > 0:
        total = passed
    return passed, total


def parse_lint_results(output: str) -> tuple[int, int]:
    """Parse lint output for errors/warnings. Returns (errors, warnings)."""
    errors = 0
    warnings = 0

    # ruff format: "file.py:1:1: E001 message"
    for m in re.finditer(r":\s*E\d+", output):
        errors += 1
    for m in re.finditer(r":\s*W\d+", output):
        warnings += 1

    # flake8 format similar
    # Generic: "X error(s), Y warning(s)"
    m = re.search(r"(\d+)\s+error", output, re.I)
    if m:
        errors = max(errors, int(m.group(1)))
    m = re.search(r"(\d+)\s+warning", output, re.I)
    if m:
        warnings = max(warnings, int(m.group(1)))

    return errors, warnings


def collect_from_output(
    stdout: str,
    stderr: str,
    exit_code: int,
    duration: float,
    diff_stat: str = "",
    test_output: str = "",
    lint_output: str = "",
) -> RunMetrics:
    """Collect all metrics from a completed run."""
    metrics = RunMetrics()
    metrics.exit_code = exit_code
    metrics.duration_seconds = duration
    metrics.stdout = stdout
    metrics.stderr = stderr

    # Parse tokens from combined output
    combined = f"{stdout}\n{stderr}"
    metrics.tokens_in, metrics.tokens_out = parse_tokens(combined)

    # Parse diff stats
    if diff_stat:
        m = re.search(r"(\d+)\s+(?:files?|insertions?)", diff_stat)
        if m:
            metrics.files_changed = int(m.group(1))
        m = re.search(r"(\d+)\s+insertion", diff_stat)
        if m:
            metrics.lines_added = int(m.group(1))
        m = re.search(r"(\d+)\s+deletion", diff_stat)
        if m:
            metrics.lines_removed = int(m.group(1))

    # Parse test results
    if test_output:
        metrics.test_pass, metrics.test_total = parse_test_results(test_output)

    # Parse lint results
    if lint_output:
        metrics.lint_errors, metrics.lint_warnings = parse_lint_results(lint_output)

    return metrics
