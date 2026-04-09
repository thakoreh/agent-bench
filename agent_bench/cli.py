"""CLI for agent-bench."""

from __future__ import annotations

import click

from . import __version__
from .config import Config
from .detector import detect_all, detect_from_config
from .reporter import format_history, format_json, format_table, format_markdown, format_baseline_table, format_baseline_markdown, format_compare, format_csv, format_breakdown_table, format_breakdown_markdown, format_leaderboard_table, format_leaderboard_markdown, format_leaderboard_json
from .web_reporter import generate_html
from .runner import AgentRunner
from .storage import Storage


@click.group()
@click.version_option(__version__, prog_name="agent-bench")
def cli() -> None:
    """Benchmark AI coding agents against each other on the same task."""
    pass


@cli.command()
@click.option("--path", default=".agent-bench.yaml", help="Config file path")
def init(path: str) -> None:
    """Create a .agent-bench.yaml config file."""
    from pathlib import Path

    target = Path(path)
    if target.exists():
        click.echo(f"Config already exists: {target}")
        return

    config = Config()
    saved = config.save(target)
    click.echo(f"Created config: {saved}")


@cli.command()
@click.option("--agent", "-a", "agents", help="Comma-separated agent names to run")
@click.option("--task", "-t", help="Task prompt (overrides config default)")
@click.option("--workdir", "-w", type=click.Path(exists=True), help="Working directory")
@click.option("--parallel", "-p", is_flag=True, help="Run agents in parallel")
@click.option("--model", "-m", "models", help="Comma-separated models to test (adds --model to each agent)")
def run(agents: str | None, task: str | None, workdir: str | None, parallel: bool, models: str | None) -> None:
    """Run agents on a task and compare results."""
    from pathlib import Path

    config = Config()
    agent_list = agents.split(",") if agents else None
    model_list = models.split(",") if models else None
    wd = Path(workdir) if workdir else None

    runner = AgentRunner(config)
    result = runner.run_all(task=task, agents=agent_list, workdir=wd, parallel=parallel, models=model_list)

    click.echo(format_table(result))


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--run-id", help="Specific run ID to show")
@click.option("--baseline", help="Baseline run ID to compare against")
@click.option("--compare", nargs=2, type=str, help="Compare two run IDs side by side")
@click.option("--markdown", is_flag=True, help="Output as markdown")
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--breakdown", is_flag=True, help="Show scoring breakdown")
@click.option("--sort-by", type=click.Choice(["quality", "cost-efficiency"]), default="quality", help="Sort results")
@click.option("--html", "as_html", is_flag=True, help="Output as HTML report")
@click.option("--output", "-o", default=None, help="Output file path (for --html, --csv)")
def results(as_json: bool, run_id: str | None, baseline: str | None, compare: tuple[str, str] | None, markdown: bool, as_csv: bool, breakdown: bool, sort_by: str, as_html: bool, output: str | None) -> None:
    """Show benchmark results."""
    storage = Storage()

    if compare:
        data_a = storage.get_run(compare[0])
        data_b = storage.get_run(compare[1])
        if not data_a or not data_b:
            click.echo(f"Run not found: {compare[0] if not data_a else compare[1]}")
            return
        click.echo(format_compare(data_a, data_b))
        return

    if run_id:
        data = storage.get_run(run_id)
    else:
        data = storage.get_latest_run()

    if not data:
        click.echo("No results found. Run 'agent-bench run' first.")
        return

    if baseline:
        baseline_data = storage.get_run(baseline)
        if baseline_data:
            if as_html:
                html_content = generate_html(data, baseline_data)
                if output:
                    from pathlib import Path
                    Path(output).write_text(html_content)
                    click.echo(f"HTML report saved to {output}")
                else:
                    click.echo(html_content)
            elif as_json:
                click.echo(format_json({"current": data, "baseline": baseline_data}))
            elif markdown:
                click.echo(format_baseline_markdown(data, baseline_data))
            else:
                click.echo(format_baseline_table(data, baseline_data))
            return

    if as_csv:
        csv_content = format_csv(data)
        if output:
            from pathlib import Path
            Path(output).write_text(csv_content)
            click.echo(f"CSV saved to {output}")
        else:
            click.echo(csv_content)
    elif breakdown:
        if markdown:
            click.echo(format_breakdown_markdown(data))
        else:
            click.echo(format_breakdown_table(data))
    elif as_html:
        html_content = generate_html(data)
        if output:
            from pathlib import Path
            Path(output).write_text(html_content)
            click.echo(f"HTML report saved to {output}")
        else:
            click.echo(html_content)
    elif as_json:
        click.echo(format_json(data))
    elif markdown:
        click.echo(format_markdown(data))
    else:
        click.echo(format_table(data, sort_by=sort_by))


@cli.command()
@click.option("--html", "as_html", is_flag=True, help="Output as HTML report")
@click.option("--output", "-o", default=None, help="Output file path (for --html)")
def report(as_html: bool, output: str | None) -> None:
    """Generate a report from the latest benchmark run."""
    storage = Storage()
    data = storage.get_latest_run()

    if not data:
        click.echo("No results found. Run 'agent-bench run' first.")
        return

    if as_html:
        html_content = generate_html(data)
        if output:
            from pathlib import Path
            Path(output).write_text(html_content)
            click.echo(f"HTML report saved to {output}")
        else:
            click.echo(html_content)
    else:
        click.echo(format_table(data))


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of runs to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def history(limit: int, as_json: bool) -> None:
    """Show past benchmark runs."""
    storage = Storage()
    runs = storage.list_runs(limit=limit)
    if as_json:
        import json as _json
        click.echo(_json.dumps(runs, indent=2))
    else:
        click.echo(format_history(runs))


@cli.command()
def agents() -> None:
    """List detected/available agents."""
    from rich.console import Console

    console = Console()
    detected = detect_all()

    console.print("\n[bold]Detected Agents:[/bold]\n")
    for info in detected:
        if info.installed:
            console.print(f"  ✅ {info}")
        else:
            console.print(f"  ❌ {info}")

    installed = sum(1 for d in detected if d.installed)
    console.print(f"\n  {installed}/{len(detected)} agents available\n")


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of agents to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--markdown", is_flag=True, help="Output as markdown")
def leaderboard(limit: int, as_json: bool, markdown: bool) -> None:
    """Show aggregated leaderboard across all runs."""
    storage = Storage()
    lb = _compute_leaderboard(storage, limit)
    if as_json:
        click.echo(format_leaderboard_json(lb))
    elif markdown:
        click.echo(format_leaderboard_markdown(lb))
    else:
        click.echo(format_leaderboard_table(lb))
    storage.close()


def _compute_leaderboard(storage: Storage, limit: int) -> list[dict]:
    """Compute leaderboard data from storage."""
    from collections import defaultdict
    runs = storage.list_runs(limit=1000)
    agent_stats: dict[str, dict] = defaultdict(lambda: {"scores": [], "runs": 0, "wins": 0})

    for run_info in runs:
        run_data = storage.get_run(run_info["run_id"])
        if not run_data or not run_data.get("results"):
            continue
        best_score = max(r.get("quality_score", 0) for r in run_data["results"])
        for r in run_data["results"]:
            name = r.get("agent_name", "?")
            score = r.get("quality_score", 0)
            agent_stats[name]["scores"].append(score)
            agent_stats[name]["runs"] += 1
            if score == best_score:
                agent_stats[name]["wins"] += 1

    leaderboard = []
    for name, stats in agent_stats.items():
        scores = stats["scores"]
        leaderboard.append({
            "agent": name,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "best_score": max(scores) if scores else 0,
            "total_runs": stats["runs"],
            "wins": stats["wins"],
        })
    leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
    return leaderboard[:limit]


@cli.command(name="delete")
@click.argument("run_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def delete_run(run_id: str, force: bool) -> None:
    """Delete a benchmark run by ID."""
    storage = Storage()
    data = storage.get_run(run_id)

    if not data:
        click.echo(f"Run '{run_id}' not found.")
        storage.close()
        return

    if not force:
        click.echo(f"About to delete run '{run_id}' ({data.get('task', '?')[:50]})")
        if not click.confirm("Proceed?"):
            click.echo("Cancelled.")
            storage.close()
            return

    storage.delete_run(run_id)
    click.echo(f"Deleted run '{run_id}'.")
    storage.close()


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of recent runs to analyze")
@click.option("--agent", "-a", default=None, help="Filter by agent name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def trend(limit: int, agent: str | None, as_json: bool) -> None:
    """Show quality score trend across recent runs."""
    storage = Storage()
    runs = storage.list_runs(limit=limit)

    if not runs:
        click.echo("No benchmark runs found.")
        storage.close()
        return

    # Collect scores per agent across runs
    from collections import defaultdict
    agent_scores: dict[str, list[tuple[str, float, str]]] = defaultdict(list)

    for run_info in reversed(runs):  # chronological order
        run_data = storage.get_run(run_info["run_id"])
        if not run_data:
            continue
        for r in run_data.get("results", []):
            name = r.get("agent_name", "?")
            if agent and name != agent:
                continue
            score = r.get("quality_score", 0)
            grade = r.get("quality_grade", "?")
            agent_scores[name].append((run_info["run_id"], score, grade))

    if not agent_scores:
        click.echo("No results found for the given filters.")
        storage.close()
        return

    if as_json:
        import json
        output = {}
        for name, entries in agent_scores.items():
            output[name] = [
                {"run_id": rid, "score": score, "grade": grade}
                for rid, score, grade in entries
            ]
        click.echo(json.dumps(output, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()
        table = Table(
            title="Quality Score Trend",
            box=box.ROUNDED,
            title_style="bold cyan",
        )
        table.add_column("Agent", style="bold")
        table.add_column("Runs", justify="right")
        table.add_column("Avg Score", justify="right")
        table.add_column("Trend", justify="center")
        table.add_column("Best", justify="right")
        table.add_column("Worst", justify="right")

        for name, entries in sorted(agent_scores.items()):
            scores = [e[1] for e in entries]
            avg = sum(scores) / len(scores)
            best = max(scores)
            worst = min(scores)

            # Simple trend: compare last 3 avg to first 3 avg
            if len(scores) >= 3:
                recent = sum(scores[-3:]) / 3
                early = sum(scores[:3]) / 3
                delta = recent - early
                if delta > 5:
                    trend_str = "[green]↑ improving[/green]"
                elif delta < -5:
                    trend_str = "[red]↓ declining[/red]"
                else:
                    trend_str = "[yellow]→ stable[/yellow]"
            elif len(scores) >= 2:
                delta = scores[-1] - scores[0]
                if delta > 5:
                    trend_str = "[green]↑[/green]"
                elif delta < -5:
                    trend_str = "[red]↓[/red]"
                else:
                    trend_str = "[yellow]→[/yellow]"
            else:
                trend_str = "—"

            table.add_row(
                name,
                str(len(entries)),
                f"{avg:.1f}",
                trend_str,
                f"{best:.0f}",
                f"{worst:.0f}",
            )

        console.print(table)

    storage.close()


if __name__ == "__main__":
    cli()
