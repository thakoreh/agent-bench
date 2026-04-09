"""Format benchmark results as tables, JSON, or markdown."""

from __future__ import annotations

import csv
import io
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


def format_table(run_data: dict[str, Any], sort_by: str = "quality") -> str:
    """Format run data as a Rich table string."""
    console = Console(width=110)
    task = run_data.get("task", "Unknown")
    timestamp = run_data.get("timestamp", "")
    results = run_data.get("results", [])

    if not results:
        return "No results to display."

    # Add cost_efficiency to each result
    for r in results:
        r["cost_efficiency"] = r.get("quality_score", 0) / max(r.get("cost", 0), 0.01)

    if sort_by == "cost-efficiency":
        sorted_results = sorted(results, key=lambda r: r.get("cost_efficiency", 0), reverse=True)
    else:
        sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)

    table = Table(title="Agent Benchmark Results", show_lines=True)
    table.add_column("Agent", style="bold")
    table.add_column("Time", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Tokens", justify="right")
    table.add_column("Tests", justify="center")
    table.add_column("Quality", justify="center", style="bold")
    table.add_column("Cost Eff.", justify="right")

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
        ce = r.get("cost_efficiency", 0)

        table.add_row(name, duration, cost, token_str, tests, quality, f"{ce:.1f}")

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


def format_markdown(run_data: dict[str, Any]) -> str:
    """Format run data as markdown for sharing."""
    task = run_data.get("task", "Unknown")
    timestamp = run_data.get("timestamp", "")
    results = run_data.get("results", [])
    run_id = run_data.get("run_id", "?")

    if not results:
        return "No results to display."

    sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)

    lines = [
        f"# Agent Benchmark Results",
        f"",
        f"**Task:** {task}",
        f"**Run ID:** {run_id}",
        f"**Timestamp:** {timestamp}",
        f"",
        f"| Agent | Time | Cost | Tokens | Tests | Quality |",
        f"|-------|------|------|--------|-------|---------|",
    ]

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

        lines.append(f"| {name} | {duration} | {cost} | {token_str} | {tests} | {quality} |")

    # Summary
    if sorted_results:
        best = sorted_results[0]
        fastest = min(results, key=lambda r: r.get("duration_seconds", float("inf")))
        cheapest = min(results, key=lambda r: r.get("cost", float("inf")))
        lines.extend([
            f"",
            f"**Winner:** {best['agent_name']} ({best.get('quality_grade', '?')} — best quality)",
            f"**Fastest:** {fastest['agent_name']} ({_format_duration(fastest.get('duration_seconds', 0))})",
            f"**Cheapest:** {cheapest['agent_name']} (${cheapest.get('cost', 0):.2f})",
        ])

    return "\n".join(lines)


def format_baseline_table(current: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Format current vs baseline as a comparison table."""
    console = Console(width=120)

    current_results = {r["agent_name"]: r for r in current.get("results", [])}
    baseline_results = {r["agent_name"]: r for r in baseline.get("results", [])}
    all_agents = sorted(set(current_results) | set(baseline_results))

    table = Table(title="Current vs Baseline", show_lines=True)
    table.add_column("Agent", style="bold")
    table.add_column("Score (now)", justify="center")
    table.add_column("Score (base)", justify="center")
    table.add_column("Delta", justify="center")
    table.add_column("Cost (now)", justify="right")
    table.add_column("Cost (base)", justify="right")
    table.add_column("Time (now)", justify="right")

    for agent in all_agents:
        cur = current_results.get(agent, {})
        bas = baseline_results.get(agent, {})

        cur_score = cur.get("quality_score", 0)
        bas_score = bas.get("quality_score", 0)
        delta = cur_score - bas_score

        delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
        if delta > 0:
            delta_str = f"[green]{delta_str}[/green]"
        elif delta < 0:
            delta_str = f"[red]{delta_str}[/red]"
        else:
            delta_str = f"{delta_str}"

        table.add_row(
            agent,
            f"{cur.get('quality_grade', '?')} ({cur_score:.0f})",
            f"{bas.get('quality_grade', '?')} ({bas_score:.0f})",
            delta_str,
            f"${cur.get('cost', 0):.2f}",
            f"${bas.get('cost', 0):.2f}",
            _format_duration(cur.get("duration_seconds", 0)),
        )

    with console.capture() as capture:
        console.print(f"  Current: {current.get('run_id', '?')} ({current.get('timestamp', '')})")
        console.print(f"  Baseline: {baseline.get('run_id', '?')} ({baseline.get('timestamp', '')})")
        console.print(table)

    return capture.get()


def format_baseline_markdown(current: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Format current vs baseline as markdown."""
    current_results = {r["agent_name"]: r for r in current.get("results", [])}
    baseline_results = {r["agent_name"]: r for r in baseline.get("results", [])}
    all_agents = sorted(set(current_results) | set(baseline_results))

    lines = [
        f"# Benchmark Comparison",
        f"",
        f"**Current:** {current.get('run_id', '?')} ({current.get('timestamp', '')})",
        f"**Baseline:** {baseline.get('run_id', '?')} ({baseline.get('timestamp', '')})",
        f"",
        f"| Agent | Score (now) | Score (base) | Delta | Cost (now) | Cost (base) |",
        f"|-------|-------------|--------------|-------|------------|-------------|",
    ]

    for agent in all_agents:
        cur = current_results.get(agent, {})
        bas = baseline_results.get(agent, {})
        cur_score = cur.get("quality_score", 0)
        bas_score = bas.get("quality_score", 0)
        delta = cur_score - bas_score
        delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
        lines.append(
            f"| {agent} | {cur.get('quality_grade', '?')} ({cur_score:.0f}) "
            f"| {bas.get('quality_grade', '?')} ({bas_score:.0f}) "
            f"| {delta_str} | ${cur.get('cost', 0):.2f} | ${bas.get('cost', 0):.2f} |"
        )

    return "\n".join(lines)


def format_compare(run_a: dict[str, Any], run_b: dict[str, Any]) -> str:
    """Compare two runs side by side."""
    return format_baseline_table(run_a, run_b)


def format_csv(run_data: dict[str, Any]) -> str:
    """Format run data as CSV."""
    results = run_data.get("results", [])
    run_id = run_data.get("run_id", "")
    timestamp = run_data.get("timestamp", "")
    task = run_data.get("task", "")

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "run_id", "timestamp", "task", "agent_name", "model",
        "duration_seconds", "cost", "tokens_in", "tokens_out",
        "files_changed", "lines_added", "lines_removed",
        "test_pass", "test_total", "lint_errors", "lint_warnings",
        "quality_score", "quality_grade",
    ]
    writer.writerow(headers)

    for r in results:
        writer.writerow([
            run_id, timestamp, task,
            r.get("agent_name", ""), r.get("model", ""),
            r.get("duration_seconds", 0), r.get("cost", 0),
            r.get("tokens_in", 0), r.get("tokens_out", 0),
            r.get("files_changed", 0), r.get("lines_added", 0), r.get("lines_removed", 0),
            r.get("test_pass", 0), r.get("test_total", 0),
            r.get("lint_errors", 0), r.get("lint_warnings", 0),
            r.get("quality_score", 0), r.get("quality_grade", ""),
        ])

    return output.getvalue()


# Scoring breakdown constants
BREAKDOWN_FACTORS = [
    ("test_pass_rate", 30),
    ("lint_clean", 14),
    ("diff_sensibility", 13),
    ("task_completion", 13),
    ("speed_bonus", 10),
    ("import_hygiene", 10),
    ("complexity", 10),
]


def _compute_breakdown(r: dict[str, Any]) -> dict[str, float]:
    """Compute individual scoring factor points for a result."""
    from .scorer import _count_import_issues, _count_unused_imports, compute_complexity_score

    breakdown = {}

    # test_pass_rate: 30 pts
    test_total = r.get("test_total", 0)
    test_pass = r.get("test_pass", 0)
    if test_total > 0:
        breakdown["test_pass_rate"] = (test_pass / test_total) * 30
    else:
        breakdown["test_pass_rate"] = 15

    # lint_clean: 14 pts
    lint_errors = r.get("lint_errors", 0)
    lint_warnings = r.get("lint_warnings", 0)
    if lint_errors == 0 and lint_warnings == 0:
        breakdown["lint_clean"] = 14
    elif lint_errors == 0:
        breakdown["lint_clean"] = 7
    else:
        breakdown["lint_clean"] = max(0, 14 - lint_errors * 3)

    # diff_sensibility: 13 pts
    total_changes = r.get("lines_added", 0) + r.get("lines_removed", 0)
    if total_changes == 0:
        breakdown["diff_sensibility"] = 0
    elif total_changes <= 5:
        breakdown["diff_sensibility"] = 7
    elif total_changes <= 50:
        breakdown["diff_sensibility"] = 13
    elif total_changes <= 200:
        breakdown["diff_sensibility"] = 9
    else:
        breakdown["diff_sensibility"] = 4

    # task_completion: 13 pts
    breakdown["task_completion"] = 13 if r.get("exit_code") == 0 else 2

    # speed_bonus: 10 pts
    duration = r.get("duration_seconds", 0)
    if duration <= 30:
        breakdown["speed_bonus"] = 10
    elif duration <= 120:
        breakdown["speed_bonus"] = 8
    elif duration <= 300:
        breakdown["speed_bonus"] = 5
    elif duration <= 600:
        breakdown["speed_bonus"] = 3
    else:
        breakdown["speed_bonus"] = 0

    # import_hygiene: 10 pts
    stdout = r.get("stdout", "")
    stderr = r.get("stderr", "")
    import_issues = _count_import_issues(stdout, stderr)
    unused = _count_unused_imports(stdout)
    total_imp = import_issues + unused
    if total_imp == 0:
        breakdown["import_hygiene"] = 10
    elif total_imp <= 2:
        breakdown["import_hygiene"] = 6
    elif total_imp <= 5:
        breakdown["import_hygiene"] = 3
    else:
        breakdown["import_hygiene"] = 0

    # complexity: 10 pts
    complexity = compute_complexity_score(stdout)
    breakdown["complexity"] = complexity * 0.10

    return breakdown


def format_breakdown_table(run_data: dict[str, Any]) -> str:
    """Format scoring breakdown as a sub-table."""
    console = Console(width=100)
    results = run_data.get("results", [])
    if not results:
        return "No results to display."

    sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)

    output = format_table(run_data)
    output += "\n\n"

    for r in sorted_results:
        name = r.get("agent_name", "?")
        score = r.get("quality_score", 0)
        bd = _compute_breakdown(r)

        table = Table(title=f"Scoring Breakdown: {name} ({score:.0f}/100)", show_lines=True)
        table.add_column("Factor", style="bold")
        table.add_column("Points", justify="right")
        table.add_column("Max", justify="right")

        for factor, max_pts in BREAKDOWN_FACTORS:
            pts = bd.get(factor, 0)
            table.add_row(factor.replace("_", " ").title(), f"{pts:.1f}", str(max_pts))

        with console.capture() as capture:
            console.print(table)
        output += capture.get() + "\n"

    return output


def format_breakdown_markdown(run_data: dict[str, Any]) -> str:
    """Format scoring breakdown as markdown."""
    results = run_data.get("results", [])
    if not results:
        return "No results to display."

    sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)
    lines = [f"# Scoring Breakdown\n"]

    for r in sorted_results:
        name = r.get("agent_name", "?")
        score = r.get("quality_score", 0)
        bd = _compute_breakdown(r)
        lines.append(f"## {name} ({score:.0f}/100)\n")
        lines.append("| Factor | Points | Max |")
        lines.append("|--------|--------|-----|")
        for factor, max_pts in BREAKDOWN_FACTORS:
            pts = bd.get(factor, 0)
            lines.append(f"| {factor.replace('_', ' ').title()} | {pts:.1f} | {max_pts} |")
        lines.append("")

    return "\n".join(lines)


def format_leaderboard_table(leaderboard: list[dict]) -> str:
    """Format leaderboard as a Rich table."""
    console = Console(width=80)
    if not leaderboard:
        return "No benchmark runs found."

    table = Table(title="Leaderboard", show_lines=True)
    table.add_column("Rank", justify="right", style="bold")
    table.add_column("Agent", style="bold")
    table.add_column("Avg Score", justify="right")
    table.add_column("Best", justify="right")
    table.add_column("Runs", justify="right")
    table.add_column("Wins", justify="right")

    for i, entry in enumerate(leaderboard, 1):
        table.add_row(
            str(i),
            entry["agent"],
            f"{entry['avg_score']:.1f}",
            f"{entry['best_score']:.0f}",
            str(entry["total_runs"]),
            str(entry["wins"]),
        )

    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_leaderboard_markdown(leaderboard: list[dict]) -> str:
    """Format leaderboard as markdown."""
    if not leaderboard:
        return "No benchmark runs found."
    lines = ["# Leaderboard\n",
             "| Rank | Agent | Avg Score | Best | Runs | Wins |",
             "|------|-------|-----------|------|------|------|"]
    for i, e in enumerate(leaderboard, 1):
        lines.append(f"| {i} | {e['agent']} | {e['avg_score']:.1f} | {e['best_score']:.0f} | {e['total_runs']} | {e['wins']} |")
    return "\n".join(lines)


def format_leaderboard_json(leaderboard: list[dict]) -> str:
    """Format leaderboard as JSON."""
    return json.dumps(leaderboard, indent=2)
