# Ralph CLI

Autonomous task execution CLI for Claude workflows.

## Installation

```bash
cd ~/.claude/cli
pip install -e .
```

## Usage

```bash
# Interactive planning
ralph plan myproject 1-4 6 8-10

# Autonomous implementation
ralph implement myproject 1-4 6 8-10
ralph implement myproject 1-3 -w /path/to/project --max-budget 5

# Run code reviews
ralph review myproject#1

# Check API health
ralph health
ralph health -v
```

## Commands

| Command | Description |
|---------|-------------|
| `plan` | Interactive task planning with human feedback |
| `implement` | Autonomous implementation with recovery and notifications |
| `review` | Run code reviews in isolated contexts |
| `health` | Check API health status |

## Configuration

Configuration is loaded from `~/.claude/scripts/.env`:

```bash
# Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Recovery settings
RECOVERY_ENABLED=true
RECOVERY_DELAYS=600,1200,1800  # 10, 20, 30 minutes
CONTEXT_OVERFLOW_MAX_RETRIES=2
```

## Development

```bash
# Run tests
pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

```
ralph/
├── __init__.py         # Package info
├── __main__.py         # Entry point
├── cli.py              # Typer CLI definition
├── config.py           # Configuration loading
├── errors.py           # Error types and classification
├── logging.py          # Logging utilities
├── executor.py         # Claude process execution
├── monitor.py          # Stream JSON parsing
├── recovery.py         # Recovery loop logic
├── git.py              # Git operations
├── notify.py           # Telegram notifications
├── health.py           # API health check
└── commands/           # CLI subcommands
    ├── plan.py
    ├── implement.py
    ├── review.py
    └── health.py
```
