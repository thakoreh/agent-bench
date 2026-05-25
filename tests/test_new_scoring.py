"""Tests for new v0.6.0 scoring factors: comment density, code cleanliness."""

from __future__ import annotations

from agent_bench.collector import RunMetrics
from agent_bench.scorer import (
    compute_comment_density,
    compute_quality_score,
    _code_cleanliness_penalty,
    _letter_grade,
)


def _make_metrics(**kwargs) -> RunMetrics:
    defaults = dict(
        exit_code=0, duration_seconds=60, tokens_in=1000, tokens_out=500,
        files_changed=2, lines_added=20, lines_removed=5,
        test_pass=8, test_total=8, lint_errors=0, lint_warnings=0,
        stdout="", stderr="",
    )
    defaults.update(kwargs)
    return RunMetrics(**defaults)


class TestCommentDensity:
    def test_empty_code(self):
        assert compute_comment_density("") == 0.15

    def test_whitespace_only(self):
        assert compute_comment_density("   \n  \t  ") == 0.15

    def test_no_comments(self):
        code = "x = 1\ny = 2\nprint(x + y)"
        density = compute_comment_density(code)
        assert density == 0.0

    def test_all_comments(self):
        code = "# comment 1\n# comment 2\n# comment 3"
        density = compute_comment_density(code)
        assert density == 1.0

    def test_mixed_code_comments(self):
        code = "# header\nx = 1\n# note\ny = 2\nprint(x)"
        density = compute_comment_density(code)
        assert 0.0 < density < 1.0

    def test_docstring_counts(self):
        code = '"""module docstring"""\nx = 1\ny = 2'
        density = compute_comment_density(code)
        assert density > 0

    def test_single_quotes_docstring(self):
        code = "'''module docstring'''\nx = 1"
        density = compute_comment_density(code)
        assert density > 0


class TestCodeCleanliness:
    def test_clean_output(self):
        assert _code_cleanliness_penalty("clean code", "") == 0.0

    def test_traceback_penalty(self):
        penalty = _code_cleanliness_penalty("Traceback (most recent call):", "")
        assert penalty > 0

    def test_syntax_error_penalty(self):
        penalty = _code_cleanliness_penalty("SyntaxError: invalid syntax", "")
        assert penalty > 0

    def test_severe_crashes(self):
        penalty = _code_cleanliness_penalty(
            "Traceback ... SyntaxError ... RuntimeError",
            "segfault"
        )
        assert penalty == 5.0

    def test_mixed_stderr(self):
        penalty = _code_cleanliness_penalty("ok", "RuntimeError")
        assert penalty > 0


class TestUpdatedScoringWeights:
    def test_perfect_run(self):
        code = '"""Module."""\n\ndef hello():\n    """Say hello."""\n    # greeting\n    return "hi"\n'
        m = _make_metrics(stdout=code)
        score, grade = compute_quality_score(m)
        assert score >= 70
        assert grade in ("A", "A-", "B+", "B", "B-", "C+")

    def test_score_bounded(self):
        m = _make_metrics()
        score, _ = compute_quality_score(m)
        assert 0 <= score <= 100

    def test_worst_case(self):
        m = RunMetrics(
            exit_code=1,
            duration_seconds=9999,
            test_pass=0,
            test_total=10,
            lint_errors=20,
            lint_warnings=10,
            lines_added=0,
            lines_removed=0,
            stdout="Traceback\nSyntaxError\nfrom os import *",
            stderr="ImportError\nRuntimeError",
        )
        score, grade = compute_quality_score(m)
        assert score < 40
        assert grade in ("D", "F")

    def test_comment_density_in_scoring(self):
        code_with_comments = "# header\nx = 1\n# note\ny = 2\n# end\nz = 3\n"
        code_without_comments = "x = 1\ny = 2\nz = 3\n"
        m_with = _make_metrics(stdout=code_with_comments)
        m_without = _make_metrics(stdout=code_without_comments)
        score_with, _ = compute_quality_score(m_with)
        score_without, _ = compute_quality_score(m_without)
        assert score_with > score_without

    def test_cleanliness_in_scoring(self):
        m_clean = _make_metrics(stdout="clean", stderr="")
        m_dirty = _make_metrics(stdout="Traceback (most recent call):", stderr="")
        score_clean, _ = compute_quality_score(m_clean)
        score_dirty, _ = compute_quality_score(m_dirty)
        assert score_clean > score_dirty
