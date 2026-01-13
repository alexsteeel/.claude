#!/bin/bash
#
# Ralph Implementation Loop with Recovery
# Runs /ralph-implement-python-task for each task with API recovery and Telegram notifications
#
# Usage: ./ralph-implement.sh <project> <task_numbers...>
# Example: ./ralph-implement.sh myproject 1 2 3
# Example: ./ralph-implement.sh myproject 1-4 6 8-10  (expands to 1 2 3 4 6 8 9 10)
#
# Features:
# - Automatic recovery on API errors (401/timeout/429) with delays
# - Context overflow detection with fresh session retry
# - Telegram notifications for pipeline status
# - Detailed failure diagnosis
#
# ⚠️  WARNING: This script uses --dangerously-skip-permissions flag!
#     Claude will execute commands without asking for confirmation.
#     Only run on trusted codebases in isolated environments.
#

set -e

# Script directory (for calling Python scripts)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

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

# Load .env configuration
load_env() {
    local env_file="${SCRIPT_DIR}/.env"
    if [[ -f "$env_file" ]]; then
        # Export variables from .env file
        set -a
        source "$env_file"
        set +a
    fi
}

load_env

# Configuration with defaults
RECOVERY_ENABLED="${RECOVERY_ENABLED:-true}"
# Default delays: 10, 20, 30 minutes
IFS=',' read -ra RECOVERY_DELAYS <<< "${RECOVERY_DELAYS:-600,1200,1800}"
CONTEXT_OVERFLOW_MAX_RETRIES="${CONTEXT_OVERFLOW_MAX_RETRIES:-2}"

# Notification helper
notify() {
    python3 "$SCRIPT_DIR/notify.py" "$@" 2>/dev/null || true
}

# Health check helper (returns exit code)
health_check() {
    python3 "$SCRIPT_DIR/health_check.py" "$@"
}

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

# Classify error from log file
# Returns: COMPLETED, AUTH_EXPIRED, API_TIMEOUT, RATE_LIMIT, OVERLOADED, CONTEXT_OVERFLOW, FORBIDDEN, UNKNOWN
classify_error() {
    local log_file="$1"

    # Success case
    if grep -q "I confirm that all task phases are fully completed" "$log_file" 2>/dev/null; then
        echo "COMPLETED"
        return
    fi

    # Context overflow - NOT recoverable (needs fresh session)
    if grep -q "Prompt is too long" "$log_file" 2>/dev/null; then
        echo "CONTEXT_OVERFLOW"
        return
    fi

    # Auth expired (401)
    if grep -qE "401|Unauthorized|authentication.*failed|AUTH_ERROR" "$log_file" 2>/dev/null; then
        echo "AUTH_EXPIRED"
        return
    fi

    # Rate limit (429)
    if grep -qE "429|rate.?limit|too.many.requests|RATE_LIMIT" "$log_file" 2>/dev/null; then
        echo "RATE_LIMIT"
        return
    fi

    # Overloaded (529)
    if grep -qE "529|overloaded|OVERLOADED" "$log_file" 2>/dev/null; then
        echo "OVERLOADED"
        return
    fi

    # API timeout (0 tokens)
    if grep -q "Tokens: 0 in / 0 out" "$log_file" 2>/dev/null; then
        echo "API_TIMEOUT"
        return
    fi

    # Forbidden (403) - NOT recoverable
    if grep -qE "403|Forbidden|FORBIDDEN" "$log_file" 2>/dev/null; then
        echo "FORBIDDEN"
        return
    fi

    # On hold (intentional stop)
    if grep -qE "status.*hold|## Blocks|→ hold" "$log_file" 2>/dev/null; then
        echo "ON_HOLD"
        return
    fi

    echo "UNKNOWN"
}

# Recovery loop - wait and check health
# Returns 0 if recovered, 1 if all attempts failed
recovery_loop() {
    local task_ref="$1"

    echo -e "\n${YELLOW}┌─────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}│ RECOVERY MODE${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────${NC}"

    local attempt=0
    local max_attempts=${#RECOVERY_DELAYS[@]}

    for delay in "${RECOVERY_DELAYS[@]}"; do
        attempt=$((attempt + 1))
        local delay_min=$((delay / 60))

        echo -e "\n${CYAN}Recovery attempt ${attempt}/${max_attempts} - waiting ${delay_min} minutes...${NC}"
        notify recovery_start --attempt "$attempt" --max-attempts "$max_attempts" --delay "$delay"

        sleep "$delay"

        echo -e "${CYAN}Running health check...${NC}"
        if health_check --verbose; then
            echo -e "${GREEN}✓ API is healthy!${NC}"
            notify recovery_success --task "$task_ref"
            return 0
        else
            echo -e "${YELLOW}API still unavailable${NC}"
        fi
    done

    echo -e "${RED}All recovery attempts failed${NC}"
    return 1
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
    echo "Options (via environment variables):"
    echo "  WORKING_DIR    Working directory for Claude (default: current directory)"
    echo "  MAX_BUDGET     Maximum budget in USD per task (default: no limit)"
    echo ""
    echo "Recovery settings (in .env file):"
    echo "  RECOVERY_ENABLED         Enable recovery loop (default: true)"
    echo "  RECOVERY_DELAYS          Delays in seconds, comma-separated (default: 600,1200,1800)"
    echo "  CONTEXT_OVERFLOW_MAX_RETRIES  Max fresh session retries (default: 2)"
    echo ""
    echo "Telegram notifications (in .env file):"
    echo "  TELEGRAM_BOT_TOKEN       Bot token from @BotFather"
    echo "  TELEGRAM_CHAT_ID         Chat/channel ID"
    echo ""
    echo "Examples:"
    echo "  $0 myproject 1 2 3"
    echo "  $0 myproject 1-4 6 8-10              # expands to 1 2 3 4 6 8 9 10"
    echo "  WORKING_DIR=/path/to/project $0 myproject 1-5"
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
EXPANDED=$(expand_ranges "$@")
read -ra TASKS <<< "$EXPANDED"

# Optional settings
WORKING_DIR="${WORKING_DIR:-$(pwd)}"
MAX_BUDGET="${MAX_BUDGET:-}"

print_header

echo -e "Project:     ${GREEN}${PROJECT}${NC}"
echo -e "Tasks:       ${GREEN}${TASKS[*]}${NC}"
echo -e "Mode:        ${CYAN}Autonomous (--print, no interaction)${NC}"
echo -e "Working dir: ${GREEN}${WORKING_DIR}${NC}"
echo -e "Recovery:    ${GREEN}${RECOVERY_ENABLED}${NC}"
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
declare -A FAILURE_REASONS

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_LOG="${LOG_DIR}/session_${PROJECT}_${TIMESTAMP}.log"
SESSION_START_TIME=$(date +%s)

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
    echo "Recovery:    ${RECOVERY_ENABLED}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "TASK EXECUTION LOG"
    echo "───────────────────────────────────────────────────────────────"
} > "$SESSION_LOG"

echo -e "Session log: ${GREEN}${SESSION_LOG}${NC}"
echo ""

# Send session start notification
notify session_start --project "$PROJECT" --tasks "${TASKS[*]}"

# Track pipeline stopped flag
PIPELINE_STOPPED=false

for TASK_NUM in "${TASKS[@]}"; do
    if [[ "$PIPELINE_STOPPED" == "true" ]]; then
        break
    fi

    CURRENT=$((CURRENT + 1))
    TASK_REF="${PROJECT}#${TASK_NUM}"
    LOG_FILE="${LOG_DIR}/${PROJECT}_${TASK_NUM}_${TIMESTAMP}.log"

    print_task_header "$TASK_REF" "$CURRENT" "$TOTAL"

    # Clean up any uncommitted changes from previous failed task
    cd "$WORKING_DIR"
    GIT_CHANGES=$(git status --porcelain 2>/dev/null || true)
    if [[ -n "$GIT_CHANGES" ]]; then
        echo -e "${YELLOW}┌─────────────────────────────────────────────────────────${NC}"
        echo -e "${YELLOW}│ Cleaning uncommitted changes from previous task${NC}"
        echo -e "${YELLOW}└─────────────────────────────────────────────────────────${NC}"
        git checkout -- . 2>/dev/null || true
        git clean -fd -e ".env*" -e "*.local" -e "*.local.*" 2>/dev/null || true
        echo -e "${GREEN}✓ Cleanup done${NC}\n"
    fi

    echo -e "Log file: ${LOG_FILE}"
    echo -e "Starting autonomous implementation...\n"

    # Record start time
    TASK_START_TIME=$(date +%s)
    TASK_START_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')

    # Initialize task log
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "Task: ${TASK_REF}"
        echo "Started: ${TASK_START_HUMAN}"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
    } > "$LOG_FILE"

    # Build Claude command
    CLAUDE_CMD="claude -p --model opus --verbose --output-format stream-json --dangerously-skip-permissions"
    if [[ -n "$MAX_BUDGET" ]]; then
        CLAUDE_CMD="$CLAUDE_CMD --max-budget-usd $MAX_BUDGET"
    fi

    # Task execution with recovery
    CONTEXT_OVERFLOW_RETRIES=0
    RECOVERY_NEEDED=false
    TASK_RESULT=""

    while true; do
        cd "$WORKING_DIR"

        # Build prompt (with recovery note if retrying)
        PROMPT="/ralph-implement-python-task ${TASK_REF}"
        if [[ "$RECOVERY_NEEDED" == "true" ]]; then
            PROMPT="$PROMPT

⚠️ RECOVERY NOTE: This task was partially executed before API interruption.
- Check \`git status\` and \`git diff\` for any uncommitted changes
- Review task status in md-task-mcp
- Continue from where the previous attempt stopped
- Do NOT redo already completed work"
        fi

        # Run Claude
        {
            echo ""
            if [[ "$RECOVERY_NEEDED" == "true" ]]; then
                echo "───────────────────────────────────────────────────────────────"
                echo "RETRY AFTER RECOVERY at $(date '+%Y-%m-%d %H:%M:%S')"
                echo "───────────────────────────────────────────────────────────────"
            fi
            echo ""
        } >> "$LOG_FILE"

        set +e
        eval "$CLAUDE_CMD \"$PROMPT\"" 2>&1 | python3 "$SCRIPT_DIR/stream-monitor.py" | tee -a "$LOG_FILE"
        EXIT_CODE=${PIPESTATUS[0]}
        set -e

        # Classify the result
        TASK_RESULT=$(classify_error "$LOG_FILE")

        case "$TASK_RESULT" in
            "COMPLETED")
                break
                ;;
            "ON_HOLD")
                break
                ;;
            "CONTEXT_OVERFLOW")
                CONTEXT_OVERFLOW_RETRIES=$((CONTEXT_OVERFLOW_RETRIES + 1))
                if [[ $CONTEXT_OVERFLOW_RETRIES -lt $CONTEXT_OVERFLOW_MAX_RETRIES ]]; then
                    print_warning "Context overflow - retrying with fresh session ($CONTEXT_OVERFLOW_RETRIES/$CONTEXT_OVERFLOW_MAX_RETRIES)"
                    notify context_overflow --task "$TASK_REF" --retry "$CONTEXT_OVERFLOW_RETRIES" --max-retries "$CONTEXT_OVERFLOW_MAX_RETRIES"
                    RECOVERY_NEEDED=true
                    continue
                else
                    print_error "Context overflow - max retries exceeded"
                    break
                fi
                ;;
            "AUTH_EXPIRED"|"API_TIMEOUT"|"RATE_LIMIT"|"OVERLOADED")
                if [[ "$RECOVERY_ENABLED" == "true" ]]; then
                    print_warning "Recoverable error: $TASK_RESULT"
                    notify task_failed --task "$TASK_REF" --reason "$TASK_RESULT"

                    if recovery_loop "$TASK_REF"; then
                        RECOVERY_NEEDED=true
                        continue
                    else
                        print_error "Recovery failed - stopping pipeline"
                        notify pipeline_stopped --reason "Recovery failed after $TASK_RESULT"
                        PIPELINE_STOPPED=true
                        break
                    fi
                else
                    print_error "Recoverable error but recovery disabled: $TASK_RESULT"
                    break
                fi
                ;;
            "FORBIDDEN")
                print_error "Fatal error: FORBIDDEN (403) - stopping pipeline"
                notify pipeline_stopped --reason "FORBIDDEN (403)"
                PIPELINE_STOPPED=true
                break
                ;;
            *)
                # Unknown error - try recovery if enabled
                if [[ "$RECOVERY_ENABLED" == "true" && $EXIT_CODE -ne 0 ]]; then
                    print_warning "Unknown error (exit code: $EXIT_CODE)"
                    notify task_failed --task "$TASK_REF" --reason "UNKNOWN_ERROR"

                    if recovery_loop "$TASK_REF"; then
                        RECOVERY_NEEDED=true
                        continue
                    fi
                fi
                break
                ;;
        esac
    done

    # Calculate duration
    TASK_END_TIME=$(date +%s)
    TASK_DURATION=$((TASK_END_TIME - TASK_START_TIME))
    TASK_DURATIONS["$TASK_REF"]=$TASK_DURATION
    DURATION_FMT=$(printf '%02d:%02d:%02d' $((TASK_DURATION/3600)) $((TASK_DURATION%3600/60)) $((TASK_DURATION%60)))

    TASK_END=$(date '+%Y-%m-%d %H:%M:%S')

    # Add footer to task log
    {
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "Finished: ${TASK_END}"
        echo "Duration: ${DURATION_FMT}"
        echo "Result: ${TASK_RESULT}"
        echo "═══════════════════════════════════════════════════════════════"
    } >> "$LOG_FILE"

    # Record result
    case "$TASK_RESULT" in
        "COMPLETED")
            print_success "Implementation completed for ${TASK_REF} [${DURATION_FMT}]"
            COMPLETED+=("$TASK_REF")
            echo "[${TASK_END}] ✓ ${TASK_REF} - COMPLETED (${DURATION_FMT})" >> "$SESSION_LOG"
            ;;
        "ON_HOLD")
            print_warning "Task ${TASK_REF} put ON HOLD [${DURATION_FMT}]"
            ON_HOLD+=("$TASK_REF")
            FAILURE_REASONS["$TASK_REF"]="ON_HOLD"
            echo "[${TASK_END}] ⚠ ${TASK_REF} - ON HOLD (${DURATION_FMT})" >> "$SESSION_LOG"
            ;;
        *)
            print_error "Task ${TASK_REF} failed: ${TASK_RESULT} [${DURATION_FMT}]"
            FAILED+=("$TASK_REF")
            FAILURE_REASONS["$TASK_REF"]="$TASK_RESULT"
            echo "[${TASK_END}] ✗ ${TASK_REF} - ${TASK_RESULT} (${DURATION_FMT})" >> "$SESSION_LOG"

            # Show last activity
            echo -e "\n${YELLOW}Last activity before failure:${NC}"
            grep -E "^\[|💻|📖|📝|✅|❌|🔍" "$LOG_FILE" 2>/dev/null | tail -5 || true
            echo ""
            ;;
    esac

    echo "  Log: ${LOG_FILE}" >> "$SESSION_LOG"
done

# Calculate total duration
SESSION_END_TIME=$(date +%s)
TOTAL_DURATION=$((SESSION_END_TIME - SESSION_START_TIME))
TOTAL_DURATION_FMT=$(printf '%02d:%02d:%02d' $((TOTAL_DURATION/3600)) $((TOTAL_DURATION%3600/60)) $((TOTAL_DURATION%60)))

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

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
        reason=${FAILURE_REASONS[$task]}
        echo -e "  ✗ $task — ${reason}  ${CYAN}${dur_fmt}${NC}"
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
            reason=${FAILURE_REASONS[$task]}
            echo "  ✗ $task — ${reason}  ($dur_fmt)"
        done
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
} >> "$SESSION_LOG"

echo -e "Session log: ${GREEN}${SESSION_LOG}${NC}"

# Send session complete notification
COMPLETED_NUMS=""
FAILED_NUMS=""
FAILED_REASONS_STR=""
for task in "${COMPLETED[@]}"; do
    num="${task#*#}"
    COMPLETED_NUMS="${COMPLETED_NUMS},${num}"
done
for task in "${FAILED[@]}"; do
    num="${task#*#}"
    reason=${FAILURE_REASONS[$task]}
    FAILED_NUMS="${FAILED_NUMS},${num}"
    FAILED_REASONS_STR="${FAILED_REASONS_STR},${reason}"
done
COMPLETED_NUMS="${COMPLETED_NUMS#,}"
FAILED_NUMS="${FAILED_NUMS#,}"
FAILED_REASONS_STR="${FAILED_REASONS_STR#,}"

notify session_complete --project "$PROJECT" --duration "$TOTAL_DURATION_FMT" \
    --completed "$COMPLETED_NUMS" --failed "$FAILED_NUMS" --failed-reasons "$FAILED_REASONS_STR"

echo ""

# Run batch check if there are completed tasks and pipeline not stopped
if [[ ${#COMPLETED[@]} -gt 0 && "$PIPELINE_STOPPED" != "true" ]]; then
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  BATCH CHECK${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

    TASK_REFS=""
    for task in "${COMPLETED[@]}"; do
        TASK_REFS="${TASK_REFS} ${task}"
    done
    TASK_REFS="${TASK_REFS# }"

    BATCH_LOG="${LOG_DIR}/batch_check_${PROJECT}_${TIMESTAMP}.log"
    echo -e "Running batch check for: ${GREEN}${TASK_REFS}${NC}"
    echo -e "Log: ${GREEN}${BATCH_LOG}${NC}\n"

    BATCH_START_TIME=$(date +%s)

    cd "$WORKING_DIR"
    $CLAUDE_CMD "/ralph-batch-check ${TASK_REFS}" 2>&1 | python3 "$SCRIPT_DIR/stream-monitor.py" | tee "$BATCH_LOG"

    BATCH_END_TIME=$(date +%s)
    BATCH_DURATION=$((BATCH_END_TIME - BATCH_START_TIME))
    BATCH_DURATION_FMT=$(printf '%02d:%02d:%02d' $((BATCH_DURATION/3600)) $((BATCH_DURATION%3600/60)) $((BATCH_DURATION%60)))

    echo -e "\n${GREEN}Batch check completed in ${BATCH_DURATION_FMT}${NC}"

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

# Exit with error if any tasks failed or pipeline stopped
if [[ ${#FAILED[@]} -gt 0 || "$PIPELINE_STOPPED" == "true" ]]; then
    exit 1
fi
