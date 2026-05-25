"""Score agent run quality."""

from __future__ import annotations

import ast
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


def compute_docstring_coverage(code: str) -> float:
    """Compute docstring coverage ratio (0-100).

    Parses Python code via AST and checks for docstrings on
    modules, classes, and functions/methods.

    Returns 50.0 (neutral) if the code cannot be parsed.
    """
    if not code.strip():
        return 50.0

    try:
        tree: ast.Module = ast.parse(code)
    except (SyntaxError, ValueError):
        return 50.0

    total: int = 0
    documented: int = 0

    # Module-level docstring
    total += 1
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        documented += 1

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                documented += 1

    if total == 0:
        return 80.0  # No definitions = trivially covered

    return (documented / total) * 100.0


def compute_type_hint_coverage(code: str) -> float:
    """Compute type hint coverage for function signatures (0-100).

    Checks function definitions for return type annotations and
    parameter annotations.

    Returns 50.0 (neutral) if the code cannot be parsed.
    """
    if not code.strip():
        return 50.0

    try:
        tree: ast.Module = ast.parse(code)
    except (SyntaxError, ValueError):
        return 50.0

    total_functions: int = 0
    annotated_params: int = 0
    total_params: int = 0
    annotated_returns: int = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_functions += 1

            # Count annotated parameters (skip self/cls)
            args = node.args
            all_args = args.args + args.posonlyargs + args.kwonlyargs
            for arg in all_args:
                if arg.arg in ("self", "cls"):
                    continue
                total_params += 1
                if arg.annotation is not None:
                    annotated_params += 1

            # Return annotation
            if node.returns is not None:
                annotated_returns += 1

    if total_functions == 0:
        return 80.0  # No functions = trivially covered

    if total_params == 0 and total_functions == 0:
        return 80.0

    # Weight: params 60%, returns 40%
    param_score: float = (annotated_params / total_params * 100) if total_params > 0 else 80.0
    return_score: float = (annotated_returns / total_functions * 100) if total_functions > 0 else 0.0

    weight_params: float = 0.6 if total_params > 0 else 0.0
    weight_returns: float = 1.0 - weight_params

    return param_score * weight_params + return_score * weight_returns


def compute_quality_score(metrics: RunMetrics) -> tuple[float, str]:
    """
    Compute quality score (0-100) and letter grade.

    Formula:
    - Test pass rate: 25%
    - Lint clean: 12%
    - Code diff sensibility: 11%
    - Task completion (exit code 0): 11%
    - Speed bonus: 8%
    - Import hygiene: 8%
    - Complexity: 7%
    - Docstring coverage: 9%
    - Type hint coverage: 9%
    """
    score: float = 0.0

    # Test pass rate: 25 points
    if metrics.test_total > 0:
        test_rate: float = metrics.test_pass / metrics.test_total
        score += test_rate * 25
    else:
        # No tests = neutral (give half)
        score += 12.5

    # Lint clean: 12 points
    if metrics.lint_errors == 0 and metrics.lint_warnings == 0:
        score += 12
    elif metrics.lint_errors == 0:
        score += 6
    else:
        score += max(0, 12 - metrics.lint_errors * 2)

    # Code diff sensibility: 11 points
    total_changes: int = metrics.lines_added + metrics.lines_removed
    if total_changes == 0:
        score += 0
    elif total_changes <= 5:
        score += 6
    elif total_changes <= 50:
        score += 11
    elif total_changes <= 200:
        score += 8
    else:
        score += 3

    # Task completion: 11 points
    if metrics.exit_code == 0:
        score += 11
    else:
        score += 2

    # Speed bonus: 8 points
    duration: float = metrics.duration_seconds
    if duration <= 30:
        score += 8
    elif duration <= 120:
        score += 6
    elif duration <= 300:
        score += 4
    elif duration <= 600:
        score += 2
    else:
        score += 0

    # Import hygiene: 8 points
    import_issues: int = _count_import_issues(metrics.stdout, metrics.stderr)
    unused_imports: int = _count_unused_imports(metrics.stdout)
    total_import_issues: int = import_issues + unused_imports
    if total_import_issues == 0:
        score += 8
    elif total_import_issues <= 2:
        score += 5
    elif total_import_issues <= 5:
        score += 2
    else:
        score += 0

    # Complexity: 7 points
    complexity: float = compute_complexity_score(metrics.stdout)
    score += complexity * 0.07

    # Docstring coverage: 9 points
    docstring_cov: float = compute_docstring_coverage(metrics.stdout)
    score += docstring_cov * 0.09

    # Type hint coverage: 9 points
    type_hint_cov: float = compute_type_hint_coverage(metrics.stdout)
    score += type_hint_cov * 0.09

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
