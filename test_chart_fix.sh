#!/bin/bash
# Quick test of chart embedding fix

cd /Users/ouray.viney/code/economist-agents

echo "Testing Writer Agent with chart embedding..."
echo "Topic: Self-Healing Tests: Myth vs Reality"
echo ""

export TOPIC="Self-Healing Tests: Myth vs Reality"
export TALKING_POINTS="vendor promises, maintenance reduction, limitations"

# Run the economist agent
.venv/bin/python scripts/economist_agent.py

# Check the latest article
LATEST_ARTICLE=$(ls -t output/2026-01-01-*.md 2>/dev/null | head -1)

if [ -f "$LATEST_ARTICLE" ]; then
    echo ""
    echo "==========================================="
    echo "VERIFICATION:"
    echo "==========================================="
    echo "Latest article: $LATEST_ARTICLE"
    echo ""

    if grep -q 'assets/charts' "$LATEST_ARTICLE"; then
        echo "✅ SUCCESS: Chart reference found in article!"
        echo ""
        grep -A 2 -B 2 'assets/charts' "$LATEST_ARTICLE"
    else
        echo "❌ FAILURE: No chart reference found!"
        echo ""
        echo "Checking if chart was generated..."
        LATEST_CHART=$(ls -t output/charts/*.png 2>/dev/null | head -1)
        if [ -f "$LATEST_CHART" ]; then
            echo "Chart exists: $LATEST_CHART"
            echo "BUT article doesn't reference it!"
        else
            echo "No chart was generated."
        fi
    fi
else
    echo "❌ No article was generated!"
fi
