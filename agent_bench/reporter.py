"""Format benchmark results as tables, JSON, or markdown."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs:02d}s"


def _format_tokens(count: int) -> str:
    """Format token count."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _test_status(passed: int, total: int) -> str:
    """Format test status with emoji."""
    if total == 0:
        return "—"
    if passed == total:
        return f"{passed}/{total} ✅"
    if passed > total * 0.5:
        return f"{passed}/{total} ⚠️"
    return f"{passed}/{total} ❌"


def format_table(run_data: dict[str, Any]) -> str:
    """Format run data as a Rich table string."""
    console = Console(width=100)
    task = run_data.get("task", "Unknown")
    timestamp = run_data.get("timestamp", "")
    results = run_data.get("results", [])

    if not results:
        return "No results to display."

    # Sort by quality score descending
    sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)

    table = Table(title="Agent Benchmark Results", show_lines=True)
    table.add_column("Agent", style="bold")
    table.add_column("Time", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Tokens", justify="right")
    table.add_column("Tests", justify="center")
    table.add_column("Quality", justify="center", style="bold")

    for r in sorted_results:
        name = r.get("agent_name", "?")
        duration = _format_duration(r.get("duration_seconds", 0))
        cost = f"${r.get('cost', 0):.2f}"
        tokens_in = _format_tokens(r.get("tokens_in", 0))
        tokens_out = _format_tokens(r.get("tokens_out", 0))
        token_str = f"{tokens_in} → {tokens_out}" if tokens_in != "0" else "—"
        tests = _test_status(r.get("test_pass", 0), r.get("test_total", 0))
        score = r.get("quality_score", 0)
        grade = r.get("quality_grade", "?")
        quality = f"{grade} ({score:.0f}/100)"

        table.add_row(name, duration, cost, token_str, tests, quality)

    with console.capture() as capture:
        console.print()
        console.print(f"  Task: [italic]\"{task}\"[/italic]")
        console.print(f"  Run: {timestamp}")
        console.print(table)

    # Winner annotations
    output = capture.get()

    if sorted_results:
        best = sorted_results[0]
        fastest = min(results, key=lambda r: r.get("duration_seconds", float("inf")))
        cheapest = min(results, key=lambda r: r.get("cost", float("inf")))

        lines = [
            f"\n  Winner: {best['agent_name']} ({best.get('quality_grade', '?')} — best quality)",
            f"  Fastest: {fastest['agent_name']} ({_format_duration(fastest.get('duration_seconds', 0))})",
            f"  Cheapest: {cheapest['agent_name']} (${cheapest.get('cost', 0):.2f})",
        ]
        output += "\n".join(lines)

    return output


def format_json(run_data: dict[str, Any]) -> str:
    """Format run data as JSON."""
    return json.dumps(run_data, indent=2, default=str)


def format_history(runs: list[dict[str, Any]]) -> str:
    """Format run history as a table."""
    if not runs:
        return "No benchmark runs found."

    console = Console(width=80)
    table = Table(title="Benchmark History", show_lines=True)
    table.add_column("Run ID", style="bold")
    table.add_column("Timestamp")
    table.add_column("Task", max_width=40, no_wrap=True)

    for run in runs:
        task = run.get("task", "")
        if len(task) > 40:
            task = task[:37] + "..."
        table.add_row(run.get("run_id", "?"), run.get("timestamp", ""), task)

    with console.capture() as capture:
        console.print(table)

    return capture.get()
