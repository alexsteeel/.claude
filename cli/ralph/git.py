"""Git operations for Ralph."""

import subprocess
from pathlib import Path
from typing import Optional


def run_git(
    args: list[str], cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run git command and return result."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def cleanup_working_dir(working_dir: Path) -> list[str]:
    """Reset working directory to clean state.

    Runs:
        git checkout -- .
        git clean -fd

    Returns list of cleaned files.
    """
    cleaned = []

    # Get list of modified files before cleanup
    result = run_git(["status", "--porcelain"], cwd=working_dir, check=False)
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                # Format: "XY filename" where X=index, Y=worktree
                cleaned.append(line[3:].strip())

    # Reset tracked files
    run_git(["checkout", "--", "."], cwd=working_dir, check=False)

    # Remove untracked files
    run_git(["clean", "-fd"], cwd=working_dir, check=False)

    return cleaned


def get_uncommitted_changes(working_dir: Path) -> list[str]:
    """Return list of modified/untracked files."""
    result = run_git(["status", "--porcelain"], cwd=working_dir, check=False)
    if result.returncode != 0:
        return []

    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(line[3:].strip())
    return files


def has_uncommitted_changes(working_dir: Path) -> bool:
    """Check if there are uncommitted changes."""
    return bool(get_uncommitted_changes(working_dir))


def commit_wip(working_dir: Path, task_ref: str, message: str) -> Optional[str]:
    """Create WIP commit for blocked task.

    Args:
        working_dir: Repository path
        task_ref: Task reference (e.g., "project#1")
        message: Brief description of why blocked

    Returns:
        Commit hash if successful, None otherwise
    """
    if not has_uncommitted_changes(working_dir):
        return None

    # Stage all changes
    run_git(["add", "-A"], cwd=working_dir, check=False)

    # Create WIP commit
    commit_msg = f"WIP: {task_ref} - blocked: {message}"
    result = run_git(["commit", "-m", commit_msg], cwd=working_dir, check=False)

    if result.returncode != 0:
        return None

    # Get commit hash
    result = run_git(["rev-parse", "--short", "HEAD"], cwd=working_dir, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def get_current_branch(working_dir: Path) -> Optional[str]:
    """Get current branch name."""
    result = run_git(["branch", "--show-current"], cwd=working_dir, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def create_branch(working_dir: Path, branch_name: str) -> bool:
    """Create and switch to new branch."""
    result = run_git(["checkout", "-b", branch_name], cwd=working_dir, check=False)
    return result.returncode == 0


def switch_branch(working_dir: Path, branch_name: str) -> bool:
    """Switch to existing branch."""
    result = run_git(["checkout", branch_name], cwd=working_dir, check=False)
    return result.returncode == 0
