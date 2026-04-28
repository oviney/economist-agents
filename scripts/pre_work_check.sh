#!/bin/bash
# Pre-Work Sprint Checklist
# Run this before starting ANY implementation work

set -e

ISSUE_NUMBER=""
RUNTIME="${AGENT_RUNTIME:-codex}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue)
            ISSUE_NUMBER="$2"
            shift 2
            ;;
        --runtime)
            RUNTIME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./scripts/pre_work_check.sh [--issue N] [--runtime codex|claude|copilot] \"Work description\""
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

echo "🔍 Sprint Discipline Pre-Work Checklist"
echo "========================================"
echo ""

# Get work description from user
if [ -z "$1" ]; then
    echo "Usage: ./scripts/pre_work_check.sh [--issue N] [--runtime codex|claude|copilot] \"Work description\""
    echo ""
    echo "Example:"
    echo "  ./scripts/pre_work_check.sh --issue 123 --runtime codex \"Implement metrics tracking\""
    echo ""
    exit 1
fi

WORK_DESC="$1"

echo "📋 About to work on: $WORK_DESC"
echo ""

# Run sprint validator
python3 scripts/sprint_validator.py --check-before-work "$WORK_DESC"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ BLOCKED: Sprint discipline checks failed"
    echo "   Fix the issues above before starting work."
    echo ""
    exit 1
fi

if [ -n "$ISSUE_NUMBER" ]; then
    echo "🔐 Verifying issue ownership..."
    python3 scripts/github_issue_claim.py check "$ISSUE_NUMBER" --runtime "$RUNTIME"

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ BLOCKED: Issue ownership check failed"
        echo "   Claim the issue before starting work."
        echo ""
        exit 1
    fi

    echo "   ✓ Issue #$ISSUE_NUMBER is reserved for $RUNTIME"
    echo ""
fi

echo ""
echo "🎯 Quick Reminder:"
echo "   - Update SPRINT.md checkboxes as you go"
echo "   - Reference story number in commits: 'Story 1: ...'  "
echo "   - Run tests before committing"
echo "   - Update sprint status when done"
echo ""
echo "✅ You're clear to start! Happy coding! 🚀"
echo ""
