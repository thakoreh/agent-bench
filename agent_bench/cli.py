"""CLI for agent-bench."""

from __future__ import annotations

import click

from . import __version__
from .config import Config
from .detector import detect_all, detect_from_config
from .reporter import format_history, format_json, format_table, format_markdown, format_baseline_table, format_baseline_markdown, format_compare
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
def run(agents: str | None, task: str | None, workdir: str | None) -> None:
    """Run agents on a task and compare results."""
    from pathlib import Path

    config = Config()
    agent_list = agents.split(",") if agents else None
    wd = Path(workdir) if workdir else None

    runner = AgentRunner(config)
    result = runner.run_all(task=task, agents=agent_list, workdir=wd)

    click.echo(format_table(result))


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--run-id", help="Specific run ID to show")
@click.option("--baseline", help="Baseline run ID to compare against")
@click.option("--compare", nargs=2, type=str, help="Compare two run IDs side by side")
@click.option("--markdown", is_flag=True, help="Output as markdown")
@click.option("--html", "as_html", is_flag=True, help="Output as HTML report")
@click.option("--output", "-o", default=None, help="Output file path (for --html)")
def results(as_json: bool, run_id: str | None, baseline: str | None, compare: tuple[str, str] | None, markdown: bool, as_html: bool, output: str | None) -> None:
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

    if as_html:
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
        click.echo(format_table(data))


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
def history(limit: int) -> None:
    """Show past benchmark runs."""
    storage = Storage()
    runs = storage.list_runs(limit=limit)
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


if __name__ == "__main__":
    cli()
