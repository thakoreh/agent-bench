"""Generate self-contained HTML reports with inline charts."""

from __future__ import annotations

import html
import math
from typing import Any


def _bar_svg(value: float, max_val: float, width: int = 200, height: int = 24, color: str = "#4CAF50") -> str:
    """Generate an inline SVG bar for a single value."""
    if max_val <= 0:
        max_val = 1
    ratio = min(value / max_val, 1.0)
    bar_w = int(width * ratio)
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="2" width="{width}" height="{height - 4}" fill="#e0e0e0" rx="4"/>'
        f'<rect x="0" y="2" width="{bar_w}" height="{height - 4}" fill="{color}" rx="4"/>'
        f'<text x="{width + 8}" y="{height - 6}" font-size="12" font-family="monospace">'
        f'{value:.1f}</text>'
        f'</svg>'
    )


def _radar_chart_svg(
    values: list[float],
    labels: list[str],
    size: int = 220,
    color: str = "#4CAF50",
    fill_opacity: float = 0.3,
) -> str:
    """Generate an SVG radar/spider chart for scoring breakdown."""
    n = len(values)
    if n < 3:
        return _fallback_bar_svg(values, labels, color)

    cx, cy = size / 2, size / 2
    radius = size / 2 - 35
    grid_rings = 4

    # Data polygon points
    points: list[str] = []
    for i in range(n):
        angle = (2 * math.pi * i / n) - math.pi / 2
        r = (values[i] / 100.0) * radius
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")

    # Grid rings
    grid_paths = ""
    for ring in range(1, grid_rings + 1):
        ring_r = (ring / grid_rings) * radius
        ring_points: list[str] = []
        for i in range(n):
            angle = (2 * math.pi * i / n) - math.pi / 2
            x = cx + ring_r * math.cos(angle)
            y = cy + ring_r * math.sin(angle)
            ring_points.append(f"{x:.1f},{y:.1f}")
        grid_paths += f'<polygon points="{" ".join(ring_points)}" fill="none" stroke="#ddd" stroke-width="0.5"/>'

    # Spokes
    spokes = ""
    label_elements = ""
    for i in range(n):
        angle = (2 * math.pi * i / n) - math.pi / 2
        x_end = cx + radius * math.cos(angle)
        y_end = cy + radius * math.sin(angle)
        spokes += f'<line x1="{cx}" y1="{cy}" x2="{x_end}" y2="{y_end}" stroke="#ddd" stroke-width="0.5"/>'

        label_r = radius + 20
        lx = cx + label_r * math.cos(angle)
        ly = cy + label_r * math.sin(angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        escaped_label = html.escape(labels[i])
        label_elements += (
            f'<text x="{lx}" y="{ly}" font-size="9" font-family="sans-serif" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{escaped_label}</text>'
        )

    polygon = (
        f'<polygon points="{" ".join(points)}" fill="{color}" '
        f'fill-opacity="{fill_opacity}" stroke="{color}" stroke-width="1.5"/>'
    )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'{grid_paths}{spokes}{polygon}{label_elements}'
        f'</svg>'
    )


def _fallback_bar_svg(
    values: list[float],
    labels: list[str],
    color: str = "#4CAF50",
) -> str:
    """Fallback horizontal bar chart for fewer than 3 dimensions."""
    if not values:
        return ""

    bar_height = 18
    gap = 6
    label_width = 100
    bar_width = 120
    total_height = len(values) * (bar_height + gap) + 10

    elements = ""
    for i, (val, label) in enumerate(zip(values, labels)):
        y = i * (bar_height + gap) + 5
        w = (val / 100.0) * bar_width
        escaped = html.escape(label)
        elements += (
            f'<text x="0" y="{y + 13}" font-size="11" font-family="sans-serif">{escaped}</text>'
            f'<rect x="{label_width}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#e0e0e0" rx="3"/>'
            f'<rect x="{label_width}" y="{y}" width="{w:.0f}" height="{bar_height}" fill="{color}" rx="3"/>'
            f'<text x="{label_width + bar_width + 5}" y="{y + 13}" font-size="10" font-family="monospace">{val:.0f}</text>'
        )

    total_width = label_width + bar_width + 40
    return (
        f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
        f'{elements}</svg>'
    )


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs:02d}s"


def _format_tokens(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


# Scoring breakdown factor labels for radar chart
RADAR_LABELS = [
    "Tests", "Lint", "Diff", "Completion", "Speed",
    "Imports", "Complexity", "Docstrings", "Types", "Comments", "Clean",
]

RADAR_KEYS = [
    "test_pass_rate", "lint_clean", "diff_sensibility", "task_completion",
    "speed_bonus", "import_hygiene", "complexity", "docstring_coverage",
    "type_hint_coverage", "comment_density", "code_cleanliness",
]


def _compute_radar_values(r: dict[str, Any]) -> list[float]:
    """Compute scoring breakdown as 0-100 values for radar chart."""
    import re as _re

    values: list[float] = []

    # Tests
    test_total = r.get("test_total", 0)
    test_pass = r.get("test_pass", 0)
    values.append((test_pass / test_total) * 100 if test_total > 0 else 50)

    # Lint
    lint_errors = r.get("lint_errors", 0)
    lint_warnings = r.get("lint_warnings", 0)
    if lint_errors == 0 and lint_warnings == 0:
        values.append(100)
    elif lint_errors == 0:
        values.append(50)
    else:
        values.append(max(0, 100 - lint_errors * 20))

    # Diff
    total_changes = r.get("lines_added", 0) + r.get("lines_removed", 0)
    if total_changes == 0:
        values.append(0)
    elif total_changes <= 50:
        values.append(100)
    elif total_changes <= 200:
        values.append(60)
    else:
        values.append(30)

    # Completion
    values.append(100 if r.get("exit_code") == 0 else 15)

    # Speed
    duration = r.get("duration_seconds", 0)
    if duration <= 30:
        values.append(100)
    elif duration <= 120:
        values.append(75)
    elif duration <= 300:
        values.append(50)
    elif duration <= 600:
        values.append(25)
    else:
        values.append(0)

    # Imports
    stdout = r.get("stdout", "")
    stderr = r.get("stderr", "")
    imp_issues = len(_re.findall(r"ImportError|ModuleNotFoundError", f"{stdout}\n{stderr}"))
    imp_issues += len(_re.findall(r"from \S+ import \*", stdout))
    imp_issues += len(_re.findall(r"F401|unused import", stdout))
    if imp_issues == 0:
        values.append(100)
    elif imp_issues <= 2:
        values.append(60)
    elif imp_issues <= 5:
        values.append(30)
    else:
        values.append(0)

    # Complexity (approximate - use simple heuristic)
    values.append(70)  # neutral default without radon

    # Docstrings (approximate)
    doc_match = len(_re.findall(r'"""', stdout))
    if doc_match >= 2:
        values.append(80)
    elif doc_match > 0:
        values.append(50)
    else:
        values.append(20)

    # Type hints (approximate)
    type_match = len(_re.findall(r"def \w+\([^)]*:\s*\w+", stdout))
    if type_match > 0:
        values.append(75)
    else:
        values.append(30)

    # Comments
    comment_lines = len(_re.findall(r"^\s*#", stdout, _re.MULTILINE))
    code_lines = max(len(stdout.splitlines()), 1)
    density = comment_lines / code_lines
    if 0.1 <= density <= 0.3:
        values.append(100)
    elif density < 0.1:
        values.append(density * 300)
    else:
        values.append(max(0, 100 - (density - 0.3) * 200))

    # Cleanliness
    combined = f"{stdout}\n{stderr}"
    crashes = len(_re.findall(r"Traceback|SyntaxError|RuntimeError|segfault|core dumped", combined, _re.I))
    if crashes == 0:
        values.append(100)
    elif crashes <= 2:
        values.append(40)
    else:
        values.append(0)

    return values


def generate_html(run_data: dict[str, Any], comparison_data: dict[str, Any] | None = None) -> str:
    """Generate a self-contained HTML report."""
    task = html.escape(run_data.get("task", "Unknown"))
    timestamp = html.escape(run_data.get("timestamp", ""))
    run_id = html.escape(run_data.get("run_id", "?"))
    results = run_data.get("results", [])

    if not results:
        return "<html><body><h1>No results to display.</h1></body></html>"

    sorted_results = sorted(results, key=lambda r: r.get("quality_score", 0), reverse=True)

    max_score = max(r.get("quality_score", 0) for r in sorted_results) or 100
    max_cost = max(r.get("cost", 0) for r in sorted_results) or 1
    max_duration = max(r.get("duration_seconds", 0) for r in sorted_results) or 1

    # Build table rows
    table_rows = ""
    for r in sorted_results:
        name = html.escape(r.get("agent_name", "?"))
        duration = _format_duration(r.get("duration_seconds", 0))
        cost = f"${r.get('cost', 0):.2f}"
        tokens_in = _format_tokens(r.get("tokens_in", 0))
        tokens_out = _format_tokens(r.get("tokens_out", 0))
        tests = f"{r.get('test_pass', 0)}/{r.get('test_total', 0)}"
        score = r.get("quality_score", 0)
        grade = r.get("quality_grade", "?")

        score_bar = _bar_svg(score, 100, color="#4CAF50")
        cost_bar = _bar_svg(r.get("cost", 0), max_cost, color="#FF9800")
        duration_bar = _bar_svg(r.get("duration_seconds", 0), max_duration, color="#2196F3")

        table_rows += f"""
        <tr>
            <td class="agent-name">{name}</td>
            <td>{grade} ({score:.0f}/100)</td>
            <td>{score_bar}</td>
            <td>{cost}</td>
            <td>{cost_bar}</td>
            <td>{duration}</td>
            <td>{duration_bar}</td>
            <td>{tokens_in} → {tokens_out}</td>
            <td>{tests}</td>
        </tr>"""

    # Winner info
    best = sorted_results[0]
    fastest = min(results, key=lambda r: r.get("duration_seconds", float("inf")))
    cheapest = min(results, key=lambda r: r.get("cost", float("inf")))

    winner_html = f"""
    <div class="winners">
        <div class="winner-card">
            <span class="winner-label">🏆 Winner</span>
            <span class="winner-value">{html.escape(best['agent_name'])} ({best.get('quality_grade', '?')})</span>
        </div>
        <div class="winner-card">
            <span class="winner-label">⚡ Fastest</span>
            <span class="winner-value">{html.escape(fastest['agent_name'])} ({_format_duration(fastest.get('duration_seconds', 0))})</span>
        </div>
        <div class="winner-card">
            <span class="winner-label">💰 Cheapest</span>
            <span class="winner-value">{html.escape(cheapest['agent_name'])} (${cheapest.get('cost', 0):.2f})</span>
        </div>
    </div>"""

    # Radar charts section
    radar_section = ""
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#F44336"]
    for i, r in enumerate(sorted_results[:5]):
        name = html.escape(r.get("agent_name", "?"))
        score = r.get("quality_score", 0)
        values = _compute_radar_values(r)
        color = colors[i % len(colors)]
        chart = _radar_chart_svg(values, RADAR_LABELS, size=240, color=color)
        radar_section += f"""
        <div class="radar-card">
            <h3>{name} — {score:.0f}/100</h3>
            {chart}
        </div>"""

    radar_html = f"""
    <div class="radar-section">
        <h2>Scoring Breakdown</h2>
        <div class="radar-grid">
            {radar_section}
        </div>
    </div>"""

    # Comparison section
    comparison_html = ""
    if comparison_data:
        comparison_html = _build_comparison_section(run_data, comparison_data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Benchmark Report — {run_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        h2 {{ font-size: 1.4rem; margin-bottom: 1rem; color: #1a1a2e; }}
        .meta {{ color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }}
        .meta span {{ margin-right: 1.5rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th {{
            background: #1a1a2e;
            color: white;
            padding: 12px 16px;
            text-align: left;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }}
        tr:hover {{ background: #f9f9f9; }}
        .agent-name {{ font-weight: 600; font-size: 1rem; }}
        .winners {{
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }}
        .winner-card {{
            flex: 1;
            min-width: 200px;
            background: white;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .winner-label {{
            display: block;
            font-size: 0.8rem;
            color: #888;
            margin-bottom: 0.3rem;
        }}
        .winner-value {{
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .radar-section {{
            margin-top: 2rem;
        }}
        .radar-section h2 {{ margin-bottom: 1rem; }}
        .radar-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}
        .radar-card {{
            background: white;
            border-radius: 8px;
            padding: 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
            min-width: 260px;
        }}
        .radar-card h3 {{
            font-size: 1rem;
            margin-bottom: 0.8rem;
            color: #333;
        }}
        .comparison {{
            margin-top: 2rem;
        }}
        .comparison h2 {{ margin-bottom: 1rem; font-size: 1.3rem; }}
        .comparison table {{ margin-top: 0.5rem; }}
        .delta-pos {{ color: #4CAF50; font-weight: 600; }}
        .delta-neg {{ color: #f44336; font-weight: 600; }}
        footer {{
            margin-top: 2rem;
            text-align: center;
            color: #aaa;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <h1>Agent Benchmark Results</h1>
    <div class="meta">
        <span>📋 Task: <strong>{task}</strong></span>
        <span>🆔 Run: <code>{run_id}</code></span>
        <span>🕐 {timestamp}</span>
    </div>

    <table>
        <thead>
            <tr>
                <th>Agent</th>
                <th>Grade</th>
                <th>Quality Score</th>
                <th>Cost</th>
                <th>Cost Bar</th>
                <th>Time</th>
                <th>Time Bar</th>
                <th>Tokens</th>
                <th>Tests</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>

    {winner_html}

    {radar_html}

    {comparison_html}

    <footer>Generated by agent-bench v0.6.0</footer>
</body>
</html>"""


def _build_comparison_section(current: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Build HTML section comparing current vs baseline."""
    current_results = {r["agent_name"]: r for r in current.get("results", [])}
    baseline_results = {r["agent_name"]: r for r in baseline.get("results", [])}
    all_agents = sorted(set(current_results) | set(baseline_results))

    rows = ""
    for agent in all_agents:
        cur = current_results.get(agent, {})
        bas = baseline_results.get(agent, {})
        cur_score = cur.get("quality_score", 0)
        bas_score = bas.get("quality_score", 0)
        delta = cur_score - bas_score
        delta_cls = "delta-pos" if delta > 0 else "delta-neg" if delta < 0 else ""
        delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"

        rows += f"""
        <tr>
            <td class="agent-name">{html.escape(agent)}</td>
            <td>{cur.get('quality_grade', '?')} ({cur_score:.0f})</td>
            <td>{bas.get('quality_grade', '?')} ({bas_score:.0f})</td>
            <td class="{delta_cls}">{delta_str}</td>
            <td>${cur.get('cost', 0):.2f}</td>
            <td>${bas.get('cost', 0):.2f}</td>
        </tr>"""

    cur_id = html.escape(current.get("run_id", "?"))
    bas_id = html.escape(baseline.get("run_id", "?"))

    return f"""
    <div class="comparison">
        <h2>Comparison: Current vs Baseline</h2>
        <div class="meta">
            <span>Current: <code>{cur_id}</code></span>
            <span>Baseline: <code>{bas_id}</code></span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Score (now)</th>
                    <th>Score (base)</th>
                    <th>Delta</th>
                    <th>Cost (now)</th>
                    <th>Cost (base)</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""
