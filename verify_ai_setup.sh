#!/bin/bash
# Verify AI Code Assistance Setup

echo "🔍 Verifying AI Code Assistance Configuration..."
echo ""

# Check 1: OPENAI_API_KEY
echo "✅ Check 1: OPENAI_API_KEY Environment Variable"
if [[ -n "$OPENAI_API_KEY" ]]; then
    KEY_PREFIX="${OPENAI_API_KEY:0:10}"
    echo "   ✓ Set: $KEY_PREFIX..."
    
    # Verify it's not a placeholder
    if [[ "$OPENAI_API_KEY" == *"your-openai-key"* ]]; then
        echo "   ⚠️  WARNING: API key appears to be a placeholder"
        echo "   Update your .env file with real key"
    fi
else
    echo "   ✗ NOT SET"
    echo "   Run: export OPENAI_API_KEY='sk-proj-your-key'"
    echo "   Or add to .env and source it"
fi
echo ""

# Check 2: Continue.dev Extension
echo "✅ Check 2: Continue.dev Extension"
if code --list-extensions | grep -q "continue.continue"; then
    echo "   ✓ Installed"
else
    echo "   ✗ NOT INSTALLED"
    echo "   Run: code --install-extension continue.continue"
fi
echo ""

# Check 3: VS Code Settings
echo "✅ Check 3: VS Code Configuration Files"
if [[ -f ".vscode/settings.json" ]]; then
    echo "   ✓ settings.json exists"
else
    echo "   ✗ settings.json missing"
fi

if [[ -f ".vscode/continue-config.json" ]]; then
    echo "   ✓ continue-config.json exists"
    
    # Verify it references OPENAI_API_KEY
    if grep -q "\${OPENAI_API_KEY}" ".vscode/continue-config.json"; then
        echo "   ✓ Configured to use \$OPENAI_API_KEY"
    else
        echo "   ⚠️  Missing \${OPENAI_API_KEY} reference"
    fi
else
    echo "   ✗ continue-config.json missing"
fi
echo ""

# Check 4: GitHub Copilot Status
echo "✅ Check 4: GitHub Copilot (Should be Disabled)"
if code --list-extensions | grep -q "github.copilot"; then
    echo "   ⚠️  GitHub Copilot installed (will be disabled in workspace)"
    echo "   Workspace settings.json disables it to avoid quota conflicts"
else
    echo "   ✓ GitHub Copilot not installed (good, no conflicts)"
fi
echo ""

# Check 5: API Key Validation (optional OpenAI API call)
echo "✅ Check 5: API Key Validation (Optional)"
if command -v curl &> /dev/null && [[ -n "$OPENAI_API_KEY" ]]; then
    echo "   Testing API key with OpenAI..."
    
    RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openai_test.json \
        https://api.openai.com/v1/models \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        --max-time 5)
    
    if [[ "$RESPONSE" == "200" ]]; then
        echo "   ✓ API key is VALID"
        
        # Show available models
        if command -v jq &> /dev/null; then
            echo "   Available models:"
            jq -r '.data[] | select(.id | contains("gpt-4o") or contains("o1")) | "     - " + .id' /tmp/openai_test.json 2>/dev/null | head -5
        fi
    elif [[ "$RESPONSE" == "401" ]]; then
        echo "   ✗ API key is INVALID (401 Unauthorized)"
    else
        echo "   ⚠️  Could not validate (HTTP $RESPONSE)"
    fi
    
    rm -f /tmp/openai_test.json
else
    echo "   ⊘ Skipped (curl not available or API key not set)"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ALL_GOOD=true

if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "❌ Set OPENAI_API_KEY environment variable"
    ALL_GOOD=false
fi

if ! code --list-extensions | grep -q "continue.continue"; then
    echo "❌ Install Continue.dev extension"
    ALL_GOOD=false
fi

if [[ ! -f ".vscode/continue-config.json" ]]; then
    echo "❌ Create .vscode/continue-config.json"
    ALL_GOOD=false
fi

if $ALL_GOOD; then
    echo "✅ All checks passed! Ready to use Continue.dev with your OpenAI API key"
    echo ""
    echo "Next steps:"
    echo "  1. Restart VS Code: code ."
    echo "  2. Press Cmd+L to open Continue chat"
    echo "  3. Test: 'Which API key prefix are you using?'"
    echo ""
    echo "📖 Full guide: .vscode/AI_SETUP.md"
else
    echo ""
    echo "⚠️  Some checks failed. See .vscode/AI_SETUP.md for setup instructions"
fi
