#!/usr/bin/env python3
"""Format Claude stream-json output for readable terminal display.

Features:
- Timestamps for each message
- Token/cost metrics from API responses
- Color-coded output (Claude text vs tools vs MCP)
- Session statistics summary
"""

import json
import sys
from datetime import datetime

# ANSI colors
WHITE = "\033[1;37m"  # Claude text (bright white for dark terminals)
GREEN = "\033[0;32m"  # Tool calls
CYAN = "\033[0;36m"  # MCP calls
YELLOW = "\033[1;33m"  # Task agents
MAGENTA = "\033[0;35m"  # Results/stats
RED = "\033[0;31m"  # Errors
DIM = "\033[2m"  # Timestamps
NC = "\033[0m"  # Reset


def format_edit(i: dict) -> str:
    """Format Edit tool with change size."""
    path = i.get("file_path", "")
    old_len = len(i.get("old_string", ""))
    new_len = len(i.get("new_string", ""))
    return f"{path} [-{old_len}/+{new_len}]"


def _format_todos(i: dict) -> str:
    """Format TodoWrite with task summary."""
    todos = i.get("todos", [])
    if not todos:
        return "todos cleared"

    # Count by status
    in_progress = [t for t in todos if t.get("status") == "in_progress"]
    completed = sum(1 for t in todos if t.get("status") == "completed")
    pending = sum(1 for t in todos if t.get("status") == "pending")

    # Show current task (in_progress) if any
    if in_progress:
        current = in_progress[0].get("activeForm", in_progress[0].get("content", "?"))
        return f"{current} ({completed}✓ {pending}○)"

    # Show summary if all completed or pending
    if completed == len(todos):
        return f"all {completed} tasks completed"

    return f"{completed}✓ {pending}○ tasks"


def _format_read(i: dict) -> str:
    """Format Read tool with optional line range."""
    path = i.get("file_path", "")
    offset = i.get("offset")
    limit = i.get("limit")

    if offset or limit:
        range_info = []
        if offset:
            range_info.append(f"from:{offset}")
        if limit:
            range_info.append(f"lines:{limit}")
        return f"{path} ({', '.join(range_info)})"
    return path


def _format_bash(i: dict) -> str:
    """Format Bash tool with description on first line, command below in italic."""
    desc = i.get("description", "")
    cmd = i.get("command", "")
    bg = i.get("run_in_background", False)

    ITALIC = "\033[3m"
    RESET = "\033[0m"

    # Build output: description first, then command in italic
    lines = []
    if desc:
        if bg:
            lines.append(f"{desc} [bg]")
        else:
            lines.append(desc)

    if cmd:
        # Indent command lines
        for line in cmd.strip().split("\n"):
            lines.append(f"   {ITALIC}{line}{RESET}")

    if not lines:
        return "[no command]"

    return "\n".join(lines)


# Tool icons and formatters
TOOL_FORMATS = {
    "Read": ("📖", lambda i: _format_read(i)),
    "Edit": ("✏️", format_edit),
    "Write": ("📝", lambda i: i.get("file_path", "")),
    "Bash": ("💻", lambda i: _format_bash(i)),
    "Grep": ("🔍", lambda i: f"{i.get('pattern', '')} in {i.get('path', '.')}"),
    "Glob": ("🔍", lambda i: i.get("pattern", "")),
    "Task": ("🤖", lambda i: i.get("description", "")),
    "TaskOutput": ("🔧", lambda i: "TaskOutput"),
    "TodoWrite": ("✅", lambda i: _format_todos(i)),
    "WebFetch": ("🌐", lambda i: i.get("url", "")),
    "WebSearch": ("🔎", lambda i: i.get("query", "")),
    "Skill": ("⚡", lambda i: f"/{i.get('skill', '')}"),
    "LSP": ("🔗", lambda i: f"{i.get('operation', '')} {i.get('filePath', '')}"),
}

# Session statistics
session_stats = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read": 0,
    "cost_usd": 0.0,
    "tool_calls": 0,
}


def timestamp() -> str:
    """Return formatted timestamp."""
    return f"{DIM}[{datetime.now().strftime('%H:%M:%S')}]{NC}"


def format_mcp_tool(name: str, input_data: dict) -> str:
    """Format MCP tool calls."""
    if name.startswith("mcp__md-task-mcp__"):
        action = name.replace("mcp__md-task-mcp__", "")
        project = input_data.get("project", "")
        number = input_data.get("number", "")
        status = input_data.get("status", "")
        result = f"{CYAN}📋 {action} {project}#{number}"
        if status:
            result += f" → {status}"
        return result + NC
    elif name.startswith("mcp__"):
        short_name = name.replace("mcp__", "")
        return f"{CYAN}🔌 {short_name}{NC}"
    return None


def format_tool(name: str, input_data: dict) -> str:
    """Format a tool call for display."""
    global session_stats
    session_stats["tool_calls"] += 1

    # Check MCP tools first
    mcp_result = format_mcp_tool(name, input_data)
    if mcp_result:
        return mcp_result

    # Check known tools
    if name in TOOL_FORMATS:
        icon, formatter = TOOL_FORMATS[name]
        return f"{GREEN}{icon} {formatter(input_data)}{NC}"

    # Fallback for unknown tools
    return f"{GREEN}🔧 {name}{NC}"


def process_init(data: dict) -> str:
    """Process system init message."""
    model = data.get("model", "unknown")
    session_id = data.get("session_id", "")[:8]
    mcp_servers = data.get("mcp_servers", [])
    mcp_status = ", ".join(
        [
            f"{s['name']}({'ok' if s.get('status') == 'connected' else 'fail'})"
            for s in mcp_servers
        ]
    )
    return f"{DIM}Session: {session_id} | Model: {model} | MCP: {mcp_status or 'none'}{NC}"


def process_result(data: dict) -> str:
    """Process result message with metrics."""
    global session_stats
    cost = data.get("total_cost_usd", 0)
    usage = data.get("usage", {})
    input_t = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
    output_t = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    session_stats["input_tokens"] += input_t
    session_stats["output_tokens"] += output_t
    session_stats["cache_read"] += cache_read
    session_stats["cost_usd"] += cost

    if data.get("is_error"):
        # Show more error details
        error_msg = data.get("result", "")
        error_code = data.get("error_code", "")
        subtype = data.get("subtype", "")

        details = []
        if error_code:
            details.append(f"code={error_code}")
        if subtype:
            details.append(f"type={subtype}")

        if error_msg:
            msg_short = error_msg[:200] + ("..." if len(error_msg) > 200 else "")
            details.append(msg_short)

        if not details:
            # Dump all keys for debugging
            keys = [k for k in data.keys() if k not in ("usage", "total_cost_usd")]
            details.append(f"keys={keys}")

        return f"{RED}❌ ERROR: {' | '.join(details)}{NC}"

    return f"{MAGENTA}📊 {input_t:,} in / {output_t:,} out | ${cost:.4f}{NC}"


def process_line(line: str) -> str | None:
    """Process a single JSON line and return formatted output."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    msg_type = data.get("type")

    # Handle system init
    if msg_type == "system" and data.get("subtype") == "init":
        return process_init(data)

    # Handle result with metrics
    if msg_type == "result":
        return process_result(data)

    # Only process assistant messages
    if msg_type != "assistant":
        return None

    message = data.get("message", {})
    content = message.get("content", [])

    results = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if text:
                results.append(f"{WHITE}{text}{NC}")
        elif item.get("type") == "tool_use":
            name = item.get("name", "")
            input_data = item.get("input", {})
            results.append(format_tool(name, input_data))

    return "\n".join(results) if results else None


def print_session_summary():
    """Print session statistics summary."""
    if session_stats["tool_calls"] == 0 and session_stats["input_tokens"] == 0:
        return

    print(f"\n{MAGENTA}{'═' * 50}{NC}")
    print(f"{MAGENTA}SESSION TOTALS{NC}")
    print(f"{MAGENTA}{'─' * 50}{NC}")
    print(
        f"{MAGENTA}Tokens: {session_stats['input_tokens']:,} in / {session_stats['output_tokens']:,} out{NC}"
    )
    if session_stats["cache_read"] > 0:
        cache_pct = (
            session_stats["cache_read"] / session_stats["input_tokens"] * 100
            if session_stats["input_tokens"] > 0
            else 0
        )
        print(f"{MAGENTA}Cache:  {session_stats['cache_read']:,} ({cache_pct:.0f}%){NC}")
    print(f"{MAGENTA}Cost:   ${session_stats['cost_usd']:.4f}{NC}")
    print(f"{MAGENTA}Tools:  {session_stats['tool_calls']}{NC}")
    print(f"{MAGENTA}{'═' * 50}{NC}")


def main():
    """Read stdin line by line and output formatted text."""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            result = process_line(line)
            if result:
                print(f"{timestamp()} {result}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        print_session_summary()


if __name__ == "__main__":
    main()
