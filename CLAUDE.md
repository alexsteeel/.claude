# Claude Code Configuration

This repository contains Claude Code configuration: commands, agents, and hooks.

## Structure

```
~/.claude/
├── commands/           # Slash commands (/command-name)
├── skills/             # User-defined skills
├── agents/             # Custom Task agents (subagent_type)
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
```

| Script | Mode | Description |
|--------|------|-------------|
| `ralph-plan.sh` | Interactive | Runs `/ralph-plan-task` for each task, allows user communication |
| `ralph-implement.sh` | Autonomous | Runs `/ralph-implement-python-task` with `--print`, logs to `~/.claude/logs/` |

## Commands

### Task Execution

| Command | Description |
|---------|-------------|
| `/execute-python-task` | Full workflow: planning → approval → implementation → testing |
| `/ralph-plan-task project#N` | Planning only with human interaction (universal) |
| `/ralph-implement-python-task project#N` | Autonomous implementation (requires plan) |

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

## Agents

Custom agents for `Task(subagent_type="agent-name")`.

Place agent definition files in `~/.claude/agents/` directory.

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
5. Code Review (pr-review-toolkit)
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

## Git Conventions

Commit message format:
- Start with verb: Add, Fix, Update, Remove, Refactor
- No period at end
- No emoji, no Co-Authored-By

Examples:
- `Add attendance export to Excel`
- `Fix camera auto-reconnect on connection loss`
- `Update employee validation rules`

## File Permissions

| Type | Mode | Description |
|------|------|-------------|
| `*.py` | 644 | Python modules |
| `*.sh` | 755 | Shell scripts |
| `*.html`, `*.css`, `*.js` | 644 | Web assets |
| `*.md`, `*.json`, `*.yml` | 644 | Config and docs |

## Docker Containers

Configuration is synced to:
- `your-project-devcontainer-1`
- `your-project-devcontainer-2`

User in containers: `claude` (not `vscode`)

Sync command:
```bash
docker cp ~/.claude/commands/file.md container:/home/claude/.claude/commands/
docker exec --user root container chown claude:claude /home/claude/.claude/commands/file.md
```
