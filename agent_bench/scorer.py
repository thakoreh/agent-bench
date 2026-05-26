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


def compute_comment_density(code: str) -> float:
    """Compute comment density as ratio of comment lines to total lines.

    Returns a value between 0.0 and 1.0.
    Returns 0.15 (neutral) if the code is empty.
    """
    if not code.strip():
        return 0.15

    lines = code.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return 0.15

    comment_lines = 0
    for line in non_empty:
        stripped = line.strip()
        if stripped.startswith('#'):
            comment_lines += 1
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            comment_lines += 1

    return comment_lines / len(non_empty)


def _code_cleanliness_penalty(stdout: str, stderr: str) -> float:
    """Compute penalty (0-5 points) for crashes/errors in output.

    Returns 0.0 if clean, up to 5.0 for severe issues.
    """
    combined = f"{stdout}\n{stderr}"
    crashes = len(re.findall(
        r"Traceback|SyntaxError|RuntimeError|segfault|core dumped",
        combined, re.IGNORECASE
    ))
    if crashes == 0:
        return 0.0
    elif crashes <= 2:
        return 3.0
    else:
        return 5.0


def compute_quality_score(metrics: RunMetrics) -> tuple[float, str]:
    """
    Compute quality score (0-100) and letter grade.

    Formula (11 factors):
    - Test pass rate: 25%
    - Lint clean: 12%
    - Code diff sensibility: 10%
    - Task completion (exit code 0): 10%
    - Speed bonus: 7%
    - Import hygiene: 7%
    - Complexity: 6%
    - Docstring coverage: 7%
    - Type hint coverage: 7%
    - Comment density: 5%
    - Code cleanliness: 4%
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

    # Code diff sensibility: 10 points
    total_changes: int = metrics.lines_added + metrics.lines_removed
    if total_changes == 0:
        score += 0
    elif total_changes <= 5:
        score += 5
    elif total_changes <= 50:
        score += 10
    elif total_changes <= 200:
        score += 7
    else:
        score += 3

    # Task completion: 10 points
    if metrics.exit_code == 0:
        score += 10
    else:
        score += 2

    # Speed bonus: 7 points
    duration: float = metrics.duration_seconds
    if duration <= 30:
        score += 7
    elif duration <= 120:
        score += 5
    elif duration <= 300:
        score += 3
    elif duration <= 600:
        score += 1
    else:
        score += 0

    # Import hygiene: 7 points
    import_issues: int = _count_import_issues(metrics.stdout, metrics.stderr)
    unused_imports: int = _count_unused_imports(metrics.stdout)
    total_import_issues: int = import_issues + unused_imports
    if total_import_issues == 0:
        score += 7
    elif total_import_issues <= 2:
        score += 4
    elif total_import_issues <= 5:
        score += 2
    else:
        score += 0

    # Complexity: 6 points
    complexity: float = compute_complexity_score(metrics.stdout)
    score += complexity * 0.06

    # Docstring coverage: 7 points
    docstring_cov: float = compute_docstring_coverage(metrics.stdout)
    score += docstring_cov * 0.07

    # Type hint coverage: 7 points
    type_hint_cov: float = compute_type_hint_coverage(metrics.stdout)
    score += type_hint_cov * 0.07

    # Comment density: 5 points
    comment_density: float = compute_comment_density(metrics.stdout)
    if 0.1 <= comment_density <= 0.3:
        score += 5
    elif comment_density < 0.1:
        score += comment_density * 30
    else:
        score += max(0, 5 - (comment_density - 0.3) * 15)

    # Code cleanliness: 4 points (penalty-based)
    score += 4 - _code_cleanliness_penalty(metrics.stdout, metrics.stderr)

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
