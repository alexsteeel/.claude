"""CLI definition with typer."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from .commands.logs import LogType, complete_log_files

app = typer.Typer(
    help="Ralph - Autonomous task execution CLI",
    no_args_is_help=True,
)

# Logs sub-application
logs_app = typer.Typer(help="View and manage log files")
app.add_typer(logs_app, name="logs")


@app.command()
def plan(
    project: str = typer.Argument(..., help="Project name"),
    tasks: list[str] = typer.Argument(..., help="Task numbers or ranges (e.g., 1-4 6 8-10)"),
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
    tasks: list[str] = typer.Argument(..., help="Task numbers or ranges (e.g., 1-4 6 8-10)"),
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


# ============================================================================
# Logs subcommands
# ============================================================================


@logs_app.callback(invoke_without_command=True)
def logs_list(
    ctx: typer.Context,
    log_type: Annotated[
        Optional[LogType],
        typer.Option(
            "-t", "--type",
            help="Filter by log type",
        ),
    ] = None,
    task: Annotated[
        Optional[str],
        typer.Option(
            "--task",
            help="Filter by task reference (e.g., project#1)",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "-n", "--limit",
            help="Maximum number of logs to show",
        ),
    ] = 20,
):
    """List recent log files."""
    # Only run if no subcommand was invoked
    if ctx.invoked_subcommand is None:
        from .commands.logs import list_logs

        raise typer.Exit(list_logs(log_type, task, limit))


@logs_app.command("view")
def logs_view(
    path: Annotated[
        str,
        typer.Argument(
            help="Log file path or name",
            autocompletion=complete_log_files,
        ),
    ],
    lines: Annotated[
        Optional[int],
        typer.Option(
            "-n", "--lines",
            help="Number of lines to show",
        ),
    ] = None,
    head: Annotated[
        bool,
        typer.Option(
            "--head",
            help="Show first N lines instead of last",
        ),
    ] = False,
    pager: Annotated[
        bool,
        typer.Option(
            "--pager",
            help="Force use of pager (less)",
        ),
    ] = False,
    no_pager: Annotated[
        bool,
        typer.Option(
            "--no-pager",
            help="Disable pager, output directly",
        ),
    ] = False,
    vim: Annotated[
        bool,
        typer.Option(
            "--vim", "-v",
            help="Open in vim",
        ),
    ] = False,
    editor: Annotated[
        bool,
        typer.Option(
            "--editor", "-e",
            help="Open in $EDITOR",
        ),
    ] = False,
):
    """View log file contents with syntax highlighting.

    By default, uses pager for files > 50KB.
    Use --vim or --editor to open in external editor.
    """
    from .commands.logs import view_log

    # Determine pager mode: None=auto, True=force, False=disable
    use_pager: Optional[bool] = None
    if pager:
        use_pager = True
    elif no_pager:
        use_pager = False

    raise typer.Exit(view_log(path, lines, head, use_pager, vim, editor))


@logs_app.command("tail")
def logs_tail(
    path: Annotated[
        str,
        typer.Argument(
            help="Log file path or name",
            autocompletion=complete_log_files,
        ),
    ],
    lines: Annotated[
        int,
        typer.Option(
            "-n", "--lines",
            help="Initial number of lines to show",
        ),
    ] = 50,
):
    """Tail log file in real-time (like tail -f)."""
    from .commands.logs import tail_log

    raise typer.Exit(tail_log(path, lines))


@logs_app.command("clean")
def logs_clean(
    log_type: Annotated[
        Optional[LogType],
        typer.Option(
            "-t", "--type",
            help="Filter by log type",
        ),
    ] = None,
    days: Annotated[
        int,
        typer.Option(
            "--days",
            help="Delete logs older than this many days",
        ),
    ] = 30,
    no_dry_run: Annotated[
        bool,
        typer.Option(
            "--no-dry-run",
            help="Actually delete files (default is dry-run)",
        ),
    ] = False,
):
    """Clean old log files."""
    from .commands.logs import clean_logs

    raise typer.Exit(clean_logs(log_type, days, dry_run=not no_dry_run))


def main():
    """Entry point."""
    app()
