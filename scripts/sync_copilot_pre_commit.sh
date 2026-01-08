#!/bin/bash
# Copilot Context Sync Automation
# Add this to .git/hooks/pre-commit for automatic syncing

set -e

echo "🔄 Syncing Copilot context with learned patterns..."

# Run the sync script
python3 scripts/sync_copilot_context.py

# Check if copilot-instructions.md was modified
if git diff --name-only | grep -q ".github/copilot-instructions.md"; then
    echo "✅ Copilot instructions updated with latest patterns"
    
    # Auto-stage the updated file
    git add .github/copilot-instructions.md
    
    echo "📝 Changes staged for commit"
else
    echo "ℹ️  No changes to Copilot instructions (patterns already current)"
fi

exit 0
