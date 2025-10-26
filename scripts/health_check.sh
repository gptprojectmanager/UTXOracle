#!/bin/bash
#
# UTXOracle Infrastructure Health Check Script
#
# Spec: 003-mempool-integration-refactor
# Task: T097 - Production health monitoring
#
# Checks status of:
#   1. Docker Stack (mempool.space)
#   2. FastAPI Service (utxoracle-api)
#   3. Cron Job (daily_analysis)
#   4. DuckDB Database
#   5. Logs
#
# Exit codes:
#   0 = All systems operational
#   1 = Warnings detected
#   2 = Critical failures
#
# Usage:
#   ./health_check.sh              # Full health check
#   ./health_check.sh --quiet      # Only show issues
#   ./health_check.sh --json       # JSON output

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Paths
DUCKDB_PATH="${DUCKDB_PATH:-/media/sam/2TB-NVMe/prod/apps/utxoracle/data/utxoracle_cache.db}"
CRON_FILE="/etc/cron.d/utxoracle-analysis"
LOG_FILE="/media/sam/2TB-NVMe/prod/apps/utxoracle/logs/daily_analysis.log"
ELECTRS_DATA_DIR="/media/sam/2TB-NVMe/prod/apps/mempool-stack/data/electrs"

# Expected values
EXPECTED_ELECTRS_SIZE_GB=38
EXPECTED_DB_MIN_SIZE_KB=100
MAX_LOG_SIZE_GB=1

# Status tracking
declare -a WARNINGS=()
declare -a ERRORS=()
QUIET_MODE=false
JSON_MODE=false

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    if [ "$QUIET_MODE" = false ] && [ "$JSON_MODE" = false ]; then
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}$1${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

status_ok() {
    if [ "$JSON_MODE" = false ]; then
        echo -e "  ${GREEN}✅ OK${NC}     $1"
    fi
}

status_warning() {
    WARNINGS+=("$1")
    if [ "$JSON_MODE" = false ]; then
        echo -e "  ${YELLOW}⚠️  WARN${NC}  $1"
    fi
}

status_error() {
    ERRORS+=("$1")
    if [ "$JSON_MODE" = false ]; then
        echo -e "  ${RED}❌ FAIL${NC}  $1"
    fi
}

human_size() {
    local size=$1
    if [ "$size" -gt 1073741824 ]; then
        echo "$(( size / 1073741824 ))GB"
    elif [ "$size" -gt 1048576 ]; then
        echo "$(( size / 1048576 ))MB"
    elif [ "$size" -gt 1024 ]; then
        echo "$(( size / 1024 ))KB"
    else
        echo "${size}B"
    fi
}

# =============================================================================
# Check 1: Docker Stack (mempool.space)
# =============================================================================

check_docker_stack() {
    print_header "1. Docker Stack (mempool.space)"

    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        status_error "Docker not installed"
        return
    fi

    # Check expected containers
    local containers=("mempool-web" "mempool-api" "mempool-db" "mempool-electrs")
    local all_running=true

    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            # Check health status
            local health_obj=$(docker inspect --format='{{.State.Health}}' "$container" 2>/dev/null | tr -d '\n')
            local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null | tr -d '\n' || echo "unknown")

            # Determine health status
            local health="N/A"
            if [ "$health_obj" = "<nil>" ] || [ -z "$health_obj" ]; then
                # No healthcheck defined - check if container is just running
                health="N/A"
            else
                # Parse health status
                health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null | tr -d '\n' || echo "unknown")
            fi

            if [ "$status" = "running" ]; then
                if [ "$health" = "healthy" ] || [ "$health" = "N/A" ]; then
                    status_ok "$container: running (health: ${health})"
                else
                    status_warning "$container: running but unhealthy (health: ${health})"
                    all_running=false
                fi
            else
                status_error "$container: not running (status: ${status})"
                all_running=false
            fi
        else
            status_error "$container: container not found"
            all_running=false
        fi
    done

    # Check electrs disk usage
    if [ -d "$ELECTRS_DATA_DIR" ]; then
        local size_bytes=$(du -sb "$ELECTRS_DATA_DIR" 2>/dev/null | cut -f1 || echo "0")
        local size_gb=$(( size_bytes / 1073741824 ))
        local size_human=$(human_size "$size_bytes")

        if [ "$size_gb" -ge "$EXPECTED_ELECTRS_SIZE_GB" ]; then
            status_ok "electrs database: ${size_human} (fully synced)"
        elif [ "$size_gb" -ge 10 ]; then
            status_warning "electrs database: ${size_human} (syncing... expected ~${EXPECTED_ELECTRS_SIZE_GB}GB)"
        else
            status_error "electrs database: ${size_human} (sync incomplete or failed)"
        fi
    else
        status_error "electrs data directory not found: $ELECTRS_DATA_DIR"
    fi
}

# =============================================================================
# Check 2: FastAPI Service (utxoracle-api)
# =============================================================================

check_fastapi_service() {
    print_header "2. FastAPI Service (utxoracle-api)"

    # Check systemd service status
    if systemctl is-active --quiet utxoracle-api; then
        local uptime=$(systemctl show utxoracle-api --property=ActiveEnterTimestamp --value)
        status_ok "systemd service: active (started: $uptime)"
    else
        status_error "systemd service: inactive or failed"
        return
    fi

    # Check health endpoint
    local health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

    if [ "$health_response" = "200" ]; then
        # Get detailed health info
        local health_json=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
        local api_status=$(echo "$health_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
        local uptime_seconds=$(echo "$health_json" | python3 -c "import sys, json; print(int(json.load(sys.stdin).get('uptime_seconds', 0)))" 2>/dev/null || echo "0")
        local uptime_human=$(printf '%dd %dh %dm' $((uptime_seconds/86400)) $((uptime_seconds%86400/3600)) $((uptime_seconds%3600/60)))

        if [ "$api_status" = "healthy" ]; then
            status_ok "API health endpoint: HTTP 200 (status: healthy, uptime: $uptime_human)"
        else
            status_warning "API health endpoint: HTTP 200 (status: $api_status)"
        fi
    else
        status_error "API health endpoint: HTTP $health_response (unreachable)"
    fi

    # Check memory usage
    if systemctl is-active --quiet utxoracle-api; then
        local pid=$(systemctl show utxoracle-api --property=MainPID --value)
        if [ "$pid" != "0" ] && [ -n "$pid" ]; then
            local mem_kb=$(ps -o rss= -p "$pid" 2>/dev/null || echo "0")
            local mem_mb=$(( mem_kb / 1024 ))

            if [ "$mem_mb" -lt 500 ]; then
                status_ok "Memory usage: ${mem_mb}MB (PID: $pid)"
            elif [ "$mem_mb" -lt 1000 ]; then
                status_warning "Memory usage: ${mem_mb}MB (high, but acceptable)"
            else
                status_warning "Memory usage: ${mem_mb}MB (very high, check for leaks)"
            fi
        fi
    fi
}

# =============================================================================
# Check 3: Cron Job (daily_analysis)
# =============================================================================

check_cron_job() {
    print_header "3. Cron Job (daily_analysis)"

    # Check if cron file exists
    if [ -f "$CRON_FILE" ]; then
        status_ok "Cron file exists: $CRON_FILE"
    else
        status_error "Cron file not found: $CRON_FILE"
        return
    fi

    # Check if cron service is running
    if systemctl is-active --quiet cron; then
        status_ok "Cron service: active"
    else
        status_error "Cron service: inactive"
    fi

    # Check recent log entries (last 30 minutes)
    if [ -f "$LOG_FILE" ]; then
        local thirty_min_ago=$(date -d '30 minutes ago' '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -v-30M '+%Y-%m-%d %H:%M:%S')
        local recent_entries=$(grep -c "$(date '+%Y-%m-%d %H:' -d '30 minutes ago' 2>/dev/null || date -v-30M '+%Y-%m-%d %H:')" "$LOG_FILE" 2>/dev/null || echo "0")

        if [ "$recent_entries" -gt 0 ]; then
            status_ok "Recent log activity: $recent_entries entries in last 30 minutes"
        else
            status_warning "No recent log activity (last 30 minutes) - check if cron is running"
        fi

        # Check for recent errors
        local recent_errors=$(tail -n 100 "$LOG_FILE" 2>/dev/null | grep -c -i "error\|exception\|failed" || echo "0")
        if [ "$recent_errors" -eq 0 ]; then
            status_ok "No recent errors in log (last 100 lines)"
        else
            status_warning "Found $recent_errors error lines in recent logs"
        fi
    else
        status_warning "Log file not found: $LOG_FILE (cron may not have run yet)"
    fi
}

# =============================================================================
# Check 4: DuckDB Database
# =============================================================================

check_duckdb() {
    print_header "4. DuckDB Database"

    # Check if database file exists
    if [ -f "$DUCKDB_PATH" ]; then
        local size_bytes=$(stat -c%s "$DUCKDB_PATH" 2>/dev/null || stat -f%z "$DUCKDB_PATH" 2>/dev/null || echo "0")
        local size_human=$(human_size "$size_bytes")
        local size_kb=$(( size_bytes / 1024 ))

        if [ "$size_kb" -ge "$EXPECTED_DB_MIN_SIZE_KB" ]; then
            status_ok "Database file: exists ($size_human)"
        else
            status_warning "Database file: very small ($size_human) - may be empty"
        fi
    else
        status_error "Database file not found: $DUCKDB_PATH"
        return
    fi

    # Query database (requires python3 with duckdb)
    if command -v python3 &> /dev/null; then
        local query_result=$(python3 -c "
import duckdb
import sys
from datetime import datetime, timedelta

try:
    conn = duckdb.connect('$DUCKDB_PATH', read_only=True)

    # Row count
    row_count = conn.execute('SELECT COUNT(*) FROM prices').fetchone()[0]
    print(f'rows:{row_count}')

    # Most recent timestamp
    if row_count > 0:
        recent = conn.execute('SELECT MAX(timestamp) FROM prices').fetchone()[0]
        print(f'recent:{recent}')

    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'error:{e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)

        if echo "$query_result" | grep -q "^rows:"; then
            local row_count=$(echo "$query_result" | grep "^rows:" | cut -d: -f2)
            local recent_ts=$(echo "$query_result" | grep "^recent:" | cut -d: -f2- | tr -d ' ')

            if [ "$row_count" -gt 0 ]; then
                status_ok "Row count: $row_count entries"
            else
                status_warning "Row count: 0 (database empty, wait for cron)"
            fi

            if [ -n "$recent_ts" ]; then
                # Check if recent data (last 20 minutes)
                local now_epoch=$(date +%s)
                local recent_epoch=$(date -d "$recent_ts" +%s 2>/dev/null || echo "0")
                local age_minutes=$(( (now_epoch - recent_epoch) / 60 ))

                if [ "$age_minutes" -le 20 ]; then
                    status_ok "Most recent data: $recent_ts (${age_minutes} minutes ago)"
                else
                    status_warning "Most recent data: $recent_ts (${age_minutes} minutes ago - stale)"
                fi
            fi
        else
            status_error "Failed to query database: $(echo "$query_result" | grep "^error:" | cut -d: -f2-)"
        fi
    else
        status_warning "Python3 not available - skipping database queries"
    fi
}

# =============================================================================
# Check 5: Logs
# =============================================================================

check_logs() {
    print_header "5. Logs"

    local logs_dir="/media/sam/2TB-NVMe/prod/apps/utxoracle/logs"

    if [ -d "$logs_dir" ]; then
        status_ok "Logs directory exists: $logs_dir"

        # Check total size
        local total_size_bytes=$(du -sb "$logs_dir" 2>/dev/null | cut -f1 || echo "0")
        local total_size_gb=$(( total_size_bytes / 1073741824 ))
        local total_size_human=$(human_size "$total_size_bytes")

        if [ "$total_size_gb" -lt "$MAX_LOG_SIZE_GB" ]; then
            status_ok "Total log size: $total_size_human (<${MAX_LOG_SIZE_GB}GB)"
        else
            status_warning "Total log size: $total_size_human (>${MAX_LOG_SIZE_GB}GB - consider rotation)"
        fi

        # List log files and check for errors
        local log_files=$(find "$logs_dir" -type f -name "*.log" 2>/dev/null)
        if [ -n "$log_files" ]; then
            local file_count=$(echo "$log_files" | wc -l)
            status_ok "Log files: $file_count found"

            # Show last 5 errors across all logs
            if [ "$QUIET_MODE" = false ] && [ "$JSON_MODE" = false ]; then
                local errors=$(grep -h -i "error\|exception\|failed" $log_files 2>/dev/null | tail -n 5 || echo "")
                if [ -n "$errors" ]; then
                    echo ""
                    echo "  Last 5 error lines:"
                    echo "$errors" | while IFS= read -r line; do
                        echo -e "    ${RED}→${NC} $line"
                    done
                fi
            fi
        else
            status_warning "No log files found in $logs_dir"
        fi
    else
        status_error "Logs directory not found: $logs_dir"
    fi
}

# =============================================================================
# Summary & Exit
# =============================================================================

print_summary() {
    if [ "$JSON_MODE" = true ]; then
        # JSON output
        local error_count=${#ERRORS[@]}
        local warning_count=${#WARNINGS[@]}

        cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$([ $error_count -eq 0 ] && [ $warning_count -eq 0 ] && echo "healthy" || [ $error_count -eq 0 ] && echo "degraded" || echo "unhealthy")",
  "checks": {
    "docker_stack": true,
    "fastapi_service": true,
    "cron_job": true,
    "duckdb": true,
    "logs": true
  },
  "summary": {
    "errors": $error_count,
    "warnings": $warning_count
  },
  "issues": {
    "errors": $(printf '%s\n' "${ERRORS[@]}" | jq -R . | jq -s . 2>/dev/null || echo "[]"),
    "warnings": $(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s . 2>/dev/null || echo "[]")
  }
}
EOF
    else
        # Human-readable summary
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}Summary${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        local error_count=${#ERRORS[@]}
        local warning_count=${#WARNINGS[@]}

        if [ $error_count -eq 0 ] && [ $warning_count -eq 0 ]; then
            echo -e "  ${GREEN}✅ All systems operational${NC}"
            echo ""
            return 0
        fi

        if [ $error_count -gt 0 ]; then
            echo -e "  ${RED}❌ Critical failures: $error_count${NC}"
            for err in "${ERRORS[@]}"; do
                echo -e "     - $err"
            done
            echo ""
        fi

        if [ $warning_count -gt 0 ]; then
            echo -e "  ${YELLOW}⚠️  Warnings: $warning_count${NC}"
            for warn in "${WARNINGS[@]}"; do
                echo -e "     - $warn"
            done
            echo ""
        fi

        # Exit code
        if [ $error_count -gt 0 ]; then
            return 2
        elif [ $warning_count -gt 0 ]; then
            return 1
        else
            return 0
        fi
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quiet|-q)
                QUIET_MODE=true
                shift
                ;;
            --json|-j)
                JSON_MODE=true
                shift
                ;;
            --help|-h)
                cat <<EOF
UTXOracle Infrastructure Health Check

Usage:
  $0 [OPTIONS]

Options:
  --quiet, -q    Only show issues (warnings and errors)
  --json, -j     Output results as JSON
  --help, -h     Show this help message

Exit Codes:
  0 = All systems operational
  1 = Warnings detected
  2 = Critical failures

Examples:
  $0                  # Full health check
  $0 --quiet          # Only show problems
  $0 --json           # JSON output for monitoring systems
EOF
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Print header
    if [ "$QUIET_MODE" = false ] && [ "$JSON_MODE" = false ]; then
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║  UTXOracle Infrastructure Health Check (T097)             ║${NC}"
        echo -e "${BLUE}║  Spec: 003-mempool-integration-refactor                   ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    fi

    # Run checks
    check_docker_stack
    check_fastapi_service
    check_cron_job
    check_duckdb
    check_logs

    # Print summary and exit
    print_summary
    exit $?
}

# Run main
main "$@"
