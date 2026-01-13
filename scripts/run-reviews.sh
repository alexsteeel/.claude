#!/bin/bash
#
# Run Reviews in Isolated Contexts
# Calls each review command sequentially via separate Claude sessions
#
# Usage: ./run-reviews.sh <project#N>
# Example: ./run-reviews.sh myproject#18
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log directory
LOG_DIR="${HOME}/.claude/logs/reviews"
mkdir -p "$LOG_DIR"

usage() {
    echo "Usage: $0 <project#N>"
    echo ""
    echo "Example:"
    echo "  $0 myproject#18"
    echo ""
    echo "Runs all review commands in isolated contexts:"
    echo "  1. /ralph-review-code (5 agents in parallel)"
    echo "  2. /ralph-review-simplify"
    echo "  3. /ralph-review-security"
    echo "  4. /ralph-review-codex"
    echo ""
    echo "Results are saved to the task's review field."
    exit 1
}

if [[ $# -ne 1 ]]; then
    usage
fi

TASK_REF="$1"

# Validate task ref format
if ! [[ "$TASK_REF" =~ ^[a-zA-Z0-9_-]+#[0-9]+$ ]]; then
    echo -e "${RED}Invalid task reference: ${TASK_REF}${NC}"
    echo "Expected format: project#N (e.g., myproject#18)"
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
WORKING_DIR="${WORKING_DIR:-$(pwd)}"

# Temporarily hide workflow state to prevent hook interference with child sessions
# Reviews are child processes - parent workflow state should not apply to them
WORKFLOW_STATE_DIR="${HOME}/.claude/workflow-state"
WORKFLOW_STATE_FILE="${WORKFLOW_STATE_DIR}/active_ralph_task.txt"
WORKFLOW_STATE_BACKUP="${WORKFLOW_STATE_DIR}/active_ralph_task.txt.bak"

# Only suspend if backup doesn't already exist (prevents overwriting on nested/interrupted runs)
if [[ -f "$WORKFLOW_STATE_FILE" ]]; then
    if [[ -f "$WORKFLOW_STATE_BACKUP" ]]; then
        echo -e "${YELLOW}Warning: backup already exists, skipping suspend (previous run interrupted?)${NC}"
    else
        mv "$WORKFLOW_STATE_FILE" "$WORKFLOW_STATE_BACKUP"
        echo -e "${YELLOW}Suspended parent workflow state${NC}"
    fi
fi

# Restore workflow state on exit (success or failure)
cleanup() {
    if [[ -f "$WORKFLOW_STATE_BACKUP" ]]; then
        mv "$WORKFLOW_STATE_BACKUP" "$WORKFLOW_STATE_FILE"
        echo -e "${YELLOW}Restored parent workflow state${NC}"
    fi
}
trap cleanup EXIT

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  REVIEWS FOR ${TASK_REF}${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

REVIEWS=(
    "ralph-review-code:Code Review (5 agents)"
    "ralph-review-simplify:Code Simplifier"
    "ralph-review-security:Security Review"
    "ralph-review-codex:Codex Review"
)

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CLAUDE_CMD="claude -p --model opus --dangerously-skip-permissions --verbose --output-format stream-json"

TOTAL=${#REVIEWS[@]}
CURRENT=0
COMPLETED=0
FAILED=0

# Arrays to store results for summary table
declare -a RESULT_NAMES
declare -a RESULT_STATUSES
declare -a RESULT_TIMES
declare -a RESULT_SIZES
declare -a RESULT_PATHS

for REVIEW_ENTRY in "${REVIEWS[@]}"; do
    REVIEW_CMD="${REVIEW_ENTRY%%:*}"
    REVIEW_NAME="${REVIEW_ENTRY##*:}"
    CURRENT=$((CURRENT + 1))

    LOG_FILE="${LOG_DIR}/${TASK_REF//#/_}_${REVIEW_CMD}_${TIMESTAMP}.log"

    echo -e "${CYAN}[${CURRENT}/${TOTAL}] ${REVIEW_NAME}${NC}"
    echo -e "  Command: /${REVIEW_CMD} ${TASK_REF}"
    echo -e "  Log: ${LOG_FILE}"

    START_TIME=$(date +%s)

    set +e
    cd "$WORKING_DIR"
    # < /dev/null prevents hang when running from another Claude session (no TTY)
    # See: https://github.com/anthropics/claude-code/issues/9026
    $CLAUDE_CMD "/${REVIEW_CMD} ${TASK_REF}" < /dev/null 2>&1 | python3 "$SCRIPT_DIR/stream-monitor.py" > "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_FMT=$(printf '%02d:%02d' $((DURATION/60)) $((DURATION%60)))
    LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo "0")

    # Store results for summary
    RESULT_NAMES+=("$REVIEW_NAME")
    RESULT_TIMES+=("$DURATION_FMT")
    RESULT_SIZES+=("$LOG_SIZE")
    RESULT_PATHS+=("$LOG_FILE")

    if [[ $EXIT_CODE -eq 0 ]]; then
        echo -e "  ${GREEN}✓ Completed${NC} [${DURATION_FMT}]\n"
        RESULT_STATUSES+=("✅ Completed")
        COMPLETED=$((COMPLETED + 1))
    else
        echo -e "  ${RED}✗ Failed (exit: ${EXIT_CODE})${NC} [${DURATION_FMT}]\n"
        RESULT_STATUSES+=("❌ Failed")
        FAILED=$((FAILED + 1))
    fi
done

# Print summary table
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 All ${COMPLETED}/${TOTAL} reviews completed successfully!${NC}\n"
else
    echo -e "${RED}⚠️  Completed: ${COMPLETED}/${TOTAL}, Failed: ${FAILED}${NC}\n"
fi

# Table header
echo -e "┌────────────────────────┬──────────────┬───────┬─────────────┐"
echo -e "│         Review         │    Status    │ Time  │  Log Size   │"
echo -e "├────────────────────────┼──────────────┼───────┼─────────────┤"

for i in "${!RESULT_NAMES[@]}"; do
    NAME="${RESULT_NAMES[$i]}"
    STATUS="${RESULT_STATUSES[$i]}"
    TIME="${RESULT_TIMES[$i]}"
    SIZE="${RESULT_SIZES[$i]}"

    # Format size with units
    if [[ $SIZE -ge 1024 ]]; then
        SIZE_FMT="$(( SIZE / 1024 )) KB"
    else
        SIZE_FMT="${SIZE} bytes"
    fi

    # Pad columns for alignment
    printf "│ %-22s │ %-12s │ %5s │ %11s │\n" "$NAME" "$STATUS" "$TIME" "$SIZE_FMT"

    if [[ $i -lt $((${#RESULT_NAMES[@]} - 1)) ]]; then
        echo -e "├────────────────────────┼──────────────┼───────┼─────────────┤"
    fi
done

echo -e "└────────────────────────┴──────────────┴───────┴─────────────┘"

# Print log file paths
echo -e "\n${CYAN}Log files:${NC}"
for i in "${!RESULT_NAMES[@]}"; do
    echo -e "  ${RESULT_NAMES[$i]}: ${RESULT_PATHS[$i]}"
done
echo ""

exit $FAILED
