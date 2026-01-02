#!/bin/bash
# Complete setup script for economist-agents

set -e

echo "🚀 Economist-Agents Development Setup"
echo "======================================"

# Check Python version
echo "→ Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "❌ Python 3.11+ required. Found: Python $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "⚠️  No virtual environment detected!"
    echo ""
    echo "Please create and activate a virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  ./scripts/setup.sh"
    echo ""
    exit 1
fi

# Install dependencies
echo "→ Installing dependencies..."
python3 -m pip install -r requirements.txt -q
python3 -m pip install -r requirements-dev.txt -q

# Setup pre-commit hooks
echo "→ Setting up pre-commit hooks..."
pre-commit install --install-hooks
pre-commit install --hook-type pre-push

# Create necessary directories
echo "→ Creating output directories..."
mkdir -p output/charts output/governance tests/outputs

# Setup .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "→ Creating .env from template..."
        cp .env.example .env
        echo "⚠️  Edit .env with your API keys before running agents"
    else
        echo "⚠️  No .env.example found. Create .env manually with your API keys"
    fi
fi

# Run initial quality checks
echo "→ Running initial quality checks..."
if make quality; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your API keys"
    echo "2. Run: make test"
    echo "3. Start developing!"
    echo ""
    echo "Custom Copilot Agents available:"
    echo "  @quality-enforcer - Enforce Python standards"
    echo "  @test-writer - Write comprehensive tests"
    echo "  @refactor-specialist - Refactor to quality standards"
else
    echo ""
    echo "⚠️  Initial quality checks failed"
    echo "Some files may need refactoring to meet standards"
    echo "Use: @refactor-specialist to fix violations"
fi
