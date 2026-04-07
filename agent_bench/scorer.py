"""Score agent run quality."""

from __future__ import annotations

from .collector import RunMetrics


def compute_quality_score(metrics: RunMetrics) -> tuple[float, str]:
    """
    Compute quality score (0-100) and letter grade.

    Formula:
    - Test pass rate: 40%
    - Lint clean: 20%
    - Code diff sensibility: 15%
    - Task completion (exit code 0): 15%
    - Speed bonus: 10%
    """
    score = 0.0

    # Test pass rate: 40 points
    if metrics.test_total > 0:
        test_rate = metrics.test_pass / metrics.test_total
        score += test_rate * 40
    else:
        # No tests = neutral (give half)
        score += 20

    # Lint clean: 20 points
    if metrics.lint_errors == 0 and metrics.lint_warnings == 0:
        score += 20
    elif metrics.lint_errors == 0:
        score += 10
    else:
        score += max(0, 20 - metrics.lint_errors * 4)

    # Code diff sensibility: 15 points
    # Reward changes but penalize too many or too few
    total_changes = metrics.lines_added + metrics.lines_removed
    if total_changes == 0:
        score += 0  # No changes = bad
    elif total_changes <= 5:
        score += 8
    elif total_changes <= 50:
        score += 15
    elif total_changes <= 200:
        score += 10
    else:
        score += 5  # Too many changes

    # Task completion: 15 points
    if metrics.exit_code == 0:
        score += 15
    else:
        score += 2

    # Speed bonus: 10 points (relative, use absolute thresholds)
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
