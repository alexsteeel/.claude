"""Telegram notifications for Ralph."""

import json
import sys
import urllib.request
from datetime import datetime
from typing import Optional

from .config import get_config


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown.

    Escapes underscores which cause issues with error codes like API_TIMEOUT.
    """
    return text.replace("_", "\\_")


def send_telegram(token: str, chat_id: str, message: str) -> bool:
    """Send message to Telegram.

    Returns True on success, False on failure.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


class Notifier:
    """Telegram notifier."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """Initialize notifier.

        If token/chat_id not provided, loads from config.
        """
        if token is None or chat_id is None:
            config = get_config()
            token = token or config.telegram_bot_token
            chat_id = chat_id or config.telegram_chat_id

        self.token = token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        """Check if notifications are configured."""
        return bool(self.token and self.chat_id)

    def _send(self, message: str) -> bool:
        """Send message if configured."""
        if not self.is_configured:
            return False
        return send_telegram(self.token, self.chat_id, message)

    def session_start(self, project: str, tasks: list[int]) -> bool:
        """Notify session start."""
        task_str = ", ".join(str(t) for t in tasks[:10])
        if len(tasks) > 10:
            task_str += "..."

        message = f"""🚀 *RALPH STARTED*

*Project:* {project}
*Tasks:* {len(tasks)} ({task_str})
*Time:* {datetime.now().strftime('%H:%M')}"""
        return self._send(message)

    def task_failed(self, task_ref: str, reason: str) -> bool:
        """Notify task failure."""
        message = f"""⚠️ Task {task_ref} failed: {escape_markdown(reason)}"""
        return self._send(message)

    def recovery_start(self, attempt: int, max_attempts: int, delay: int) -> bool:
        """Notify recovery start."""
        delay_min = delay // 60
        message = f"""🔄 *API error detected*
Recovery attempt {attempt}/{max_attempts} in {delay_min} min"""
        return self._send(message)

    def recovery_success(self, task_ref: str) -> bool:
        """Notify recovery success."""
        message = f"""✅ *API recovered*
Resuming task {task_ref}"""
        return self._send(message)

    def pipeline_stopped(self, reason: str) -> bool:
        """Notify pipeline stopped."""
        message = f"""🚨 *PIPELINE STOPPED*

*Reason:* {escape_markdown(reason)}
*Time:* {datetime.now().strftime('%H:%M')}"""
        return self._send(message)

    def session_complete(
        self,
        project: str,
        duration: str,
        completed: list[int],
        failed: list[int],
        failed_reasons: Optional[list[str]] = None,
        durations: Optional[dict[int, str]] = None,
    ) -> bool:
        """Notify session completion."""
        lines = [
            "📊 *RALPH SESSION COMPLETE*",
            "",
            f"*Project:* {project}",
            f"*Duration:* {duration}",
        ]

        if completed:
            lines.append("")
            lines.append(f"✅ *Completed ({len(completed)}):*")
            for task in completed:
                dur = durations.get(task, "") if durations else ""
                dur_str = f" ({dur})" if dur else ""
                lines.append(f"• #{task}{dur_str}")

        if failed:
            lines.append("")
            lines.append(f"❌ *Failed ({len(failed)}):*")
            for i, task in enumerate(failed):
                reason = (
                    failed_reasons[i]
                    if failed_reasons and i < len(failed_reasons)
                    else "UNKNOWN"
                )
                lines.append(f"• #{task} — {escape_markdown(reason)}")

        return self._send("\n".join(lines))

    def context_overflow(self, task_ref: str, retry: int, max_retries: int) -> bool:
        """Notify context overflow retry."""
        message = f"""⚠️ *Context overflow* on task {task_ref}
Retry {retry}/{max_retries} with fresh session"""
        return self._send(message)
