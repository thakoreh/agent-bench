"""Generate self-contained HTML reports with inline charts."""

from __future__ import annotations

import html
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
    {comparison_html}

    <footer>Generated by agent-bench v0.2.0</footer>
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
