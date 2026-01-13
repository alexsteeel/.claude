"""Implement command - autonomous task implementation."""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config import Config, get_config
from ..errors import ErrorType
from ..executor import TaskResult, build_prompt, expand_task_ranges, run_claude
from ..git import cleanup_working_dir
from ..logging import Console, SessionLog, format_duration, console
from ..notify import Notifier
from ..recovery import recovery_loop, should_recover, should_retry_fresh


def run_implement(
    project: str,
    task_args: List[str],
    working_dir: Optional[Path] = None,
    max_budget: Optional[float] = None,
    no_recovery: bool = False,
) -> int:
    """Run autonomous implementation for tasks.

    Args:
        project: Project name
        task_args: Task numbers or ranges
        working_dir: Optional working directory
        max_budget: Maximum budget per task
        no_recovery: Disable automatic recovery

    Returns:
        Exit code (0 = all success, 1 = any failures)
    """
    config = get_config()
    if no_recovery:
        config.recovery_enabled = False

    tasks = expand_task_ranges(task_args)

    if not tasks:
        console.error("No valid task numbers provided")
        return 1

    if working_dir is None:
        working_dir = Path.cwd()

    notifier = Notifier()

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = config.log_dir / "ralph-implement"
    log_dir.mkdir(parents=True, exist_ok=True)
    session_log = SessionLog(log_dir / f"session_{timestamp}.log")

    session_log.write_header(
        "RALPH IMPLEMENTATION SESSION",
        Project=project,
        Tasks=", ".join(str(t) for t in tasks),
        WorkingDir=str(working_dir),
        MaxBudget=str(max_budget) if max_budget else "unlimited",
        Recovery="disabled" if no_recovery else "enabled",
    )

    console.header(f"Ralph Implementation: {project}")
    console.kv("Tasks", ", ".join(str(t) for t in tasks))
    console.kv("Working directory", str(working_dir))
    console.kv("Recovery", "disabled" if no_recovery else "enabled")

    # Notify session start
    notifier.session_start(project, tasks)

    completed: List[int] = []
    failed: List[int] = []
    failed_reasons: List[str] = []
    task_durations: Dict[int, str] = {}
    pipeline_stopped = False
    start_time = datetime.now()

    for task_num in tasks:
        if pipeline_stopped:
            break

        task_ref = f"{project}#{task_num}"
        console.subheader(f"Task: {task_ref}")
        session_log.append(f"Starting: {task_ref}")

        # Cleanup before task
        cleaned = cleanup_working_dir(working_dir)
        if cleaned:
            console.dim(f"Cleaned {len(cleaned)} files")
            session_log.append(f"Cleaned {len(cleaned)} files")

        result = execute_task_with_recovery(
            task_ref=task_ref,
            working_dir=working_dir,
            log_dir=log_dir,
            config=config,
            notifier=notifier,
            max_budget=max_budget,
            session_log=session_log,
        )

        task_durations[task_num] = format_duration(result.duration_seconds)

        if result.error_type.is_success:
            console.success(f"Completed: {task_ref} ({task_durations[task_num]})")
            session_log.append(f"Completed: {task_ref}")
            completed.append(task_num)

        elif result.error_type == ErrorType.ON_HOLD:
            console.warning(f"On hold: {task_ref}")
            session_log.append(f"On hold: {task_ref}")
            # Continue to next task (don't add to failed)

        elif result.error_type.is_fatal:
            console.error(f"Fatal error: {task_ref} - {result.error_type.value}")
            session_log.append(f"Fatal error: {task_ref} - {result.error_type.value}")
            failed.append(task_num)
            failed_reasons.append(result.error_type.value)
            pipeline_stopped = True
            notifier.pipeline_stopped(result.error_type.value)

        else:
            console.error(f"Failed: {task_ref} - {result.error_type.value}")
            session_log.append(f"Failed: {task_ref} - {result.error_type.value}")
            failed.append(task_num)
            failed_reasons.append(result.error_type.value)
            notifier.task_failed(task_ref, result.error_type.value)

    # Session complete
    duration = format_duration(int((datetime.now() - start_time).total_seconds()))

    session_log.write_summary(
        Completed=[str(t) for t in completed],
        Failed=[f"{t} ({failed_reasons[i]})" for i, t in enumerate(failed)],
    )

    console.header("Session Complete")
    console.kv("Duration", duration)
    console.kv("Completed", str(len(completed)))
    console.kv("Failed", str(len(failed)))

    # Notify session complete
    notifier.session_complete(
        project=project,
        duration=duration,
        completed=completed,
        failed=failed,
        failed_reasons=failed_reasons,
        durations=task_durations,
    )

    # Run batch check if any tasks completed
    if completed:
        run_batch_check(project, completed, working_dir, log_dir)

    return 0 if not failed else 1


def execute_task_with_recovery(
    task_ref: str,
    working_dir: Path,
    log_dir: Path,
    config: Config,
    notifier: Notifier,
    max_budget: Optional[float],
    session_log: SessionLog,
) -> TaskResult:
    """Execute single task with recovery loop."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    context_overflow_attempts = 0
    resume_session: Optional[str] = None
    recovery_note: Optional[str] = None

    while True:
        log_path = log_dir / f"{task_ref.replace('#', '_')}_{timestamp}.log"

        prompt = build_prompt(
            skill="ralph-implement-python-task",
            task_ref=task_ref,
            recovery_note=recovery_note,
        )

        result = run_claude(
            prompt=prompt,
            working_dir=working_dir,
            log_path=log_path,
            max_budget=max_budget,
            resume_session=resume_session,
        )

        # Success or on hold - return immediately
        if result.error_type.is_success or result.error_type == ErrorType.ON_HOLD:
            return result

        # Context overflow - retry with fresh session
        if should_retry_fresh(result.error_type, context_overflow_attempts, config):
            context_overflow_attempts += 1
            notifier.context_overflow(task_ref, context_overflow_attempts, config.context_overflow_max_retries)
            session_log.append(
                f"Context overflow retry {context_overflow_attempts}/{config.context_overflow_max_retries}"
            )
            console.warning(
                f"Context overflow - retry {context_overflow_attempts}/{config.context_overflow_max_retries}"
            )
            recovery_note = (
                f"Previous attempt failed with context overflow. "
                f"This is retry {context_overflow_attempts}/{config.context_overflow_max_retries}. "
                f"Focus on essential changes only."
            )
            resume_session = None  # Fresh session
            continue

        # Recoverable error - wait and retry
        if should_recover(result.error_type, config):
            console.warning(f"API error: {result.error_type.value} - starting recovery")
            session_log.append(f"Recovery started for {result.error_type.value}")

            def on_attempt(attempt: int, max_attempts: int, delay: int):
                notifier.recovery_start(attempt, max_attempts, delay)
                console.info(f"Recovery attempt {attempt}/{max_attempts} in {delay // 60} min")

            def on_recovered():
                notifier.recovery_success(task_ref)
                console.success("API recovered")

            recovered = recovery_loop(
                config=config,
                on_attempt=on_attempt,
                on_recovered=on_recovered,
            )

            if recovered:
                session_log.append("API recovered - resuming")
                resume_session = result.session_id
                recovery_note = (
                    f"Previous attempt was interrupted by {result.error_type.value}. "
                    f"This is a recovery resume. Continue where you left off."
                )
                continue
            else:
                session_log.append("Recovery failed - all attempts exhausted")
                console.error("Recovery failed - all attempts exhausted")
                return result

        # Non-recoverable error
        return result


def run_batch_check(
    project: str,
    completed_tasks: List[int],
    working_dir: Path,
    log_dir: Path,
):
    """Run batch check after all tasks complete."""
    import subprocess

    console.subheader("Running batch check")

    task_refs = " ".join(f"{project}#{t}" for t in completed_tasks)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"batch_check_{timestamp}.log"

    cmd = [
        "claude",
        "-p",
        f"/ralph-batch-check {task_refs}",
        "--model",
        "opus",
        "--output-format",
        "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]

    try:
        with open(log_path, "w") as log_file:
            from ..monitor import StreamMonitor

            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            monitor = StreamMonitor(log_file=log_file)
            if process.stdout:
                monitor.process_stream(process.stdout)

            process.wait()
            monitor.print_summary()

        console.success("Batch check complete")

    except Exception as e:
        console.error(f"Batch check failed: {e}")
