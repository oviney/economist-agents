#!/bin/bash
#
# Git Hooks Installer
# Installs custom git hooks for quality enforcement
#
# Usage:
#   ./scripts/install-hooks.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "📦 Installing git hooks..."
echo ""

# ============================================================================
# Copy hooks to .git/hooks/
# ============================================================================

# Pre-commit hook
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    echo "✓ pre-commit hook already installed"
else
    echo "⚠  pre-commit hook not found in .git/hooks/"
    echo "  Expected location: $HOOKS_DIR/pre-commit"
    exit 1
fi

# Commit-msg hook
if [ -f "$HOOKS_DIR/commit-msg" ]; then
    echo "✓ commit-msg hook already installed"
else
    echo "⚠  commit-msg hook not found in .git/hooks/"
    echo "  Expected location: $HOOKS_DIR/commit-msg"
    exit 1
fi

# Make executable
chmod +x "$HOOKS_DIR/pre-commit" 2>/dev/null || true
chmod +x "$HOOKS_DIR/commit-msg" 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Git hooks installed successfully"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installed hooks:"
echo "  • pre-commit:  Quality checks before commit"
echo "  • commit-msg:  GitHub close syntax validation"
echo ""
echo "To test:"
echo "  git commit -m 'test message'"
echo ""
