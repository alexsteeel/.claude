"""CLI definition with typer."""

from pathlib import Path
from typing import List, Optional

import typer

app = typer.Typer(
    help="Ralph - Autonomous task execution CLI",
    no_args_is_help=True,
)


@app.command()
def plan(
    project: str = typer.Argument(..., help="Project name"),
    tasks: List[str] = typer.Argument(..., help="Task numbers or ranges (e.g., 1-4 6 8-10)"),
    working_dir: Optional[Path] = typer.Option(
        None, "-w", "--working-dir", help="Working directory"
    ),
):
    """Interactive task planning with human feedback."""
    from .commands.plan import run_plan

    raise typer.Exit(run_plan(project, tasks, working_dir))


@app.command()
def implement(
    project: str = typer.Argument(..., help="Project name"),
    tasks: List[str] = typer.Argument(..., help="Task numbers or ranges (e.g., 1-4 6 8-10)"),
    working_dir: Optional[Path] = typer.Option(
        None, "-w", "--working-dir", help="Working directory"
    ),
    max_budget: Optional[float] = typer.Option(
        None, "--max-budget", help="Maximum budget in USD per task"
    ),
    no_recovery: bool = typer.Option(
        False, "--no-recovery", help="Disable automatic recovery"
    ),
):
    """Autonomous implementation with recovery and notifications."""
    from .commands.implement import run_implement

    raise typer.Exit(run_implement(project, tasks, working_dir, max_budget, no_recovery))


@app.command()
def review(
    task_ref: str = typer.Argument(..., help="Task reference (e.g., project#1)"),
):
    """Run code reviews in isolated contexts."""
    from .commands.review import run_review

    raise typer.Exit(run_review(task_ref))


@app.command()
def health(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed output"),
):
    """Check API health status."""
    from .commands.health import run_health

    raise typer.Exit(run_health(verbose))


def main():
    """Entry point."""
    app()
