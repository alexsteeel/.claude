#!/bin/bash
#
# Ralph Implementation Loop
# Runs /ralph-implement-python-task for each task sequentially in autonomous mode
#
# Usage: ./ralph-implement.sh <project> <task_numbers...>
# Example: ./ralph-implement.sh myproject 1 2 3
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Log directory
LOG_DIR="${HOME}/.claude/logs/ralph-implement"
mkdir -p "$LOG_DIR"

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  RALPH AUTONOMOUS IMPLEMENTATION LOOP${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"
}

print_task_header() {
    local task_ref="$1"
    local current="$2"
    local total="$3"
    echo -e "\n${CYAN}────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}  Task ${current}/${total}: ${task_ref}${NC}"
    echo -e "${CYAN}  Mode: AUTONOMOUS (no user interaction)${NC}"
    echo -e "${CYAN}────────────────────────────────────────────────────────${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

usage() {
    echo "Usage: $0 <project> <task_numbers...>"
    echo ""
    echo "Arguments:"
    echo "  project        Project name (e.g., myproject)"
    echo "  task_numbers   One or more task numbers (e.g., 1 2 3)"
    echo ""
    echo "Options (via environment variables):"
    echo "  WORKING_DIR    Working directory for Claude (default: current directory)"
    echo "  MAX_BUDGET     Maximum budget in USD per task (default: no limit)"
    echo ""
    echo "Example:"
    echo "  $0 myproject 1 2 3"
    echo "  WORKING_DIR=/path/to/project MAX_BUDGET=5 $0 myproject 1 2 3"
    echo ""
    echo "This script runs /ralph-implement-python-task in AUTONOMOUS mode."
    echo "Tasks must have a ## Plan section (run ralph-plan.sh first)."
    echo ""
    echo "Logs are saved to: ${LOG_DIR}/"
    exit 1
}

# Check arguments
if [[ $# -lt 2 ]]; then
    usage
fi

PROJECT="$1"
shift
TASKS=("$@")

# Optional settings
WORKING_DIR="${WORKING_DIR:-$(pwd)}"
MAX_BUDGET="${MAX_BUDGET:-}"

print_header

echo -e "Project:     ${GREEN}${PROJECT}${NC}"
echo -e "Tasks:       ${GREEN}${TASKS[*]}${NC}"
echo -e "Mode:        ${CYAN}Autonomous (--print, no interaction)${NC}"
echo -e "Working dir: ${GREEN}${WORKING_DIR}${NC}"
if [[ -n "$MAX_BUDGET" ]]; then
    echo -e "Max budget:  ${GREEN}\$${MAX_BUDGET} per task${NC}"
fi
echo -e "Logs:        ${GREEN}${LOG_DIR}/${NC}"
echo ""

TOTAL=${#TASKS[@]}
CURRENT=0
COMPLETED=()
FAILED=()
ON_HOLD=()

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

for TASK_NUM in "${TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    TASK_REF="${PROJECT}#${TASK_NUM}"
    LOG_FILE="${LOG_DIR}/${PROJECT}_${TASK_NUM}_${TIMESTAMP}.log"

    print_task_header "$TASK_REF" "$CURRENT" "$TOTAL"

    echo -e "Log file: ${LOG_FILE}"
    echo -e "Starting autonomous implementation...\n"

    # Build Claude command
    CLAUDE_CMD="claude -p --model opus"

    if [[ -n "$MAX_BUDGET" ]]; then
        CLAUDE_CMD="$CLAUDE_CMD --max-budget-usd $MAX_BUDGET"
    fi

    # Add permission bypass for autonomous mode
    CLAUDE_CMD="$CLAUDE_CMD --dangerously-skip-permissions"

    # Run Claude in print mode (autonomous)
    # Output goes to both terminal and log file
    cd "$WORKING_DIR"

    set +e  # Don't exit on error
    $CLAUDE_CMD "/ralph-implement-python-task ${TASK_REF}" 2>&1 | tee "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    # Check result
    if [[ $EXIT_CODE -eq 0 ]]; then
        # Check if task was put on hold (look for hold markers in log)
        if grep -q 'status="hold"' "$LOG_FILE" 2>/dev/null || grep -q '## Blocks' "$LOG_FILE" 2>/dev/null; then
            print_warning "Task ${TASK_REF} put ON HOLD (blocked)"
            ON_HOLD+=("$TASK_REF")
        else
            print_success "Implementation completed for ${TASK_REF}"
            COMPLETED+=("$TASK_REF")
        fi
    else
        print_error "Implementation failed for ${TASK_REF} (exit code: $EXIT_CODE)"
        FAILED+=("$TASK_REF")
    fi

    echo ""
done

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

if [[ ${#COMPLETED[@]} -gt 0 ]]; then
    echo -e "${GREEN}Completed (${#COMPLETED[@]}):${NC}"
    for task in "${COMPLETED[@]}"; do
        echo -e "  ✓ $task (status: done)"
    done
fi

if [[ ${#ON_HOLD[@]} -gt 0 ]]; then
    echo -e "${YELLOW}On Hold (${#ON_HOLD[@]}):${NC}"
    for task in "${ON_HOLD[@]}"; do
        echo -e "  ⚠ $task (needs human attention)"
    done
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo -e "${RED}Failed (${#FAILED[@]}):${NC}"
    for task in "${FAILED[@]}"; do
        echo -e "  ✗ $task"
    done
fi

echo ""
echo -e "Logs saved to: ${GREEN}${LOG_DIR}/${NC}"
echo ""

# Exit with error if any tasks failed
if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
