#!/bin/bash
#
# Ralph Planning Loop
# Runs /ralph-plan-task for each task sequentially in interactive mode
#
# Usage: ./ralph-plan.sh <project> <task_numbers...>
# Example: ./ralph-plan.sh myproject 1 2 3
# Example: ./ralph-plan.sh myproject 1-4 6 8-10  (expands to 1 2 3 4 6 8 9 10)
#
# ⚠️  WARNING: This script uses --dangerously-skip-permissions flag!
#     Claude will execute commands without asking for confirmation.
#     Only run on trusted codebases in isolated environments.
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
LOG_DIR="${HOME}/.claude/logs/ralph-plan"
mkdir -p "$LOG_DIR"

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  RALPH PLANNING LOOP${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"
}

print_task_header() {
    local task_ref="$1"
    local current="$2"
    local total="$3"
    echo -e "\n${YELLOW}────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}  Task ${current}/${total}: ${task_ref}${NC}"
    echo -e "${YELLOW}────────────────────────────────────────────────────────${NC}\n"
}

print_success() {
    echo -e "\n${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "\n${RED}✗ $1${NC}"
}

# Expand ranges like "1-4 6 8-10" to "1 2 3 4 6 8 9 10"
expand_ranges() {
    local result=()
    for arg in "$@"; do
        if [[ "$arg" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            if [[ $start -le $end ]]; then
                for ((i=start; i<=end; i++)); do
                    result+=("$i")
                done
            else
                # Reverse range (e.g., 10-8 → 10 9 8)
                for ((i=start; i>=end; i--)); do
                    result+=("$i")
                done
            fi
        else
            result+=("$arg")
        fi
    done
    echo "${result[@]}"
}

usage() {
    echo "Usage: $0 <project> <task_numbers...>"
    echo ""
    echo "Arguments:"
    echo "  project        Project name (e.g., myproject)"
    echo "  task_numbers   One or more task numbers or ranges"
    echo ""
    echo "Ranges:"
    echo "  N-M            Expands to N, N+1, ..., M (e.g., 1-4 → 1 2 3 4)"
    echo ""
    echo "Examples:"
    echo "  $0 myproject 1 2 3"
    echo "  $0 myproject 1-4 6 8-10    # expands to 1 2 3 4 6 8 9 10"
    echo ""
    echo "This script runs /ralph-plan-task for each task in INTERACTIVE mode."
    echo "You can communicate with Claude during planning."
    exit 1
}

# Check arguments
if [[ $# -lt 2 ]]; then
    usage
fi

PROJECT="$1"
shift
# Expand ranges (e.g., "1-4 6" → "1 2 3 4 6")
EXPANDED=$(expand_ranges "$@")
read -ra TASKS <<< "$EXPANDED"

print_header

echo -e "Project: ${GREEN}${PROJECT}${NC}"
echo -e "Tasks:   ${GREEN}${TASKS[*]}${NC}"
echo -e "Mode:    ${YELLOW}Interactive (planning with human feedback)${NC}"
echo ""

TOTAL=${#TASKS[@]}
CURRENT=0
COMPLETED=()
FAILED=()

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_LOG="${LOG_DIR}/session_${PROJECT}_${TIMESTAMP}.log"

# Initialize session log
{
    echo "═══════════════════════════════════════════════════════════════"
    echo "RALPH PLANNING SESSION"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Started:     $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Project:     ${PROJECT}"
    echo "Tasks:       ${TASKS[*]}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "TASK PLANNING LOG"
    echo "───────────────────────────────────────────────────────────────"
} > "$SESSION_LOG"

echo -e "Logs:        ${GREEN}${LOG_DIR}/${NC}"
echo ""

for TASK_NUM in "${TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    TASK_REF="${PROJECT}#${TASK_NUM}"
    LOG_FILE="${LOG_DIR}/${PROJECT}_${TASK_NUM}_${TIMESTAMP}.log"

    print_task_header "$TASK_REF" "$CURRENT" "$TOTAL"

    # Record start time
    TASK_START=$(date '+%Y-%m-%d %H:%M:%S')

    echo -e "Log file: ${CYAN}${LOG_FILE}${NC}"
    echo -e "Starting Claude in interactive mode for planning..."
    echo -e "You can communicate with Claude to clarify requirements.\n"

    # Initialize task log
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "Task: ${TASK_REF}"
        echo "Started: ${TASK_START}"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
    } > "$LOG_FILE"

    # Run Claude interactively with logging
    # User can interact with Claude during planning
    if claude --model opus --dangerously-skip-permissions --settings '{"outputStyle": "explanatory"}' "/ralph-plan-task ${TASK_REF}" 2>&1 | tee -a "$LOG_FILE"; then
        TASK_END=$(date '+%Y-%m-%d %H:%M:%S')
        print_success "Planning completed for ${TASK_REF}"
        COMPLETED+=("$TASK_REF")
        echo "[${TASK_END}] ✓ ${TASK_REF} - COMPLETED" >> "$SESSION_LOG"
    else
        TASK_END=$(date '+%Y-%m-%d %H:%M:%S')
        print_error "Planning failed or was cancelled for ${TASK_REF}"
        FAILED+=("$TASK_REF")
        echo "[${TASK_END}] ✗ ${TASK_REF} - FAILED/CANCELLED" >> "$SESSION_LOG"
    fi

    # Add footer to task log
    {
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Finished: ${TASK_END}"
        echo "═══════════════════════════════════════════════════════════════"
    } >> "$LOG_FILE"

    # If more tasks remain, ask to continue
    if [[ $CURRENT -lt $TOTAL ]]; then
        echo ""
        read -p "Continue to next task? [Y/n] " -n 1 -r REPLY
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}Stopping loop at user request.${NC}"
            break
        fi
    fi
done

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

if [[ ${#COMPLETED[@]} -gt 0 ]]; then
    echo -e "${GREEN}Completed (${#COMPLETED[@]}):${NC}"
    for task in "${COMPLETED[@]}"; do
        echo -e "  ✓ $task"
    done
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo -e "${RED}Failed/Cancelled (${#FAILED[@]}):${NC}"
    for task in "${FAILED[@]}"; do
        echo -e "  ✗ $task"
    done
fi

REMAINING=$((TOTAL - CURRENT))
if [[ $REMAINING -gt 0 ]]; then
    echo -e "${YELLOW}Not started (${REMAINING}):${NC}"
    for ((i=CURRENT; i<TOTAL; i++)); do
        echo -e "  - ${PROJECT}#${TASKS[$i]}"
    done
fi

# Write final summary to session log
{
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "SESSION SUMMARY"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
    echo "Finished:    $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "Results:"
    echo "  Completed: ${#COMPLETED[@]}"
    echo "  Failed:    ${#FAILED[@]}"
    echo ""
    if [[ ${#COMPLETED[@]} -gt 0 ]]; then
        echo "Completed tasks:"
        for task in "${COMPLETED[@]}"; do
            echo "  ✓ $task"
        done
    fi
    if [[ ${#FAILED[@]} -gt 0 ]]; then
        echo "Failed tasks:"
        for task in "${FAILED[@]}"; do
            echo "  ✗ $task"
        done
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
} >> "$SESSION_LOG"

echo ""
echo -e "Session log: ${GREEN}${SESSION_LOG}${NC}"
echo ""
echo -e "To implement planned tasks, run:"
echo -e "  ${GREEN}./ralph-implement.sh ${PROJECT} ${TASKS[*]}${NC}"
echo ""
