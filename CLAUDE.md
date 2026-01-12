# Claude Code Configuration

This repository contains Claude Code configuration: commands, skills, and hooks.

## Structure

```
~/.claude/
├── commands/           # Slash commands (/command-name)
├── skills/             # User-defined skills
├── hooks/              # Workflow automation hooks
└── scripts/            # Shell scripts for running loops
```

## Scripts

Shell scripts for running Ralph loops manually:

```bash
# Planning (interactive, with user feedback)
./scripts/ralph-plan.sh <project> <task_numbers...>
./scripts/ralph-plan.sh myproject 1 2 3
./scripts/ralph-plan.sh myproject 1-4 6 8-10    # ranges supported!

# Implementation (autonomous, no interaction)
./scripts/ralph-implement.sh <project> <task_numbers...>
./scripts/ralph-implement.sh myproject 1 2 3
./scripts/ralph-implement.sh myproject 1-4 6 8-10    # ranges supported!

# With options
WORKING_DIR=/path/to/project MAX_BUDGET=5 ./scripts/ralph-implement.sh myproject 1-5

# With retry settings
MAX_RETRIES=5 RETRY_DELAY=60 ./scripts/ralph-implement.sh myproject 1
```

### Task Number Ranges

Both scripts support range syntax for task numbers:

| Syntax | Expands to |
|--------|------------|
| `1-4` | `1 2 3 4` |
| `1-4 6 8-10` | `1 2 3 4 6 8 9 10` |
| `5-3` | `5 4 3` (reverse) |

| Script | Mode | Description |
|--------|------|-------------|
| `ralph-plan.sh` | Interactive | Runs `/ralph-plan-task` for each task, allows user communication |
| `ralph-implement.sh` | Autonomous | Runs `/ralph-implement-python-task` for each task, then `/ralph-batch-check` |
| `run-reviews.sh` | Autonomous | Runs all review commands in isolated contexts |

### ralph-implement.sh Options

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKING_DIR` | `$(pwd)` | Working directory for Claude |
| `MAX_BUDGET` | unlimited | Maximum budget in USD per task |
| `MAX_RETRIES` | 3 | Max retry attempts on API timeout |
| `RETRY_DELAY` | 30 | Delay in seconds between retries |

### Error Handling

The script automatically detects and diagnoses failures:

| Error Type | Detection | Action |
|------------|-----------|--------|
| `CONTEXT_OVERFLOW` | `Prompt is too long` | Fail (no retry) |
| `API_TIMEOUT` | `Tokens: 0 in / 0 out` | Auto-retry with `--resume` |
| `RATE_LIMIT` | `429` or `rate limit` | Fail (manual retry needed) |
| `AUTH_ERROR` | `401` or `403` | Fail |
| `UNKNOWN_ERROR` | `Unknown error` | Auto-retry with `--resume` |

### Cleanup Before Each Task

Before starting each task, the script cleans uncommitted changes:
```bash
git checkout -- .
git clean -fd
```

This ensures each task starts with a clean codebase, preventing contamination from failed previous tasks.

## Commands

### Task Execution

| Command | Description |
|---------|-------------|
| `/execute-python-task` | Full workflow: planning → approval → implementation → testing |
| `/ralph-plan-task project#N` | Planning only with human interaction (universal) |
| `/ralph-implement-python-task project#N` | Autonomous implementation (requires plan) |
| `/ralph-batch-check project#1 project#2...` | Run full test suite after batch, fix indirect issues |

### Reviews

| Command | Description |
|---------|-------------|
| `/ralph-review-code project#N` | 5 code review agents in parallel, saves to task |
| `/ralph-review-simplify project#N` | Code simplifier, saves to task |
| `/ralph-review-security project#N` | Security review, saves to task |
| `/ralph-review-codex project#N` | Codex review, saves to task |
| `/python-linters` | Run ruff and djlint on codebase |

### Reviews (direct, not recommended)

| Command | Description |
|---------|-------------|
| `/pr-review-toolkit:review-pr` | Comprehensive PR review (use Task tool for isolation) |
| `/security-review` | Security audit (use Task tool for isolation) |
| `/codex-review project#N` | Code review via Codex CLI (use Task tool for isolation) |

### Task Management

| Command | Description |
|---------|-------------|
| `/create-tasks` | Create tasks in md-task-mcp from requirements |
| `/memorize-task` | Update memory with task summary |

## Hooks

### check_workflow.py

Controls `/execute-python-task` workflow:
- Blocks stop until Claude confirms: `I confirm that all task phases are fully completed.`
- Returns checklist if not confirmed
- Allows "need feedback" bypass for user interaction

### check_workflow_ralph.py

Controls `/ralph-implement-python-task` autonomous workflow:
- Blocks stop until Claude confirms: `I confirm that all task phases are fully completed.`
- Returns checklist if not confirmed
- Allows stop on hold (`## Blocks` + `status=hold`)
- No "need feedback" bypass (autonomous mode)

### enforce_isolated_skills.py

Blocks direct Skill calls for tools that must run in isolated context:
- `pr-review-toolkit:review-pr` → must use Task tool
- `code-simplifier:code-simplifier` → must use Task tool
- `security-review` → must use Task tool
- `codex-review` → must use Task tool

These skills consume too much context when run directly, causing context overflow.

### hook_utils.py

Common logging utilities for all hooks:
```python
from hook_utils import get_logger
log = get_logger("my_hook")
log("EVENT", "message")
```

Writes to: `~/.claude/logs/hooks/{hook_name}.log`

### notify.sh

Desktop notifications for:
- Agent task completion
- User attention needed

## Logging

All logs are stored in `~/.claude/logs/`:

```
~/.claude/logs/
├── ralph-implement/          # Implementation sessions
│   ├── session_*.log         # Session summary
│   ├── {project}_{N}_*.log   # Per-task output
│   └── batch_check_*.log     # Batch check output
├── ralph-plan/               # Planning sessions
│   ├── session_*.log         # Session summary
│   └── {project}_{N}_*.log   # Per-task output
├── reviews/                  # Review sessions
│   └── {project}_{N}_{review}_*.log
└── hooks/                    # Hook events
    ├── check_workflow.log
    ├── check_workflow_ralph.log
    └── enforce_isolated_skills.log
```

### Log Format

**Scripts**: Full Claude output with timestamps and headers.

**Hooks**: `[YYYY-MM-DD HH:MM:SS] EVENT: message`
- `WORKFLOW_START` / `WORKFLOW_CONFIRMED` / `WORKFLOW_HOLD`
- `BLOCKED` / `ALLOWED`
- `NEED_FEEDBACK`
- `ERROR`

## Testing Requirements

All workflows require comprehensive testing:

| Type | Description |
|------|-------------|
| **Unit tests** | Functions, methods, edge cases |
| **API tests** | Endpoints, response codes, auth |
| **UI tests** | Playwright for frontend flows |
| **Edge cases** | Empty data, boundaries, errors |

## Workflow Phases

### execute-python-task (0-12)

```
0. Get Task
1. Plan Mode (EnterPlanMode → analysis → ExitPlanMode) ← STOP for approval
2. Update Task (status=work)
3. Implementation
4. Initial Testing
5. Code Review (/pr-review-toolkit:review-pr)
6. Security Review (/security-review)
7. Codex Review (/codex-review)
8. Final Testing
9. Linters (/python-linters)
10. Cleanup (garbage files, permissions)
11. Documentation
12. Complete (report, user confirmation) ← STOP for approval
```

### ralph-implement-python-task (0-11)

```
0. Validate Task (check ## Plan exists)
1. Update Task (status=work, skip if already work)
2. Read Plan Context (files from Scope)
3. Implementation
4. Initial Testing (with data-testid for UI tests)
5. UI Review (visual analysis with Opus + playwright)
6. Reviews (run-reviews.sh — isolated contexts)
7. Final Testing (+ final UI check)
8. Linters
9. Cleanup
10. Documentation
11. Complete (auto commit, report to task, status=done)
```

**Key difference**: Ralph is fully autonomous - no stops, auto-commits, blocks+hold on problems.

**Reviews (Phase 6)** run in isolated shell sessions via `run-reviews.sh`:
- `/ralph-review-code` — 5 agents in parallel
- `/ralph-review-simplify` — code-simplifier
- `/ralph-review-security` — security review
- `/ralph-review-codex` — Codex review

## Ralph Workflow Architecture

**Daily cycle:** Evening planning → Overnight implementation → Morning review

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RALPH WORKFLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│  │ md-task-mcp  │────▶│   Tasks DB   │◀────│ Task State Machine   │ │
│  └──────────────┘     └──────────────┘     │ backlog→work→done    │ │
│                                             │         ↓            │ │
│                                             │       hold           │ │
│                                             └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  PLANNING PHASE (Interactive)                                        │
│  ┌────────────────┐    ┌─────────────────────┐                      │
│  │ ralph-plan.sh  │───▶│ /ralph-plan-task    │                      │
│  │ (loop runner)  │    │ EnterPlanMode       │◀──▶ Human           │
│  └────────────────┘    │ AskUserQuestion     │     Feedback         │
│                        │ ExitPlanMode        │                      │
│                        └─────────────────────┘                      │
│                                 │                                    │
│                                 ▼                                    │
│                        ┌─────────────────────┐                      │
│                        │  Task += ## Plan    │                      │
│                        │  status = work      │                      │
│                        └─────────────────────┘                      │
├─────────────────────────────────────────────────────────────────────┤
│  IMPLEMENTATION PHASE (Autonomous)                                   │
│  ┌──────────────────┐  ┌───────────────────────────┐                │
│  │ralph-implement.sh│─▶│/ralph-implement-python-task│               │
│  │ --print          │  │ NO AskUserQuestion        │                │
│  │ --dangerously-   │  │ NO "need feedback"        │                │
│  │   skip-permissions│ │ Auto-commit on success    │                │
│  └──────────────────┘  └───────────────────────────┘                │
│           │                       │                                  │
│           │            ┌──────────┴──────────┐                      │
│           │            ▼                     ▼                      │
│           │    ┌─────────────┐       ┌─────────────┐                │
│           │    │   SUCCESS   │       │   BLOCKED   │                │
│           │    │ status=done │       │ WIP commit  │                │
│           │    │ + commit    │       │ status=hold │                │
│           │    └─────────────┘       │ + ## Blocks │                │
│           │                          └─────────────┘                │
│           ▼                                                          │
│  ┌────────────────────────────────────────────┐                     │
│  │         check_workflow_ralph.py            │                     │
│  │  Hook: UserPromptSubmit → track task       │                     │
│  │  Hook: Stop → require confirmation OR hold │                     │
│  └────────────────────────────────────────────┘                     │
├─────────────────────────────────────────────────────────────────────┤
│  BATCH CHECK PHASE (after all tasks)                                 │
│  ┌──────────────────┐  ┌───────────────────────────┐                │
│  │ralph-implement.sh│─▶│  /ralph-batch-check       │                │
│  │ (auto after loop)│  │  - Full test suite        │                │
│  └──────────────────┘  │  - Fix indirect issues    │                │
│                        │  - Create check task      │                │
│                        └───────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

## Reviews Isolation (run-reviews.sh)

Reviews run in isolated Claude sessions to prevent context overflow. The workflow state must be suspended for child sessions.

```mermaid
sequenceDiagram
    participant P as Parent Session<br>/ralph-implement-python-task
    participant S as run-reviews.sh
    participant F as workflow-state/<br>active_ralph_task.txt
    participant C as Child Sessions
    participant H as check_workflow_ralph.py

    P->>S: Phase 6: call run-reviews.sh
    S->>F: mv active_ralph_task.txt → .bak
    Note over F: State suspended

    loop For each review
        S->>C: claude "/ralph-review-* project#N"
        C->>H: Stop event
        H->>F: exists?
        F-->>H: NO (renamed to .bak)
        H-->>C: return 0 (allow)
        C->>C: update_task(review=...)
        C-->>S: exit 0
    end

    S->>F: mv .bak → active_ralph_task.txt
    Note over F: State restored (trap EXIT)
    S-->>P: return with summary table
    P->>P: Continue Phase 7...
```

### Hook State Machine

```mermaid
stateDiagram-v2
    [*] --> CheckEvent

    state CheckEvent {
        [*] --> UserPromptSubmit
        [*] --> Stop
    }

    state UserPromptSubmit {
        [*] --> CheckPrompt
        CheckPrompt --> SetActive: contains "ralph-implement-python-task"
        CheckPrompt --> Pass: otherwise
        SetActive --> [*]: write active_ralph_task.txt
        Pass --> [*]
    }

    state Stop {
        [*] --> CheckFile
        CheckFile --> Allow1: file not exists
        CheckFile --> CheckConfirmation: file exists

        CheckConfirmation --> CheckSkipped: confirmation found
        CheckConfirmation --> CheckHold: confirmation not found

        CheckSkipped --> Allow2: no @pytest.mark.skip
        CheckSkipped --> Block1: skip found in repo

        CheckHold --> Allow3: "## Blocks" or status=hold
        CheckHold --> Block2: otherwise

        Allow1 --> [*]: return 0
        Allow2 --> [*]: clear_active_task + return 0
        Allow3 --> [*]: clear_active_task + return 0
        Block1 --> [*]: return 2 + show files
        Block2 --> [*]: return 2 + show checklist
    }
```

### run-reviews.sh Output

```
════════════════════════════════════════════════════════════════════════════════
  SUMMARY
════════════════════════════════════════════════════════════════════════════════
🎉 All 4/4 reviews completed successfully!

┌────────────────────────┬──────────────┬───────┬─────────────┐
│         Review         │    Status    │ Time  │  Log Size   │
├────────────────────────┼──────────────┼───────┼─────────────┤
│ Code Review (5 agents) │ ✅ Completed │ 03:41 │      9 KB   │
├────────────────────────┼──────────────┼───────┼─────────────┤
│ Code Simplifier        │ ✅ Completed │ 01:56 │      2 KB   │
├────────────────────────┼──────────────┼───────┼─────────────┤
│ Security Review        │ ✅ Completed │ 01:44 │      2 KB   │
├────────────────────────┼──────────────┼───────┼─────────────┤
│ Codex Review           │ ✅ Completed │ 03:49 │      4 KB   │
└────────────────────────┴──────────────┴───────┴─────────────┘

Log files:
  Code Review (5 agents): ~/.claude/logs/reviews/project_N_ralph-review-code_*.log
  Code Simplifier: ~/.claude/logs/reviews/project_N_ralph-review-simplify_*.log
  Security Review: ~/.claude/logs/reviews/project_N_ralph-review-security_*.log
  Codex Review: ~/.claude/logs/reviews/project_N_ralph-review-codex_*.log
```

## Task Statuses (md-task-mcp)

| Status | Meaning |
|--------|---------|
| `backlog` | Not started |
| `work` | In progress |
| `done` | Implementation complete, awaiting review |
| `human approved` | Verified by human |
| `hold` | Blocked, needs human intervention |

## Blocks Pattern

When autonomous workflow encounters a problem:

```bash
# 1. Save current work
git add -A
git commit -m "WIP: project#N - blocked: brief description"
```

```python
# 2. Record block in task
update_task(
    project="project",
    number=N,
    status="hold",
    body=existing_body + """
## Blocks
- [2025-01-07 12:00] Problem description
  - Attempted: what was tried
  - Failed because: reason
  - Need from human: specific request
  - WIP commit: abc1234
"""
)
```

Then EXIT immediately. WIP commit ensures next task in loop starts clean.
