"""Review command - run code reviews in isolated contexts."""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple, Optional

from ..config import get_config
from ..logging import Console, format_duration, console


class ReviewResult(NamedTuple):
    """Result of a single review."""

    name: str
    success: bool
    duration_seconds: int
    log_path: Path
    log_size: int


# Review definitions
REVIEWS = [
    ("Code Review (5 agents)", "ralph-review-code"),
    ("Code Simplifier", "ralph-review-simplify"),
    ("Security Review", "ralph-review-security"),
    ("Codex Review", "ralph-review-codex"),
]


def run_review(task_ref: str) -> int:
    """Run all code reviews in isolated contexts.

    Args:
        task_ref: Task reference (e.g., project#1)

    Returns:
        Exit code (0 = all success, 1 = any failures)
    """
    config = get_config()

    console.header(f"Running Reviews: {task_ref}")

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = config.log_dir / "reviews"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Suspend workflow state (if exists)
    state_file = Path.home() / ".claude/workflow-state/active_ralph_task.txt"
    state_backup = state_file.with_suffix(".bak")
    state_suspended = False

    if state_file.exists():
        try:
            state_file.rename(state_backup)
            state_suspended = True
            console.dim("Workflow state suspended")
        except Exception as e:
            console.warning(f"Could not suspend workflow state: {e}")

    results: List[ReviewResult] = []
    start_time = datetime.now()

    try:
        for review_name, skill_name in REVIEWS:
            result = run_single_review(
                task_ref=task_ref,
                review_name=review_name,
                skill_name=skill_name,
                log_dir=log_dir,
                timestamp=timestamp,
            )
            results.append(result)

    finally:
        # Restore workflow state
        if state_suspended and state_backup.exists():
            try:
                state_backup.rename(state_file)
                console.dim("Workflow state restored")
            except Exception as e:
                console.warning(f"Could not restore workflow state: {e}")

    # Print summary
    print_review_summary(results)

    # Count failures
    failures = sum(1 for r in results if not r.success)
    return 0 if failures == 0 else 1


def run_single_review(
    task_ref: str,
    review_name: str,
    skill_name: str,
    log_dir: Path,
    timestamp: str,
) -> ReviewResult:
    """Run single review and return result."""
    console.info(f"Starting: {review_name}")

    # Build log path
    safe_name = skill_name.replace("-", "_")
    task_safe = task_ref.replace("#", "_")
    log_path = log_dir / f"{task_safe}_{safe_name}_{timestamp}.log"

    cmd = [
        "claude",
        "-p",
        f"/{skill_name} {task_ref}",
        "--model",
        "opus",
        "--output-format",
        "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]

    start_time = time.time()

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=1800,  # 30 min timeout
            )

        duration = int(time.time() - start_time)
        success = result.returncode == 0
        log_size = log_path.stat().st_size

        if success:
            console.success(f"Completed: {review_name} ({format_duration(duration)})")
        else:
            console.error(f"Failed: {review_name} (exit code {result.returncode})")

        return ReviewResult(
            name=review_name,
            success=success,
            duration_seconds=duration,
            log_path=log_path,
            log_size=log_size,
        )

    except subprocess.TimeoutExpired:
        duration = int(time.time() - start_time)
        console.error(f"Timeout: {review_name}")
        return ReviewResult(
            name=review_name,
            success=False,
            duration_seconds=duration,
            log_path=log_path,
            log_size=log_path.stat().st_size if log_path.exists() else 0,
        )

    except Exception as e:
        duration = int(time.time() - start_time)
        console.error(f"Error: {review_name} - {e}")
        return ReviewResult(
            name=review_name,
            success=False,
            duration_seconds=duration,
            log_path=log_path,
            log_size=0,
        )


def print_review_summary(results: List[ReviewResult]):
    """Print summary table of review results."""
    success_count = sum(1 for r in results if r.success)
    total = len(results)

    console.header("SUMMARY")

    if success_count == total:
        console.success(f"All {total}/{total} reviews completed successfully!")
    else:
        console.warning(f"{success_count}/{total} reviews completed")

    # Print table
    print()
    print("┌" + "─" * 24 + "┬" + "─" * 14 + "┬" + "─" * 9 + "┬" + "─" * 13 + "┐")
    print("│" + "         Review         " + "│" + "    Status    " + "│" + "  Time   " + "│" + "  Log Size   " + "│")
    print("├" + "─" * 24 + "┼" + "─" * 14 + "┼" + "─" * 9 + "┼" + "─" * 13 + "┤")

    for r in results:
        status = "✅ Completed" if r.success else "❌ Failed"
        time_str = format_duration(r.duration_seconds)[:5]  # MM:SS
        size_kb = r.log_size // 1024

        name_col = r.name[:22].ljust(22)
        status_col = status.ljust(12)
        time_col = time_str.center(7)
        size_col = f"{size_kb:>6} KB".center(11)

        print(f"│ {name_col} │ {status_col} │ {time_col} │ {size_col} │")
        print("├" + "─" * 24 + "┼" + "─" * 14 + "┼" + "─" * 9 + "┼" + "─" * 13 + "┤")

    # Replace last separator with bottom border
    print("\033[1A" + "└" + "─" * 24 + "┴" + "─" * 14 + "┴" + "─" * 9 + "┴" + "─" * 13 + "┘")

    # Print log file paths
    print("\nLog files:")
    for r in results:
        print(f"  {r.name}: {r.log_path}")
