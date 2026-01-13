"""Plan command - interactive task planning."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import get_settings
from ..executor import expand_task_ranges
from ..git import cleanup_working_dir
from ..logging import SessionLog, format_duration

console = Console()


def run_plan(
    project: str,
    task_args: list[str],
    working_dir: Optional[Path] = None,
) -> int:
    """Run interactive planning for tasks."""
    settings = get_settings()
    tasks = expand_task_ranges(task_args)

    if not tasks:
        console.print("[red]No valid task numbers provided[/red]")
        return 1

    if working_dir is None:
        working_dir = Path.cwd()

    # Setup logging
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = settings.log_dir / "ralph-plan"
    log_dir.mkdir(parents=True, exist_ok=True)
    session_log = SessionLog(log_dir / f"session_{ts}.log")

    session_log.write_header(
        "RALPH PLANNING SESSION",
        Project=project,
        Tasks=", ".join(str(t) for t in tasks),
        WorkingDir=str(working_dir),
    )

    console.rule(f"[bold blue]Ralph Planning: {project}[/bold blue]")
    console.print(f"Tasks: [green]{', '.join(str(t) for t in tasks)}[/green]")
    console.print(f"Working directory: [green]{working_dir}[/green]")

    completed = []
    failed = []
    start_time = datetime.now()

    for task_num in tasks:
        task_ref = f"{project}#{task_num}"
        console.rule(f"[cyan]Planning: {task_ref}[/cyan]")
        session_log.append(f"Starting: {task_ref}")

        # Cleanup before task
        cleaned = cleanup_working_dir(working_dir)
        if cleaned:
            console.print(f"[dim]Cleaned {len(cleaned)} files[/dim]")
            session_log.append(f"Cleaned {len(cleaned)} files")

        # Run Claude interactively (no --print, with tty)
        cmd = [
            "claude",
            "-p",
            f"/ralph-plan-task {task_ref}",
            "--model",
            "opus",
            "--verbose",
        ]

        try:
            result = subprocess.run(cmd, cwd=working_dir)

            if result.returncode == 0:
                console.print(f"[green]✓ Completed: {task_ref}[/green]")
                session_log.append(f"Completed: {task_ref}")
                completed.append(task_num)
            else:
                console.print(f"[red]✗ Failed: {task_ref} (exit code {result.returncode})[/red]")
                session_log.append(f"Failed: {task_ref} (exit code {result.returncode})")
                failed.append(task_num)

        except KeyboardInterrupt:
            console.print("[yellow]Interrupted by user[/yellow]")
            session_log.append("Session interrupted by user")
            break
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            session_log.append(f"Error: {e}")
            failed.append(task_num)

    # Summary
    duration = format_duration(int((datetime.now() - start_time).total_seconds()))

    session_log.write_summary(
        Completed=[str(t) for t in completed],
        Failed=[str(t) for t in failed],
    )

    console.rule("[bold blue]Session Complete[/bold blue]")
    console.print(f"Duration: [green]{duration}[/green]")
    console.print(f"Completed: [green]{len(completed)}[/green]")
    console.print(f"Failed: [red]{len(failed)}[/red]")

    return 0 if not failed else 1
