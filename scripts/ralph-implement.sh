#!/bin/bash
#
# Ralph Implementation Loop
# Runs /ralph-implement-python-task for each task sequentially in autonomous mode
#
# Usage: ./ralph-implement.sh <project> <task_numbers...>
# Example: ./ralph-implement.sh myproject 1 2 3
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
declare -A TASK_DURATIONS

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_LOG="${LOG_DIR}/session_${PROJECT}_${TIMESTAMP}.log"

# Initialize session log
{
    echo "═══════════════════════════════════════════════════════════════"
    echo "RALPH IMPLEMENTATION SESSION"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Started:     $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Project:     ${PROJECT}"
    echo "Tasks:       ${TASKS[*]}"
    echo "Working dir: ${WORKING_DIR}"
    echo "Max budget:  ${MAX_BUDGET:-unlimited}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "TASK EXECUTION LOG"
    echo "───────────────────────────────────────────────────────────────"
} > "$SESSION_LOG"

echo -e "Session log: ${GREEN}${SESSION_LOG}${NC}"
echo ""

for TASK_NUM in "${TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    TASK_REF="${PROJECT}#${TASK_NUM}"
    LOG_FILE="${LOG_DIR}/${PROJECT}_${TASK_NUM}_${TIMESTAMP}.log"

    print_task_header "$TASK_REF" "$CURRENT" "$TOTAL"

    echo -e "Log file: ${LOG_FILE}"
    echo -e "Starting autonomous implementation...\n"

    # Record start time
    TASK_START_TIME=$(date +%s)
    TASK_START_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')

    # Initialize task log with header
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "Task: ${TASK_REF}"
        echo "Started: ${TASK_START_HUMAN}"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
    } > "$LOG_FILE"

    # Build Claude command
    # Use stream-json to force stdout output (bypasses /dev/tty)
    # Note: stream-json requires --verbose flag
    CLAUDE_CMD="claude -p --model opus --verbose --output-format stream-json"

    if [[ -n "$MAX_BUDGET" ]]; then
        CLAUDE_CMD="$CLAUDE_CMD --max-budget-usd $MAX_BUDGET"
    fi

    # Add permission bypass for autonomous mode
    CLAUDE_CMD="$CLAUDE_CMD --dangerously-skip-permissions"

    # Run Claude in print mode (autonomous)
    # Use script to capture terminal output (Claude writes to /dev/tty, not stdout)
    cd "$WORKING_DIR"

    set +e  # Don't exit on error
    # Formatted output to both terminal and log file
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
    $CLAUDE_CMD "/ralph-implement-python-task ${TASK_REF}" 2>&1 | python3 "$SCRIPT_DIR/format-output.py" | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    # Calculate duration
    TASK_END_TIME=$(date +%s)
    TASK_DURATION=$((TASK_END_TIME - TASK_START_TIME))
    TASK_DURATIONS["$TASK_REF"]=$TASK_DURATION

    # Format duration as HH:MM:SS
    DURATION_FMT=$(printf '%02d:%02d:%02d' $((TASK_DURATION/3600)) $((TASK_DURATION%3600/60)) $((TASK_DURATION%60)))

    # Check result and log to session
    TASK_END=$(date '+%Y-%m-%d %H:%M:%S')

    # Add footer to task log
    {
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Finished: ${TASK_END}"
        echo "Duration: ${DURATION_FMT}"
        echo "Exit code: ${EXIT_CODE}"
        echo "═══════════════════════════════════════════════════════════════"
    } >> "$LOG_FILE"
    if [[ $EXIT_CODE -eq 0 ]]; then
        # Check if task was put on hold (look for hold markers in log)
        # In formatted logs, look for task update with hold status or Blocks mention
        if grep -qi 'update_task.*hold' "$LOG_FILE" 2>/dev/null || grep -q '## Blocks' "$LOG_FILE" 2>/dev/null || grep -q '→ hold' "$LOG_FILE" 2>/dev/null; then
            print_warning "Task ${TASK_REF} put ON HOLD (blocked) [${DURATION_FMT}]"
            ON_HOLD+=("$TASK_REF")
            echo "[${TASK_END}] ⚠ ${TASK_REF} - ON HOLD (${DURATION_FMT})" >> "$SESSION_LOG"
        # Check if task was properly completed (confirmation phrase present)
        elif grep -q "I confirm that all task phases are fully completed" "$LOG_FILE" 2>/dev/null; then
            print_success "Implementation completed for ${TASK_REF} [${DURATION_FMT}]"
            COMPLETED+=("$TASK_REF")
            echo "[${TASK_END}] ✓ ${TASK_REF} - COMPLETED (${DURATION_FMT})" >> "$SESSION_LOG"
        else
            # Exit code 0 but no confirmation - task may be incomplete
            print_warning "Task ${TASK_REF} incomplete (no confirmation phrase) [${DURATION_FMT}]"
            ON_HOLD+=("$TASK_REF")
            echo "[${TASK_END}] ⚠ ${TASK_REF} - INCOMPLETE (${DURATION_FMT})" >> "$SESSION_LOG"
        fi
    else
        print_error "Implementation failed for ${TASK_REF} (exit code: $EXIT_CODE) [${DURATION_FMT}]"
        FAILED+=("$TASK_REF")
        echo "[${TASK_END}] ✗ ${TASK_REF} - FAILED (${DURATION_FMT})" >> "$SESSION_LOG"
    fi

    echo "  Log: ${LOG_FILE}" >> "$SESSION_LOG"
    echo ""
done

# Calculate total duration
TOTAL_DURATION=0
for duration in "${TASK_DURATIONS[@]}"; do
    TOTAL_DURATION=$((TOTAL_DURATION + duration))
done
TOTAL_DURATION_FMT=$(printf '%02d:%02d:%02d' $((TOTAL_DURATION/3600)) $((TOTAL_DURATION%3600/60)) $((TOTAL_DURATION%60)))

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Format duration helper
format_duration() {
    local secs=$1
    printf '%02d:%02d:%02d' $((secs/3600)) $((secs%3600/60)) $((secs%60))
}

if [[ ${#COMPLETED[@]} -gt 0 ]]; then
    echo -e "${GREEN}Completed (${#COMPLETED[@]}):${NC}"
    for task in "${COMPLETED[@]}"; do
        dur=${TASK_DURATIONS[$task]}
        dur_fmt=$(format_duration $dur)
        echo -e "  ✓ $task  ${CYAN}${dur_fmt}${NC}"
    done
fi

if [[ ${#ON_HOLD[@]} -gt 0 ]]; then
    echo -e "${YELLOW}On Hold (${#ON_HOLD[@]}):${NC}"
    for task in "${ON_HOLD[@]}"; do
        dur=${TASK_DURATIONS[$task]}
        dur_fmt=$(format_duration $dur)
        echo -e "  ⚠ $task  ${CYAN}${dur_fmt}${NC}"
    done
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo -e "${RED}Failed (${#FAILED[@]}):${NC}"
    for task in "${FAILED[@]}"; do
        dur=${TASK_DURATIONS[$task]}
        dur_fmt=$(format_duration $dur)
        echo -e "  ✗ $task  ${CYAN}${dur_fmt}${NC}"
    done
fi

echo ""
echo -e "Total time:  ${CYAN}${TOTAL_DURATION_FMT}${NC}"
echo -e "Logs:        ${GREEN}${LOG_DIR}/${NC}"
echo ""

# Write final summary to session log
{
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "SESSION SUMMARY"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
    echo "Finished:    $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Total time:  ${TOTAL_DURATION_FMT}"
    echo ""
    echo "Results:"
    echo "  Completed: ${#COMPLETED[@]}"
    echo "  On Hold:   ${#ON_HOLD[@]}"
    echo "  Failed:    ${#FAILED[@]}"
    echo ""
    if [[ ${#COMPLETED[@]} -gt 0 ]]; then
        echo "Completed tasks:"
        for task in "${COMPLETED[@]}"; do
            dur_fmt=$(format_duration ${TASK_DURATIONS[$task]})
            echo "  ✓ $task  ($dur_fmt)"
        done
    fi
    if [[ ${#ON_HOLD[@]} -gt 0 ]]; then
        echo "On hold tasks:"
        for task in "${ON_HOLD[@]}"; do
            dur_fmt=$(format_duration ${TASK_DURATIONS[$task]})
            echo "  ⚠ $task  ($dur_fmt)"
        done
    fi
    if [[ ${#FAILED[@]} -gt 0 ]]; then
        echo "Failed tasks:"
        for task in "${FAILED[@]}"; do
            dur_fmt=$(format_duration ${TASK_DURATIONS[$task]})
            echo "  ✗ $task  ($dur_fmt)"
        done
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
} >> "$SESSION_LOG"

echo -e "Session log: ${GREEN}${SESSION_LOG}${NC}"
echo ""

# Exit with error if any tasks failed
if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi

# Run batch check if there are completed tasks
if [[ ${#COMPLETED[@]} -gt 0 ]]; then
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  BATCH CHECK${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

    # Build task refs string (e.g., "project#1 project#2 project#3")
    TASK_REFS=""
    for task in "${COMPLETED[@]}"; do
        TASK_REFS="${TASK_REFS} ${task}"
    done
    TASK_REFS="${TASK_REFS# }"  # Trim leading space

    BATCH_LOG="${LOG_DIR}/batch_check_${PROJECT}_${TIMESTAMP}.log"
    echo -e "Running batch check for: ${GREEN}${TASK_REFS}${NC}"
    echo -e "Log: ${GREEN}${BATCH_LOG}${NC}\n"

    BATCH_START_TIME=$(date +%s)

    # Run batch check
    cd "$WORKING_DIR"
    $CLAUDE_CMD "/ralph-batch-check ${TASK_REFS}" 2>&1 | python3 "$SCRIPT_DIR/format-output.py" | tee "$BATCH_LOG"

    BATCH_END_TIME=$(date +%s)
    BATCH_DURATION=$((BATCH_END_TIME - BATCH_START_TIME))
    BATCH_DURATION_FMT=$(printf '%02d:%02d:%02d' $((BATCH_DURATION/3600)) $((BATCH_DURATION%3600/60)) $((BATCH_DURATION%60)))

    echo -e "\n${GREEN}Batch check completed in ${BATCH_DURATION_FMT}${NC}"

    # Log to session
    {
        echo ""
        echo "───────────────────────────────────────────────────────────────"
        echo "BATCH CHECK"
        echo "───────────────────────────────────────────────────────────────"
        echo "Tasks checked: ${TASK_REFS}"
        echo "Duration: ${BATCH_DURATION_FMT}"
        echo "Log: ${BATCH_LOG}"
    } >> "$SESSION_LOG"
fi
