"""Plan command - interactive task planning."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..config import get_config
from ..executor import expand_task_ranges
from ..git import cleanup_working_dir
from ..logging import Console, SessionLog, format_duration, console
from ..notify import Notifier


def run_plan(
    project: str,
    task_args: List[str],
    working_dir: Optional[Path] = None,
) -> int:
    """Run interactive planning for tasks.

    Args:
        project: Project name
        task_args: Task numbers or ranges
        working_dir: Optional working directory

    Returns:
        Exit code (0 = success, 1 = any failures)
    """
    config = get_config()
    tasks = expand_task_ranges(task_args)

    if not tasks:
        console.error("No valid task numbers provided")
        return 1

    if working_dir is None:
        working_dir = Path.cwd()

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = config.log_dir / "ralph-plan"
    log_dir.mkdir(parents=True, exist_ok=True)
    session_log = SessionLog(log_dir / f"session_{timestamp}.log")

    session_log.write_header(
        "RALPH PLANNING SESSION",
        Project=project,
        Tasks=", ".join(str(t) for t in tasks),
        WorkingDir=str(working_dir),
    )

    console.header(f"Ralph Planning: {project}")
    console.kv("Tasks", ", ".join(str(t) for t in tasks))
    console.kv("Working directory", str(working_dir))

    completed = []
    failed = []
    start_time = datetime.now()

    for task_num in tasks:
        task_ref = f"{project}#{task_num}"
        console.subheader(f"Planning: {task_ref}")
        session_log.append(f"Starting: {task_ref}")

        # Cleanup before task
        cleaned = cleanup_working_dir(working_dir)
        if cleaned:
            console.dim(f"Cleaned {len(cleaned)} files")
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
            result = subprocess.run(
                cmd,
                cwd=working_dir,
            )

            if result.returncode == 0:
                console.success(f"Completed: {task_ref}")
                session_log.append(f"Completed: {task_ref}")
                completed.append(task_num)
            else:
                console.error(f"Failed: {task_ref} (exit code {result.returncode})")
                session_log.append(f"Failed: {task_ref} (exit code {result.returncode})")
                failed.append(task_num)

        except KeyboardInterrupt:
            console.warning("Interrupted by user")
            session_log.append("Session interrupted by user")
            break
        except Exception as e:
            console.error(f"Error: {e}")
            session_log.append(f"Error: {e}")
            failed.append(task_num)

    # Summary
    duration = format_duration(int((datetime.now() - start_time).total_seconds()))

    session_log.write_summary(
        Completed=[str(t) for t in completed],
        Failed=[str(t) for t in failed],
    )

    console.header("Session Complete")
    console.kv("Duration", duration)
    console.kv("Completed", str(len(completed)))
    console.kv("Failed", str(len(failed)))

    return 0 if not failed else 1
