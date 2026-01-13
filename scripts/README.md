# Ralph Scripts

## Overview

Scripts for autonomous task execution with API recovery and Telegram notifications.

## Scripts

| Script | Description |
|--------|-------------|
| `ralph-plan.sh` | Interactive planning with human feedback |
| `ralph-implement.sh` | Autonomous implementation with recovery |
| `run-reviews.sh` | Run code reviews in isolated contexts |

## Configuration

### Environment Variables

Create `.env` file in `~/.claude/scripts/`:

```bash
# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="-1001234567890"

# Recovery settings
RECOVERY_ENABLED=true
RECOVERY_DELAYS="600,1200,1800"  # 10, 20, 30 minutes
```

### Telegram Bot Setup

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get bot token
3. Add bot to channel/group or get your chat ID
4. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`

## ralph-implement.sh Workflow

### Main Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         SESSION START                            │
│  • Load .env configuration                                       │
│  • Send Telegram: "🚀 Ralph started: project (N tasks)"          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FOR EACH TASK                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Cleanup repo   │
                    │  (git checkout) │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Run Task N    │
                    │   (claude -p)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Analyze Exit   │
                    │  Code & Logs    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         COMPLETED      RECOVERABLE      FATAL
              │         (401/timeout     (403/unknown)
              │          /429)                │
              ▼              │                ▼
    ┌─────────────┐          │      ┌─────────────────┐
    │ COMPLETED[] │          │      │  STOP PIPELINE  │
    │ Next Task   │          │      │  Telegram: 🚨   │
    └─────────────┘          │      └─────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │     RECOVERY LOOP        │
              │                          │
              │  Telegram: 🔄 Recovery   │
              │  attempt 1/3 in 10 min   │
              │                          │
              │  ┌────────────────────┐  │
              │  │ Sleep 10 min       │  │
              │  │ Health Check       │──┼──► OK ──┐
              │  └─────────┬──────────┘  │         │
              │            │ FAIL        │         │
              │  ┌─────────▼──────────┐  │         │
              │  │ Sleep 20 min       │  │         │
              │  │ Health Check       │──┼──► OK ──┤
              │  └─────────┬──────────┘  │         │
              │            │ FAIL        │         │
              │  ┌─────────▼──────────┐  │         │
              │  │ Sleep 30 min       │  │         │
              │  │ Health Check       │──┼──► OK ──┤
              │  └─────────┬──────────┘  │         │
              │            │ FAIL        │         │
              └────────────┼─────────────┘         │
                           │                       │
                           ▼                       │
                ┌─────────────────┐                │
                │ PIPELINE FAILED │                │
                │ Telegram: 🚨    │                │
                │ Exit Loop       │                │
                └─────────────────┘                │
                                                   │
                           ┌───────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  Telegram: ✅ Recovered  │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  RETRY TASK N            │
              │                          │
              │  Modified prompt:        │
              │  "Task was partially     │
              │   executed. Check git    │
              │   status and continue    │
              │   from where stopped."   │
              └────────────┬─────────────┘
                           │
                           ▼
                    (back to task loop)
```

### Error Classification

| Error | Detection | Action |
|-------|-----------|--------|
| `AUTH_EXPIRED` | `401` in logs | Recovery loop → Retry task |
| `API_TIMEOUT` | `Tokens: 0 in / 0 out` | Recovery loop → Retry task |
| `RATE_LIMIT` | `429` in logs | Recovery loop → Retry task |
| `OVERLOADED` | `529` or `overloaded` in logs | Recovery loop → Retry task |
| `CONTEXT_OVERFLOW` | `Prompt is too long` | Immediate retry (new session) |
| `FORBIDDEN` | `403` in logs | Stop pipeline |
| `COMPLETED` | Confirmation phrase | Success |

### Context Overflow Handling

Context overflow means the session accumulated too much context. Solution: **restart with fresh session**.

```
CONTEXT_OVERFLOW detected
         │
         ▼
┌─────────────────────────┐
│  Telegram: ⚠️ Context   │
│  overflow on task #N    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Increment retry count  │
│  (max 2 retries)        │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
  retries < 2   retries >= 2
     │             │
     ▼             ▼
┌──────────┐  ┌──────────────┐
│  RETRY   │  │  FAIL TASK   │
│  task    │  │  next task   │
│  (new    │  │  Telegram:🚨 │
│  session)│  └──────────────┘
└──────────┘
```

Retry prompt includes partial execution note (same as recovery retry).

### Health Check

Lightweight API check after detecting recoverable error:

```bash
python3 health_check.py [--verbose]
```

**Exit codes:**
- `0` — API healthy (got valid response)
- `1` — Auth error (401)
- `2` — Rate limited (429)
- `3` — Other error (timeout, parse error, etc.)
- `4` — Overloaded (529)

The script parses JSON response properly instead of grepping raw output.

### Telegram Notifications

| Event | Message |
|-------|---------|
| Session start | `🚀 *RALPH STARTED*\nProject: {project}\nTasks: {N}` |
| Task failed (non-recoverable) | `⚠️ Task #{N} failed: {reason}` |
| Recovery started | `🔄 API error detected\nRecovery attempt 1/3 in 10 min` |
| Recovery success | `✅ API recovered\nResuming task #{N}` |
| Pipeline stopped | `🚨 *PIPELINE STOPPED*\nReason: {error}` |
| Session complete | Full summary (see below) |

### Session Summary

```
📊 *RALPH SESSION COMPLETE*

*Project:* face_recognition
*Duration:* 04:16:51

✅ *Completed (3):*
• #91 (00:44:48)
• #93 (00:17:16)
• #98 (00:28:35)

❌ *Failed (3):*
• #95 — API_TIMEOUT
• #96 — AUTH_ERROR
• #97 — CONTEXT_OVERFLOW

📁 Session log: session_*.log
```

## File Structure

```
~/.claude/scripts/
├── ralph-implement.sh      # Main implementation script with recovery
├── ralph-plan.sh           # Planning script (interactive)
├── run-reviews.sh          # Reviews runner (isolated contexts)
├── stream-monitor.py        # JSON stream formatter with error classification
├── notify.py               # Telegram notifications (Python)
├── health_check.py         # API health check (Python)
├── .env                    # Credentials (git-ignored)
├── .env.example            # Example configuration
└── README.md               # This file
```

### Python Scripts

All Python scripts are standalone and use only standard library:

| Script | Purpose |
|--------|---------|
| `stream-monitor.py` | Formats Claude stream-json output, classifies errors |
| `health_check.py` | Lightweight API health check (exit codes 0-3) |
| `notify.py` | Sends Telegram notifications |

## Usage

```bash
# Planning (interactive)
./ralph-plan.sh myproject 1-5

# Implementation (autonomous)
./ralph-implement.sh myproject 1-5

# With custom settings
WORKING_DIR=/path/to/project ./ralph-implement.sh myproject 1-5
```

## Recovery Behavior

When recoverable error detected:

1. **Immediately**: Send Telegram notification
2. **Wait 10 min**: Health check
3. **Wait 20 min**: Health check (if still failing)
4. **Wait 30 min**: Health check (if still failing)
5. **If all fail**: Stop pipeline, send alert

After successful recovery:
- Restart current task with modified prompt
- Prompt includes: "Task was partially executed, check git status"
- Task cleanup runs before restart (git checkout)

## Partial Execution Prompt

When retrying after recovery, the prompt is modified:

```
/ralph-implement-python-task {project}#{number}

⚠️ RECOVERY NOTE: This task was partially executed before API interruption.
- Check `git status` and `git diff` for any uncommitted changes
- Review task status in md-task-mcp
- Continue from where the previous attempt stopped
- Do NOT redo already completed work
```
