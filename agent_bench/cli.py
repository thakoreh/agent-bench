"""CLI for agent-bench."""

from __future__ import annotations

import click

from . import __version__
from .config import Config
from .detector import detect_all, detect_from_config
from .reporter import format_history, format_json, format_table
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
def results(as_json: bool, run_id: str | None) -> None:
    """Show benchmark results."""
    storage = Storage()

    if run_id:
        data = storage.get_run(run_id)
    else:
        data = storage.get_latest_run()

    if not data:
        click.echo("No results found. Run 'agent-bench run' first.")
        return

    if as_json:
        click.echo(format_json(data))
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
