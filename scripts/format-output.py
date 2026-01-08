#!/usr/bin/env python3
"""Format Claude stream-json output for readable terminal display."""

import json
import sys

# Tool icons and formatters
TOOL_FORMATS = {
    "Read": ("📖", lambda i: i.get("file_path", "")),
    "Edit": ("✏️ ", lambda i: i.get("file_path", "")),
    "Write": ("📝", lambda i: i.get("file_path", "")),
    "Bash": ("💻", lambda i: i.get("command", "")[:80]),
    "Grep": ("🔍", lambda i: f"{i.get('pattern', '')} in {i.get('path', '.')}"),
    "Glob": ("🔍", lambda i: i.get("pattern", "")),
    "Task": ("🤖", lambda i: i.get("description", "")),
    "TodoWrite": ("✅", lambda i: "todos updated"),
    "WebFetch": ("🌐", lambda i: i.get("url", "")),
    "WebSearch": ("🔎", lambda i: i.get("query", "")),
    "Skill": ("⚡", lambda i: f"/{i.get('skill', '')}"),
    "LSP": ("🔗", lambda i: f"{i.get('operation', '')} {i.get('filePath', '')}"),
}


def format_mcp_tool(name: str, input_data: dict) -> str:
    """Format MCP tool calls."""
    if name.startswith("mcp__md-task-mcp__"):
        action = name.replace("mcp__md-task-mcp__", "")
        project = input_data.get("project", "")
        number = input_data.get("number", "")
        status = input_data.get("status", "")
        result = f"📋 {action} {project}#{number}"
        if status:
            result += f" → {status}"
        return result
    elif name.startswith("mcp__"):
        short_name = name.replace("mcp__", "")
        return f"🔌 {short_name}"
    return None


def format_tool(name: str, input_data: dict) -> str:
    """Format a tool call for display."""
    # Check MCP tools first
    mcp_result = format_mcp_tool(name, input_data)
    if mcp_result:
        return mcp_result

    # Check known tools
    if name in TOOL_FORMATS:
        icon, formatter = TOOL_FORMATS[name]
        return f"{icon} {formatter(input_data)}"

    # Fallback for unknown tools
    return f"🔧 {name}"


def process_line(line: str) -> str | None:
    """Process a single JSON line and return formatted output."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    if data.get("type") != "assistant":
        return None

    message = data.get("message", {})
    content = message.get("content", [])

    results = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if text:
                results.append(text)
        elif item.get("type") == "tool_use":
            name = item.get("name", "")
            input_data = item.get("input", {})
            results.append(format_tool(name, input_data))

    return "\n".join(results) if results else None


def main():
    """Read stdin line by line and output formatted text."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        result = process_line(line)
        if result:
            print(result, flush=True)


if __name__ == "__main__":
    main()
