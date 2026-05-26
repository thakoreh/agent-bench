"""Tests for v0.5.0 features: docstring coverage, type hint coverage, updated scoring."""

import pytest

from agent_bench.scorer import (
    compute_docstring_coverage,
    compute_type_hint_coverage,
    compute_quality_score,
    _letter_grade,
)
from agent_bench.collector import RunMetrics
from agent_bench.reporter import BREAKDOWN_FACTORS


class TestDocstringCoverage:
    """Tests for compute_docstring_coverage."""

    def test_empty_code(self):
        assert compute_docstring_coverage("") == 50.0

    def test_whitespace_only(self):
        assert compute_docstring_coverage("   \n  \n") == 50.0

    def test_invalid_syntax(self):
        assert compute_docstring_coverage("def foo(") == 50.0

    def test_fully_documented_module(self):
        code = '''"""Module docstring."""

def foo():
    """Foo docstring."""
    pass

class Bar:
    """Bar docstring."""
    pass
'''
        assert compute_docstring_coverage(code) == 100.0

    def test_partially_documented(self):
        code = '''"""Module docstring."""

def foo():
    """Has docstring."""
    pass

def bar():
    pass

class Baz:
    pass
'''
        # Module: yes, foo: yes, bar: no, Baz: no = 2/4 = 50%
        assert compute_docstring_coverage(code) == 50.0

    def test_undocumented(self):
        code = '''def foo():
    pass

def bar():
    pass
'''
        # No module docstring, no function docstrings = 0/3
        # (module body[0] is FunctionDef, not Expr with Constant str)
        result = compute_docstring_coverage(code)
        assert result == 0.0

    def test_class_with_methods(self):
        code = '''class MyClass:
    """Class doc."""
    
    def method_a(self):
        """Method A."""
        pass
    
    def method_b(self):
        pass
'''
        # Module: no (body[0] is ClassDef), MyClass: yes, method_a: yes, method_b: no = 2/4 = 50%
        # Module-level check finds ClassDef not Expr, so module counts as undocumented
        result = compute_docstring_coverage(code)
        assert 40 < result < 60

    def test_async_function(self):
        code = '''async def fetch():
    """Fetch data."""
    return 42
'''
        result = compute_docstring_coverage(code)
        # Module body[0] is AsyncFunctionDef not Expr, so module undocumented
        # total=2 (module + func), documented=1 (func has docstring) = 50%
        assert result == 50.0

    def test_no_definitions(self):
        code = '''x = 1
y = 2
'''
        # Only module-level check. body[0] is Assign, not Expr with Constant str
        # total=1, documented=0
        result = compute_docstring_coverage(code)
        assert result == 0.0


class TestTypeHintCoverage:
    """Tests for compute_type_hint_coverage."""

    def test_empty_code(self):
        assert compute_type_hint_coverage("") == 50.0

    def test_whitespace_only(self):
        assert compute_type_hint_coverage("   ") == 50.0

    def test_invalid_syntax(self):
        assert compute_type_hint_coverage("def foo(") == 50.0

    def test_fully_typed(self):
        code = '''def add(a: int, b: int) -> int:
    return a + b
'''
        result = compute_type_hint_coverage(code)
        assert result == 100.0

    def test_no_type_hints(self):
        code = '''def add(a, b):
    return a + b
'''
        # 0 annotated params, 0 annotated returns
        # total_params=2, annotated_params=0, returns=0
        # param_score=0, return_score=0
        result = compute_type_hint_coverage(code)
        assert result == 0.0

    def test_return_only(self):
        code = '''def foo() -> int:
    return 42
'''
        # No params, so param_score=80 (no params). Returns annotated.
        # weight_params=0, weight_returns=1.0
        result = compute_type_hint_coverage(code)
        assert result == 100.0

    def test_params_only(self):
        code = '''def foo(a: int, b: str):
    pass
'''
        # params annotated: 2/2=100, returns: 0/1=0
        # weight_params=0.6, weight_returns=0.4
        result = compute_type_hint_coverage(code)
        assert result == 60.0

    def test_self_skipped(self):
        code = '''class Foo:
    def bar(self, x: int) -> str:
        return str(x)
'''
        # self is skipped, x annotated, return annotated
        result = compute_type_hint_coverage(code)
        assert result == 100.0

    def test_no_functions(self):
        code = '''x = 1
y = 2
'''
        # No functions = trivially covered
        result = compute_type_hint_coverage(code)
        assert result == 80.0

    def test_async_function(self):
        code = '''async def fetch(url: str) -> bytes:
    return b""
'''
        result = compute_type_hint_coverage(code)
        assert result == 100.0

    def test_partial_annotation(self):
        code = '''def foo(a: int, b):
    return a + b
'''
        # 1/2 params annotated=50%, 0 returns=0%
        # weight_params=0.6, weight_returns=0.4
        result = compute_type_hint_coverage(code)
        assert result == pytest.approx(30.0, abs=0.1)


class TestUpdatedScoring:
    """Tests that the updated scoring formula includes new factors."""

    def _make_metrics(self, **kwargs) -> RunMetrics:
        defaults = {
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
            "duration_seconds": 30.0,
        }
        defaults.update(kwargs)
        return RunMetrics(**defaults)

    def test_max_score_approaches_100(self):
        """Well-documented, fully-typed code should score high."""
        code = '''"""Module docstring."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y
'''
        m = self._make_metrics(
            stdout=code,
            test_pass=10,
            test_total=10,
            lint_errors=0,
            lint_warnings=0,
            lines_added=20,
            lines_removed=5,
        )
        score, grade = compute_quality_score(m)
        # Should be well above 70
        assert score > 70
        assert grade in ("A", "A-", "B+", "B")

    def test_new_factors_dont_break_basic_scoring(self):
        """Ensure basic metrics still produce reasonable scores."""
        m = self._make_metrics(test_pass=5, test_total=10)
        score, grade = compute_quality_score(m)
        assert 0 <= score <= 100
        assert grade in ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F")

    def test_empty_stdout_gives_moderate_score(self):
        """Empty code should get neutral scores for new factors."""
        m = self._make_metrics(test_pass=5, test_total=10, lines_added=10, lines_removed=5)
        score, grade = compute_quality_score(m)
        assert 30 <= score <= 80

    def test_breakdown_factors_sum_to_100(self):
        """All breakdown factor max points should sum to 100."""
        total = sum(max_pts for _, max_pts in BREAKDOWN_FACTORS)
        assert total == 100


class TestLetterGradeBoundaries:
    """Test letter grade edge cases."""

    def test_exact_boundaries(self):
        assert _letter_grade(93.0) == "A"
        assert _letter_grade(90.0) == "A-"
        assert _letter_grade(87.0) == "B+"
        assert _letter_grade(83.0) == "B"
        assert _letter_grade(80.0) == "B-"
        assert _letter_grade(77.0) == "C+"
        assert _letter_grade(73.0) == "C"
        assert _letter_grade(70.0) == "C-"
        assert _letter_grade(60.0) == "D"

    def test_below_d(self):
        assert _letter_grade(59.9) == "F"
        assert _letter_grade(0) == "F"

    def test_perfect_score(self):
        assert _letter_grade(100) == "A"

    def test_just_above_boundary(self):
        assert _letter_grade(93.1) == "A"
        assert _letter_grade(90.1) == "A-"
