#!/bin/bash
# Security Verification Test Suite
# Tests all security features are working correctly

set -e  # Exit on error

echo "🔒 Security Verification Test Suite"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# Test 1: .env.example exists
echo "Test 1: Template file exists"
if [ -f ".env.example" ]; then
    pass ".env.example found"
else
    fail ".env.example missing"
fi

# Test 2: .env.example has no real keys
echo "Test 2: Template has placeholders"
if grep -q "your-.*-key-here" .env.example; then
    pass "Template uses placeholders"
else
    fail "Template may contain real keys!"
fi

# Test 3: .gitignore protects .env
echo "Test 3: Git protection active"
if grep -q "^\.env$" .gitignore; then
    pass ".env in .gitignore"
else
    fail ".env not protected by .gitignore"
fi

# Test 4: .env is not tracked by git
echo "Test 4: .env not in git"
if git ls-files --error-unmatch .env 2>/dev/null; then
    fail ".env is tracked by git! Run: git rm --cached .env"
else
    pass ".env not tracked by git"
fi

# Test 5: Check for accidental key commits
echo "Test 5: No keys in git history"
if git log --all --source --full-history -- . | grep -i "sk-ant-\|sk-proj-" | grep -v "sk-...\|placeholder\|your-"; then
    warn "Possible API key found in git history!"
    echo "  Run: git log --all -S 'sk-' to investigate"
else
    pass "No obvious keys in git history"
fi

# Test 6: .env has correct permissions (if it exists)
echo "Test 6: File permissions"
if [ -f ".env" ]; then
    perms=$(stat -f "%OLp" .env 2>/dev/null || stat -c "%a" .env 2>/dev/null)
    if [ "$perms" = "600" ]; then
        pass ".env has 600 permissions"
    else
        warn ".env has $perms permissions (should be 600)"
        echo "  Run: chmod 600 .env"
    fi
else
    warn ".env doesn't exist yet (run ./scripts/setup_env.sh)"
fi

# Test 7: Secure scripts exist
echo "Test 7: Security scripts present"
scripts=("scripts/secure_env.py" "scripts/setup_env.sh" "scripts/test_setup.py")
for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        pass "$script exists"
    else
        fail "$script missing"
    fi
done

# Test 8: Documentation exists
echo "Test 8: Security documentation"
docs=(".github/API_KEY_SECURITY.md" ".github/SECURITY_IMPLEMENTATION.md" ".github/SECURITY_QUICKSTART.md")
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        pass "$doc exists"
    else
        fail "$doc missing"
    fi
done

# Test 9: Dependencies installed
echo "Test 9: Python dependencies"
if python3 -c "import dotenv" 2>/dev/null; then
    pass "python-dotenv installed"
else
    warn "python-dotenv not installed (run: pip install python-dotenv)"
fi

# Test 10: LLM client has auto-loading
echo "Test 10: Auto-loading enabled"
if grep -q "load_dotenv" scripts/llm_client.py; then
    pass "LLM client auto-loads .env"
else
    fail "LLM client missing auto-load"
fi

# Summary
echo ""
echo "===================================="
echo "🎉 Security Verification Complete"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Add your API key: ./scripts/setup_env.sh"
echo "2. Test setup: python3 scripts/test_setup.py"
echo "3. Generate article: python3 scripts/economist_agent.py"
echo ""
