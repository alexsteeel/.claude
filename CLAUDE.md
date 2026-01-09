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

# Implementation (autonomous, no interaction)
./scripts/ralph-implement.sh <project> <task_numbers...>
./scripts/ralph-implement.sh myproject 1 2 3

# With options
WORKING_DIR=/path/to/project MAX_BUDGET=5 ./scripts/ralph-implement.sh myproject 1

# With retry settings
MAX_RETRIES=5 RETRY_DELAY=60 ./scripts/ralph-implement.sh myproject 1
```

| Script | Mode | Description |
|--------|------|-------------|
| `ralph-plan.sh` | Interactive | Runs `/ralph-plan-task` for each task, allows user communication |
| `ralph-implement.sh` | Autonomous | Runs `/ralph-implement-python-task` for each task, then `/ralph-batch-check` |

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
| `API_TIMEOUT` | `Tokens: 0 in / 0 out` | Auto-retry with `--resume` |
| `RATE_LIMIT` | `429` or `rate limit` | Fail (manual retry needed) |
| `AUTH_ERROR` | `401` or `403` | Fail |
| `UNKNOWN_ERROR` | `Unknown error` | Auto-retry with `--resume` |

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
| `/pr-review-toolkit:review-pr` | Comprehensive PR review using specialized agents (plugin) |
| `/security-review` | Security audit of uncommitted changes (built-in) |
| `/codex-review project#N` | Code review via Codex CLI tool |
| `/python-linters` | Run ruff and djlint on codebase |

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

### notify.sh

Desktop notifications for:
- Agent task completion
- User attention needed

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

### ralph-implement-python-task (0-12)

```
0. Validate Task (check ## Plan exists)
1. Update Task (status=work)
2. Read Plan Context (files from Scope)
3. Implementation
4. Initial Testing
5. Code Review (pr-review-toolkit + code-simplifier)
6. Security Review (/security-review)
7. Codex Review
8. Final Testing
9. Linters
10. Cleanup
11. Documentation
12. Complete (auto commit, report to task, status=done)
```

**Key difference**: Ralph is fully autonomous - no stops, auto-commits, blocks+hold on problems.

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
