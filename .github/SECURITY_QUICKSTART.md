# Security Quick Start

**TLDR**: Use `.env` files for API keys. Never commit them.

## 30-Second Setup

```bash
# 1. Run secure setup
./scripts/setup_env.sh

# 2. Edit .env file (add your real API key)
nano .env

# 3. Test it works
python3 scripts/test_setup.py

# 4. Start using
python3 scripts/economist_agent.py
```

**Done!** Your API keys are now secure.

---

## What Just Happened?

✅ Created `.env` file with your API key  
✅ Set 600 permissions (only you can read it)  
✅ Added to `.gitignore` (won't be committed)  
✅ Auto-loaded by all scripts  

---

## Example `.env` File

```bash
# For OpenAI (recommended)
OPENAI_API_KEY=sk-proj-abc123xyz...
OPENAI_MODEL=gpt-4o

# For Anthropic (alternative)
#ANTHROPIC_API_KEY=sk-ant-abc123xyz...
#ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Optional
OUTPUT_DIR=output
```

---

## Commands You'll Use

### Setup
```bash
./scripts/setup_env.sh          # One-time setup
python3 scripts/test_setup.py   # Verify it works
```

### Check Security
```bash
git status                      # .env should NOT appear
ls -la .env                     # Should show -rw------- (600)
```

### If Key Compromised
```bash
# 1. Revoke on provider dashboard IMMEDIATELY
# 2. Generate new key
# 3. Update .env with new key
nano .env
# 4. Test
python3 scripts/test_setup.py
```

---

## Get Your API Key

**OpenAI** (recommended):  
https://platform.openai.com/api-keys

**Anthropic**:  
https://console.anthropic.com/settings/keys

---

## Safety Checklist

Before committing code:
- [ ] `.env` exists locally
- [ ] `.env` not in `git status`
- [ ] No API keys in source files
- [ ] File permissions are 600

---

## Full Documentation

- **Complete Security Guide**: [API_KEY_SECURITY.md](API_KEY_SECURITY.md)
- **Implementation Details**: [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md)
- **Main README**: [../README.md](../README.md)

---

## Common Issues

**"No API keys found"**
```bash
# Did you edit .env?
nano .env

# Did you run setup?
./scripts/setup_env.sh
```

**"Permission denied"**
```bash
chmod 600 .env
```

**"API key invalid"**
```bash
# Check format:
# OpenAI: sk-proj-... or sk-...
# Anthropic: sk-ant-...

# Get new key from provider dashboard
```

---

**Need help?** See [API_KEY_SECURITY.md](API_KEY_SECURITY.md) for complete troubleshooting guide.
