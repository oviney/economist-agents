#!/bin/bash
# Pre-Work Sprint Checklist
# Run this before starting ANY implementation work

set -e

echo "🔍 Sprint Discipline Pre-Work Checklist"
echo "========================================"
echo ""

# Get work description from user
if [ -z "$1" ]; then
    echo "Usage: ./scripts/pre_work_check.sh \"Work description\""
    echo ""
    echo "Example:"
    echo "  ./scripts/pre_work_check.sh \"Implement metrics tracking\""
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

echo ""
echo "🎯 Quick Reminder:"
echo "   - Update SPRINT.md checkboxes as you go"
echo "   - Reference story number in commits: 'Story 1: ...'  "
echo "   - Run tests before committing"
echo "   - Update sprint status when done"
echo ""
echo "✅ You're clear to start! Happy coding! 🚀"
echo ""
