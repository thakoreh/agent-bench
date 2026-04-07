"""Tests for scorer module."""

import pytest
from agent_bench.collector import RunMetrics
from agent_bench.scorer import compute_quality_score, _letter_grade


def _make_metrics(**kwargs) -> RunMetrics:
    defaults = dict(
        exit_code=0, duration_seconds=60, tokens_in=1000, tokens_out=500,
        files_changed=2, lines_added=20, lines_removed=5,
        test_pass=8, test_total=8, lint_errors=0, lint_warnings=0,
    )
    defaults.update(kwargs)
    return RunMetrics(**defaults)


class TestComputeQualityScore:
    def test_perfect_run(self):
        m = _make_metrics()
        score, grade = compute_quality_score(m)
        assert score >= 90
        assert grade in ("A", "A-")

    def test_failed_tests(self):
        m = _make_metrics(test_pass=4, test_total=8)
        score, _ = compute_quality_score(m)
        assert score < 85

    def test_lint_errors(self):
        m = _make_metrics(lint_errors=5)
        score, _ = compute_quality_score(m)
        assert score < 85

    def test_nonzero_exit(self):
        m = _make_metrics(exit_code=1)
        score, _ = compute_quality_score(m)
        assert score < 90

    def test_no_changes(self):
        m = _make_metrics(files_changed=0, lines_added=0, lines_removed=0)
        score, _ = compute_quality_score(m)
        assert score < 87

    def test_slow_run(self):
        m = _make_metrics(duration_seconds=900)
        score, _ = compute_quality_score(m)
        assert score < 95

    def test_no_tests(self):
        m = _make_metrics(test_pass=0, test_total=0)
        score, _ = compute_quality_score(m)
        # Should get half credit (20/40)
        assert 50 < score < 90

    def test_score_bounded(self):
        m = _make_metrics()
        score, _ = compute_quality_score(m)
        assert 0 <= score <= 100


class TestLetterGrade:
    @pytest.mark.parametrize("score,grade", [
        (95, "A"), (91, "A-"), (88, "B+"), (85, "B"),
        (81, "B-"), (78, "C+"), (75, "C"), (71, "C-"),
        (65, "D"), (50, "F"),
    ])
    def test_grade_boundaries(self, score, grade):
        assert _letter_grade(score) == grade
