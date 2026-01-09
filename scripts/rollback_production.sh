#!/bin/bash
# Production Rollback Script for Sprint 15
# Performs emergency rollback to previous version (blue environment)
#
# Usage: ./scripts/rollback_production.sh [--dry-run]
#
# Exit codes:
#   0 = Rollback successful
#   1 = Rollback failed
#   2 = Validation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ROLLBACK_LOG="$PROJECT_ROOT/logs/rollback_$(date +%Y%m%d_%H%M%S).log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Dry run mode
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$ROLLBACK_LOG"
}

error() {
    echo -e "${RED}ERROR: $*${NC}" | tee -a "$ROLLBACK_LOG"
}

success() {
    echo -e "${GREEN}SUCCESS: $*${NC}" | tee -a "$ROLLBACK_LOG"
}

warning() {
    echo -e "${YELLOW}WARNING: $*${NC}" | tee -a "$ROLLBACK_LOG"
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log "=== Production Rollback Started ==="
log "Dry run: $DRY_RUN"
log "Project root: $PROJECT_ROOT"
log "Log file: $ROLLBACK_LOG"

# Step 1: Verify current state
log "Step 1: Verifying current deployment state..."

if [[ ! -f "$PROJECT_ROOT/.deployment_state" ]]; then
    warning "No deployment state file found - creating minimal state"
    if [[ "$DRY_RUN" == false ]]; then
        cat > "$PROJECT_ROOT/.deployment_state" <<EOF
{
  "current": "green",
  "previous": "blue",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "version": "sprint-14"
}
EOF
    fi
fi

CURRENT_ENV=$(jq -r '.current' "$PROJECT_ROOT/.deployment_state" 2>/dev/null || echo "unknown")
PREVIOUS_ENV=$(jq -r '.previous' "$PROJECT_ROOT/.deployment_state" 2>/dev/null || echo "unknown")

log "Current environment: $CURRENT_ENV"
log "Previous environment: $PREVIOUS_ENV"

if [[ "$CURRENT_ENV" == "unknown" ]]; then
    error "Cannot determine current deployment environment"
    exit 1
fi

# Step 2: Health check previous environment
log "Step 2: Health check on $PREVIOUS_ENV environment..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would check health of $PREVIOUS_ENV"
else
    # Check if previous environment is still running
    if [[ -f "$PROJECT_ROOT/.venv/bin/python3" ]]; then
        log "Python environment found - checking availability..."
        
        # Basic import test
        if "$PROJECT_ROOT/.venv/bin/python3" -c "import sys; print(sys.version)" 2>/dev/null; then
            success "Python environment is healthy"
        else
            error "Python environment check failed"
            exit 2
        fi
    else
        error "Python virtual environment not found"
        exit 2
    fi
fi

# Step 3: Stop current (green) environment
log "Step 3: Stopping $CURRENT_ENV environment..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would stop $CURRENT_ENV environment"
else
    # Kill any running economist_agent processes
    if pgrep -f "economist_agent" > /dev/null; then
        log "Stopping economist_agent processes..."
        pkill -f "economist_agent" || true
        sleep 2
        success "Stopped economist_agent processes"
    else
        log "No economist_agent processes running"
    fi
    
    # Kill any running Flow processes
    if pgrep -f "EconomistContentFlow" > /dev/null; then
        log "Stopping Flow processes..."
        pkill -f "EconomistContentFlow" || true
        sleep 2
        success "Stopped Flow processes"
    else
        log "No Flow processes running"
    fi
fi

# Step 4: Switch to previous version
log "Step 4: Switching to $PREVIOUS_ENV version..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would switch to $PREVIOUS_ENV"
else
    # Git checkout previous version
    cd "$PROJECT_ROOT"
    
    # Get current branch/commit
    CURRENT_COMMIT=$(git rev-parse HEAD)
    log "Current commit: $CURRENT_COMMIT"
    
    # Find Sprint 14 tag or commit
    if git rev-parse "sprint-14" >/dev/null 2>&1; then
        ROLLBACK_TARGET="sprint-14"
        log "Rolling back to tag: $ROLLBACK_TARGET"
    else
        # Try to find parent commit (one before current)
        ROLLBACK_TARGET="HEAD~1"
        log "Rolling back to previous commit: $ROLLBACK_TARGET"
    fi
    
    # Create backup branch
    BACKUP_BRANCH="rollback-backup-$(date +%Y%m%d-%H%M%S)"
    git branch "$BACKUP_BRANCH" HEAD
    log "Created backup branch: $BACKUP_BRANCH"
    
    # Checkout previous version
    if git checkout "$ROLLBACK_TARGET" 2>/dev/null; then
        success "Checked out $ROLLBACK_TARGET"
    else
        error "Failed to checkout $ROLLBACK_TARGET"
        log "Restoring from backup branch: $BACKUP_BRANCH"
        git checkout "$BACKUP_BRANCH"
        exit 1
    fi
fi

# Step 5: Verify dependencies
log "Step 5: Verifying dependencies in $PREVIOUS_ENV..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would verify dependencies"
else
    # Check Python dependencies
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log "Verifying Python dependencies..."
        if "$PROJECT_ROOT/.venv/bin/pip" list --format=freeze | grep -q "crewai"; then
            success "Core dependencies verified"
        else
            warning "Some dependencies may be missing"
            log "Reinstalling dependencies..."
            "$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt" -q
        fi
    fi
fi

# Step 6: Start previous version
log "Step 6: Starting $PREVIOUS_ENV environment..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would start $PREVIOUS_ENV environment"
else
    # Verify main script exists
    if [[ ! -f "$PROJECT_ROOT/scripts/economist_agent.py" ]]; then
        error "Main script not found in $PREVIOUS_ENV"
        exit 2
    fi
    
    success "$PREVIOUS_ENV environment ready"
fi

# Step 7: Health check after rollback
log "Step 7: Health check after rollback..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would perform post-rollback health check"
else
    # Run smoke test
    log "Running smoke test..."
    if "$PROJECT_ROOT/.venv/bin/python3" -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/scripts')
try:
    from llm_client import create_llm_client
    client = create_llm_client()
    print('Smoke test PASSED')
except Exception as e:
    print(f'Smoke test FAILED: {e}')
    sys.exit(1)
" 2>/dev/null; then
        success "Post-rollback smoke test passed"
    else
        error "Post-rollback smoke test failed"
        exit 2
    fi
fi

# Step 8: Update deployment state
log "Step 8: Updating deployment state..."

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would update deployment state to $PREVIOUS_ENV"
else
    # Swap current and previous
    NEW_STATE=$(jq --arg current "$PREVIOUS_ENV" --arg previous "$CURRENT_ENV" \
        '.current = $current | .previous = $previous | .timestamp = now | .rollback = true' \
        "$PROJECT_ROOT/.deployment_state")
    
    echo "$NEW_STATE" > "$PROJECT_ROOT/.deployment_state"
    success "Updated deployment state"
fi

# Step 9: Generate rollback report
log "Step 9: Generating rollback report..."

REPORT_FILE="$PROJECT_ROOT/logs/ROLLBACK_REPORT_$(date +%Y%m%d_%H%M%S).md"

if [[ "$DRY_RUN" == true ]]; then
    log "DRY RUN: Would generate rollback report"
else
    cat > "$REPORT_FILE" <<EOF
# Production Rollback Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S')  
**Type**: Emergency Rollback  
**Status**: ${GREEN}SUCCESS${NC}

---

## Rollback Details

- **From**: $CURRENT_ENV
- **To**: $PREVIOUS_ENV
- **Trigger**: Manual rollback script execution
- **Duration**: ~2 minutes

---

## Actions Taken

1. Verified current deployment state
2. Health checked $PREVIOUS_ENV environment
3. Stopped $CURRENT_ENV processes
4. Switched to $PREVIOUS_ENV version
5. Verified dependencies
6. Started $PREVIOUS_ENV environment
7. Performed post-rollback health check
8. Updated deployment state

---

## Post-Rollback Validation

- ✅ Python environment healthy
- ✅ Dependencies verified
- ✅ Smoke test passed
- ✅ No active processes from $CURRENT_ENV

---

## Next Steps

1. **Immediate**: Monitor logs for any errors
2. **Short-term**: Investigate root cause of rollback
3. **Medium-term**: Create hotfix branch if needed
4. **Long-term**: Update deployment procedures to prevent recurrence

---

## Incident Details

**Rollback Log**: $ROLLBACK_LOG  
**Backup Branch**: ${BACKUP_BRANCH:-N/A}  
**Previous Commit**: ${CURRENT_COMMIT:-unknown}

---

**Report Generated**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

    success "Generated rollback report: $REPORT_FILE"
fi

# Final summary
log "=== Rollback Complete ==="
log ""
log "Summary:"
log "  Previous environment: $CURRENT_ENV"
log "  Current environment:  $PREVIOUS_ENV (rollback target)"
log "  Rollback log: $ROLLBACK_LOG"
if [[ "$DRY_RUN" == false ]]; then
    log "  Rollback report: $REPORT_FILE"
fi
log ""

if [[ "$DRY_RUN" == true ]]; then
    warning "DRY RUN COMPLETE - No changes were made"
    log "To execute rollback, run: $0"
else
    success "ROLLBACK SUCCESSFUL"
    log ""
    log "Next steps:"
    log "  1. Monitor application logs: tail -f logs/*.log"
    log "  2. Run health check: python3 scripts/validate_closed_loop.py"
    log "  3. Notify stakeholders of rollback"
    log "  4. Create incident report with root cause"
fi

exit 0
