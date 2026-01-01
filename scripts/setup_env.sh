#!/bin/bash
# Secure API Key Setup Script

set -e

echo "🔒 Secure API Key Setup"
echo "======================="
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
fi

# Copy template
cp .env.example .env
echo "✅ Created .env file from template"

# Secure permissions (Unix only)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    chmod 600 .env
    echo "✅ Set secure permissions (600) on .env"
fi

echo ""
echo "📝 Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Add your OpenAI API key"
echo "3. Test it: python3 scripts/llm_client.py"
echo ""
echo "Security reminders:"
echo "- .env is in .gitignore (won't be committed)"
echo "- Keep your API keys secret"
echo "- Never share .env files"
echo "- Use separate keys for dev/prod"
echo ""
echo "To get your OpenAI key:"
echo "https://platform.openai.com/api-keys"
