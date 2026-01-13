#!/usr/bin/env python3
"""
Telegram Notifications for Ralph Pipeline

Sends notifications about pipeline status to Telegram.

Usage:
    # From command line
    python notify.py session_start --project myproject --tasks "1 2 3"
    python notify.py task_failed --task "myproject#1" --reason "API_TIMEOUT"
    python notify.py recovery_start --attempt 1 --max_attempts 3 --delay 600
    python notify.py recovery_success --task "myproject#1"
    python notify.py pipeline_stopped --reason "AUTH_ERROR"
    python notify.py session_complete --project myproject --duration "04:16:51" \\
        --completed "91,93,98" --failed "95,96,97" --failed_reasons "API_TIMEOUT,AUTH_ERROR,CONTEXT_OVERFLOW"

    # From Python
    from notify import send_notification
    send_notification("session_start", project="myproject", tasks=["1", "2", "3"])

Environment:
    TELEGRAM_BOT_TOKEN - Bot token from @BotFather
    TELEGRAM_CHAT_ID - Chat/channel ID for notifications
"""

import argparse
import os
import sys
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Optional
from datetime import datetime


def load_env() -> dict:
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / ".env"
    env_vars = {}

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value

    return env_vars


def get_config() -> tuple[Optional[str], Optional[str]]:
    """Get Telegram configuration from environment."""
    # Load from .env file first
    env_vars = load_env()

    # Environment variables override .env file
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or env_vars.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or env_vars.get("TELEGRAM_CHAT_ID")

    return token, chat_id


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown.

    Escapes: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    # For basic Markdown, mainly need to escape underscores
    return text.replace("_", "\\_")


def send_telegram(token: str, chat_id: str, message: str, parse_mode: str = "Markdown") -> bool:
    """Send message to Telegram.

    Returns True on success, False on failure.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


def format_session_start(project: str, tasks: list[str]) -> str:
    """Format session start message."""
    return f"""🚀 *RALPH STARTED*

*Project:* {project}
*Tasks:* {len(tasks)} ({', '.join(tasks[:10])}{'...' if len(tasks) > 10 else ''})
*Time:* {datetime.now().strftime('%H:%M')}"""


def format_task_failed(task: str, reason: str) -> str:
    """Format task failure message."""
    return f"""⚠️ Task {task} failed: {escape_markdown(reason)}"""


def format_recovery_start(attempt: int, max_attempts: int, delay: int) -> str:
    """Format recovery start message."""
    delay_min = delay // 60
    return f"""🔄 *API error detected*
Recovery attempt {attempt}/{max_attempts} in {delay_min} min"""


def format_recovery_success(task: str) -> str:
    """Format recovery success message."""
    return f"""✅ *API recovered*
Resuming task {task}"""


def format_pipeline_stopped(reason: str) -> str:
    """Format pipeline stopped message."""
    return f"""🚨 *PIPELINE STOPPED*

*Reason:* {escape_markdown(reason)}
*Time:* {datetime.now().strftime('%H:%M')}"""


def format_session_complete(
    project: str,
    duration: str,
    completed: list[str],
    failed: list[str],
    failed_reasons: Optional[list[str]] = None,
    durations: Optional[dict[str, str]] = None
) -> str:
    """Format session completion summary."""
    lines = [
        "📊 *RALPH SESSION COMPLETE*",
        "",
        f"*Project:* {project}",
        f"*Duration:* {duration}",
    ]

    if completed:
        lines.append("")
        lines.append(f"✅ *Completed ({len(completed)}):*")
        for i, task in enumerate(completed):
            dur = durations.get(task, "") if durations else ""
            dur_str = f" ({dur})" if dur else ""
            lines.append(f"• #{task}{dur_str}")

    if failed:
        lines.append("")
        lines.append(f"❌ *Failed ({len(failed)}):*")
        for i, task in enumerate(failed):
            reason = failed_reasons[i] if failed_reasons and i < len(failed_reasons) else "UNKNOWN"
            lines.append(f"• #{task} — {escape_markdown(reason)}")

    return "\n".join(lines)


def format_context_overflow(task: str, retry: int, max_retries: int) -> str:
    """Format context overflow message."""
    return f"""⚠️ *Context overflow* on task {task}
Retry {retry}/{max_retries} with fresh session"""


def send_notification(event: str, **kwargs) -> bool:
    """Send notification for given event.

    Returns True if sent successfully, False otherwise.
    """
    token, chat_id = get_config()

    if not token or not chat_id:
        # Silent fail if not configured
        return False

    formatters = {
        "session_start": lambda: format_session_start(
            kwargs.get("project", "unknown"),
            kwargs.get("tasks", [])
        ),
        "task_failed": lambda: format_task_failed(
            kwargs.get("task", "unknown"),
            kwargs.get("reason", "UNKNOWN")
        ),
        "recovery_start": lambda: format_recovery_start(
            kwargs.get("attempt", 1),
            kwargs.get("max_attempts", 3),
            kwargs.get("delay", 600)
        ),
        "recovery_success": lambda: format_recovery_success(
            kwargs.get("task", "unknown")
        ),
        "pipeline_stopped": lambda: format_pipeline_stopped(
            kwargs.get("reason", "UNKNOWN")
        ),
        "session_complete": lambda: format_session_complete(
            kwargs.get("project", "unknown"),
            kwargs.get("duration", "00:00:00"),
            kwargs.get("completed", []),
            kwargs.get("failed", []),
            kwargs.get("failed_reasons"),
            kwargs.get("durations")
        ),
        "context_overflow": lambda: format_context_overflow(
            kwargs.get("task", "unknown"),
            kwargs.get("retry", 1),
            kwargs.get("max_retries", 2)
        ),
    }

    formatter = formatters.get(event)
    if not formatter:
        print(f"Unknown event: {event}", file=sys.stderr)
        return False

    message = formatter()
    return send_telegram(token, chat_id, message)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Send Ralph pipeline notifications to Telegram")
    parser.add_argument("event", choices=[
        "session_start", "task_failed", "recovery_start", "recovery_success",
        "pipeline_stopped", "session_complete", "context_overflow"
    ], help="Event type")

    # Event-specific arguments
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--tasks", help="Task numbers (space or comma separated)")
    parser.add_argument("--task", help="Single task reference")
    parser.add_argument("--reason", help="Failure reason")
    parser.add_argument("--attempt", type=int, help="Recovery attempt number")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max recovery attempts")
    parser.add_argument("--delay", type=int, default=600, help="Delay in seconds")
    parser.add_argument("--duration", help="Session duration (HH:MM:SS)")
    parser.add_argument("--completed", help="Completed task numbers (comma separated)")
    parser.add_argument("--failed", help="Failed task numbers (comma separated)")
    parser.add_argument("--failed-reasons", help="Failure reasons (comma separated)")
    parser.add_argument("--retry", type=int, help="Context overflow retry number")
    parser.add_argument("--max-retries", type=int, default=2, help="Max context overflow retries")

    args = parser.parse_args()

    # Build kwargs from args
    kwargs = {}
    if args.project:
        kwargs["project"] = args.project
    if args.tasks:
        # Support both space and comma separated
        kwargs["tasks"] = [t.strip() for t in args.tasks.replace(",", " ").split()]
    if args.task:
        kwargs["task"] = args.task
    if args.reason:
        kwargs["reason"] = args.reason
    if args.attempt:
        kwargs["attempt"] = args.attempt
    if args.max_attempts:
        kwargs["max_attempts"] = args.max_attempts
    if args.delay:
        kwargs["delay"] = args.delay
    if args.duration:
        kwargs["duration"] = args.duration
    if args.completed:
        kwargs["completed"] = [t.strip() for t in args.completed.split(",") if t.strip()]
    if args.failed:
        kwargs["failed"] = [t.strip() for t in args.failed.split(",") if t.strip()]
    if args.failed_reasons:
        kwargs["failed_reasons"] = [r.strip() for r in args.failed_reasons.split(",")]
    if args.retry:
        kwargs["retry"] = args.retry
    if args.max_retries:
        kwargs["max_retries"] = args.max_retries

    success = send_notification(args.event, **kwargs)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
