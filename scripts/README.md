# Ralph Scripts (Deprecated)

**Scripts migrated to Python CLI package: `~/.claude/cli/ralph`**

## New Usage

```bash
# Install
cd ~/.claude/cli
pip install -e .

# Commands
ralph plan myproject 1-5
ralph implement myproject 1-5
ralph review myproject#1
ralph health
```

See `~/.claude/cli/README.md` for full documentation.

## Configuration

Configuration still lives here in `.env`:

```bash
# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="-1001234567890"

# Recovery settings
RECOVERY_ENABLED=true
RECOVERY_DELAYS="600,1200,1800"  # 10, 20, 30 minutes
CONTEXT_OVERFLOW_MAX_RETRIES=2
```

## Files

```
~/.claude/scripts/
├── .env            # Credentials (git-ignored)
├── .env.example    # Example configuration
├── .gitignore
└── README.md       # This file

~/.claude/cli/
├── ralph/          # Python CLI package
├── tests/          # pytest tests
├── pyproject.toml
└── README.md       # Full documentation
```
