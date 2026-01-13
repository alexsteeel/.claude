"""Logging utilities for Ralph."""

import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

# ANSI colors
WHITE = "\033[1;37m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
DIM = "\033[2m"
NC = "\033[0m"  # Reset


def timestamp() -> str:
    """Return formatted timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_short() -> str:
    """Return short timestamp for inline use."""
    return datetime.now().strftime("%H:%M:%S")


class Console:
    """Console output with colors."""

    def __init__(self, file: TextIO = sys.stdout):
        self.file = file
        self.use_color = file.isatty()

    def _color(self, color: str, text: str) -> str:
        if self.use_color:
            return f"{color}{text}{NC}"
        return text

    def print(self, message: str = "", end: str = "\n"):
        print(message, file=self.file, end=end, flush=True)

    def header(self, title: str):
        self.print(self._color(BLUE, f"\n{'═' * 60}"))
        self.print(self._color(BLUE, f"  {title}"))
        self.print(self._color(BLUE, f"{'═' * 60}\n"))

    def subheader(self, title: str):
        self.print(self._color(CYAN, f"\n{'─' * 60}"))
        self.print(self._color(CYAN, f"  {title}"))
        self.print(self._color(CYAN, f"{'─' * 60}\n"))

    def success(self, message: str):
        self.print(self._color(GREEN, f"✓ {message}"))

    def error(self, message: str):
        self.print(self._color(RED, f"✗ {message}"))

    def warning(self, message: str):
        self.print(self._color(YELLOW, f"⚠ {message}"))

    def info(self, message: str):
        self.print(self._color(CYAN, f"  {message}"))

    def dim(self, message: str):
        self.print(self._color(DIM, message))

    def kv(self, key: str, value: str):
        """Print key-value pair."""
        self.print(f"{key}: {self._color(GREEN, value)}")


class SessionLog:
    """Session log file writer."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write_header(self, title: str, **fields):
        """Write session header."""
        with open(self.log_path, "w") as f:
            f.write(f"{'═' * 60}\n")
            f.write(f"{title}\n")
            f.write(f"{'═' * 60}\n\n")
            f.write(f"Started: {timestamp()}\n")
            for key, value in fields.items():
                f.write(f"{key}: {value}\n")
            f.write(f"\n{'─' * 60}\n")
            f.write("EXECUTION LOG\n")
            f.write(f"{'─' * 60}\n")

    def append(self, message: str):
        """Append line to log."""
        with open(self.log_path, "a") as f:
            f.write(f"[{timestamp()}] {message}\n")

    def write_summary(self, **sections):
        """Write session summary."""
        with open(self.log_path, "a") as f:
            f.write(f"\n{'─' * 60}\n")
            f.write("SESSION SUMMARY\n")
            f.write(f"{'─' * 60}\n\n")
            f.write(f"Finished: {timestamp()}\n\n")
            for section, lines in sections.items():
                f.write(f"{section}:\n")
                for line in lines:
                    f.write(f"  {line}\n")
            f.write(f"\n{'═' * 60}\n")


class TaskLog:
    """Task log file writer."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO | None = None

    def __enter__(self):
        self._file = open(self.log_path, "w")
        return self

    def __exit__(self, *args):
        if self._file:
            self._file.close()
            self._file = None

    def write_header(self, task_ref: str):
        """Write task header."""
        if self._file:
            self._file.write(f"{'═' * 60}\n")
            self._file.write(f"Task: {task_ref}\n")
            self._file.write(f"Started: {timestamp()}\n")
            self._file.write(f"{'═' * 60}\n\n")
            self._file.flush()

    def write(self, text: str):
        """Write text to log."""
        if self._file:
            self._file.write(text)
            self._file.flush()

    def write_footer(self, duration: str, result: str):
        """Write task footer."""
        if self._file:
            self._file.write(f"\n{'═' * 60}\n")
            self._file.write(f"Finished: {timestamp()}\n")
            self._file.write(f"Duration: {duration}\n")
            self._file.write(f"Result: {result}\n")
            self._file.write(f"{'═' * 60}\n")
            self._file.flush()


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS."""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Global console instance
console = Console()
