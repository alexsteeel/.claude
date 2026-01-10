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
    $CLAUDE_CMD "/${REVIEW_CMD} ${TASK_REF}" 2>&1 | python3 "$SCRIPT_DIR/format-output.py" | tee "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_FMT=$(printf '%02d:%02d' $((DURATION/60)) $((DURATION%60)))

    if [[ $EXIT_CODE -eq 0 ]]; then
        echo -e "  ${GREEN}✓ Completed${NC} [${DURATION_FMT}]\n"
        COMPLETED=$((COMPLETED + 1))
    else
        echo -e "  ${RED}✗ Failed (exit: ${EXIT_CODE})${NC} [${DURATION_FMT}]\n"
        FAILED=$((FAILED + 1))
    fi
done

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Completed: ${COMPLETED}/${TOTAL}${NC}"
if [[ $FAILED -gt 0 ]]; then
    echo -e "${RED}Failed: ${FAILED}${NC}"
fi
echo ""

exit $FAILED
