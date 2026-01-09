#!/bin/bash
#
# Ralph Planning Loop
# Runs /ralph-plan-task for each task sequentially in interactive mode
#
# Usage: ./ralph-plan.sh <project> <task_numbers...>
# Example: ./ralph-plan.sh myproject 1 2 3
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
NC='\033[0m' # No Color

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

usage() {
    echo "Usage: $0 <project> <task_numbers...>"
    echo ""
    echo "Arguments:"
    echo "  project        Project name (e.g., myproject)"
    echo "  task_numbers   One or more task numbers (e.g., 1 2 3)"
    echo ""
    echo "Example:"
    echo "  $0 myproject 1 2 3"
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
TASKS=("$@")

print_header

echo -e "Project: ${GREEN}${PROJECT}${NC}"
echo -e "Tasks:   ${GREEN}${TASKS[*]}${NC}"
echo -e "Mode:    ${YELLOW}Interactive (planning with human feedback)${NC}"
echo ""

TOTAL=${#TASKS[@]}
CURRENT=0
COMPLETED=()
FAILED=()

for TASK_NUM in "${TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    TASK_REF="${PROJECT}#${TASK_NUM}"

    print_task_header "$TASK_REF" "$CURRENT" "$TOTAL"

    echo -e "Starting Claude in interactive mode for planning..."
    echo -e "You can communicate with Claude to clarify requirements.\n"

    # Run Claude interactively
    # User can interact with Claude during planning
    if claude --model opus --dangerously-skip-permissions --settings '{"outputStyle": "explanatory"}' "/ralph-plan-task ${TASK_REF}"; then
        print_success "Planning completed for ${TASK_REF}"
        COMPLETED+=("$TASK_REF")
    else
        print_error "Planning failed or was cancelled for ${TASK_REF}"
        FAILED+=("$TASK_REF")
    fi

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

echo ""
echo -e "To implement planned tasks, run:"
echo -e "  ${GREEN}./ralph-implement.sh ${PROJECT} ${TASKS[*]}${NC}"
echo ""
