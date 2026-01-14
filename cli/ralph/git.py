"""Git operations using GitPython."""

import logging
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


def get_repo(working_dir: Path) -> Optional[Repo]:
    """Get git repository for working directory."""
    try:
        return Repo(working_dir)
    except InvalidGitRepositoryError:
        return None


def get_files_to_clean(working_dir: Path) -> tuple[list[str], list[str]]:
    """Get list of files that would be cleaned.

    Returns:
        Tuple of (modified_files, untracked_files).
    """
    repo = get_repo(working_dir)
    if not repo:
        return [], []

    modified = []
    untracked = []

    if repo.is_dirty(untracked_files=True):
        for item in repo.index.diff(None):
            modified.append(item.a_path)
        untracked = list(repo.untracked_files)

    return modified, untracked


def cleanup_working_dir(working_dir: Path) -> list[str]:
    """Reset working directory to clean state.

    Runs:
        git checkout -- .
        git clean -fd

    Returns list of cleaned files.
    """
    repo = get_repo(working_dir)
    if not repo:
        return []

    modified, untracked = get_files_to_clean(working_dir)
    cleaned = modified + untracked

    # Reset tracked files
    try:
        repo.git.checkout("--", ".")
    except GitCommandError as e:
        logger.debug("git checkout failed: %s", e)

    # Remove untracked files
    try:
        repo.git.clean("-fd")
    except GitCommandError as e:
        logger.debug("git clean failed: %s", e)

    return cleaned


def get_uncommitted_changes(working_dir: Path) -> list[str]:
    """Return list of modified/untracked files."""
    repo = get_repo(working_dir)
    if not repo:
        return []

    files = []

    # Modified files
    for item in repo.index.diff(None):
        files.append(item.a_path)

    # Staged files
    for item in repo.index.diff("HEAD"):
        files.append(item.a_path)

    # Untracked files
    files.extend(repo.untracked_files)

    return list(set(files))


def has_uncommitted_changes(working_dir: Path) -> bool:
    """Check if there are uncommitted changes."""
    repo = get_repo(working_dir)
    if not repo:
        return False
    return repo.is_dirty(untracked_files=True)


def commit_wip(working_dir: Path, task_ref: str, message: str) -> Optional[str]:
    """Create WIP commit for blocked task.

    Args:
        working_dir: Repository path
        task_ref: Task reference (e.g., "project#1")
        message: Brief description of why blocked

    Returns:
        Commit hash if successful, None otherwise
    """
    repo = get_repo(working_dir)
    if not repo:
        return None

    if not repo.is_dirty(untracked_files=True):
        return None

    try:
        # Stage all changes
        repo.git.add("-A")

        # Create WIP commit
        commit_msg = f"WIP: {task_ref} - blocked: {message}"
        repo.index.commit(commit_msg)

        # Return short hash
        return repo.head.commit.hexsha[:7]
    except GitCommandError as e:
        logger.debug("commit_wip failed: %s", e)
        return None


def get_current_branch(working_dir: Path) -> Optional[str]:
    """Get current branch name."""
    repo = get_repo(working_dir)
    if not repo:
        return None

    try:
        return repo.active_branch.name
    except TypeError:
        # Detached HEAD state
        return None


def create_branch(working_dir: Path, branch_name: str) -> bool:
    """Create and switch to new branch."""
    repo = get_repo(working_dir)
    if not repo:
        return False

    try:
        repo.git.checkout("-b", branch_name)
        return True
    except GitCommandError as e:
        logger.debug("create_branch failed: %s", e)
        return False


def switch_branch(working_dir: Path, branch_name: str) -> bool:
    """Switch to existing branch."""
    repo = get_repo(working_dir)
    if not repo:
        return False

    try:
        repo.git.checkout(branch_name)
        return True
    except GitCommandError as e:
        logger.debug("switch_branch failed: %s", e)
        return False
