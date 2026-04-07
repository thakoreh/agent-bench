"""Score agent run quality."""

from __future__ import annotations

import re
from typing import Optional

from .collector import RunMetrics


def compute_complexity_score(code: str) -> float:
    """Compute readability score from cyclomatic complexity via radon.

    Returns 0-100 where lower complexity = higher score.
    Returns 50.0 (neutral) if radon is not installed.
    """
    try:
        from radon.complexity import cc_visit
        from radon.visitors import ComplexityVisitor
    except ImportError:
        return 50.0

    if not code.strip():
        return 50.0

    try:
        blocks = cc_visit(code)
    except Exception:
        return 50.0

    if not blocks:
        return 80.0  # No complexity blocks = simple code

    avg_complexity = sum(b.complexity for b in blocks) / len(blocks)
    # Lower complexity = higher score. complexity 1-5 → 100-80, 6-10 → 80-60, etc.
    score = max(0.0, min(100.0, 100.0 - (avg_complexity - 1) * 10))
    return score


def _count_import_issues(stdout: str, stderr: str) -> int:
    """Count import-related issues in agent output."""
    issues = 0
    combined = f"{stdout}\n{stderr}"
    # Match common import errors
    issues += len(re.findall(r"ImportError", combined))
    issues += len(re.findall(r"ModuleNotFoundError", combined))
    # Wildcard imports (bad practice)
    issues += len(re.findall(r"from \S+ import \*", combined))
    return issues


def _count_unused_imports(stdout: str) -> int:
    """Count unused import warnings (from linters)."""
    return len(re.findall(r"F401|unused import", stdout))


def compute_quality_score(metrics: RunMetrics) -> tuple[float, str]:
    """
    Compute quality score (0-100) and letter grade.

    Formula:
    - Test pass rate: 30%
    - Lint clean: 14%
    - Code diff sensibility: 13%
    - Task completion (exit code 0): 13%
    - Speed bonus: 10%
    - Import hygiene: 10%
    - Complexity: 10%
    """
    score = 0.0

    # Test pass rate: 30 points
    if metrics.test_total > 0:
        test_rate = metrics.test_pass / metrics.test_total
        score += test_rate * 30
    else:
        # No tests = neutral (give half)
        score += 15

    # Lint clean: 14 points
    if metrics.lint_errors == 0 and metrics.lint_warnings == 0:
        score += 14
    elif metrics.lint_errors == 0:
        score += 7
    else:
        score += max(0, 14 - metrics.lint_errors * 3)

    # Code diff sensibility: 13 points
    total_changes = metrics.lines_added + metrics.lines_removed
    if total_changes == 0:
        score += 0
    elif total_changes <= 5:
        score += 7
    elif total_changes <= 50:
        score += 13
    elif total_changes <= 200:
        score += 9
    else:
        score += 4

    # Task completion: 13 points
    if metrics.exit_code == 0:
        score += 13
    else:
        score += 2

    # Speed bonus: 10 points
    duration = metrics.duration_seconds
    if duration <= 30:
        score += 10
    elif duration <= 120:
        score += 8
    elif duration <= 300:
        score += 5
    elif duration <= 600:
        score += 3
    else:
        score += 0

    # Import hygiene: 10 points
    import_issues = _count_import_issues(metrics.stdout, metrics.stderr)
    unused_imports = _count_unused_imports(metrics.stdout)
    total_import_issues = import_issues + unused_imports
    if total_import_issues == 0:
        score += 10
    elif total_import_issues <= 2:
        score += 6
    elif total_import_issues <= 5:
        score += 3
    else:
        score += 0

    # Complexity: 10 points
    complexity = compute_complexity_score(metrics.stdout)
    score += complexity * 0.10

    return min(100, score), _letter_grade(score)


def _letter_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 60:
        return "D"
    return "F"
