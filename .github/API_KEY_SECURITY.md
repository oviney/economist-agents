# API Key Security Guide

This project handles API keys securely. Follow these guidelines to protect your credentials.

## 🔒 Security Best Practices

### 1. Use .env Files (Recommended)

**Setup**:
```bash
# One-time setup
./scripts/setup_env.sh

# Edit with your real keys
nano .env
```

**Benefits**:
- ✅ Keys stored in one secure file
- ✅ Automatic .gitignore protection
- ✅ 600 permissions (user-only access)
- ✅ Easy to rotate keys
- ✅ Works across all scripts

### 2. Environment Variables (Alternative)

**Temporary (session only)**:
```bash
export OPENAI_API_KEY='sk-...'
python3 -c "from src.economist_agents.flow import EconomistContentFlow; EconomistContentFlow().kickoff()"
```

**Permanent (add to ~/.zshrc or ~/.bashrc)**:
```bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

## 🚫 What NOT To Do

❌ **Never commit API keys to git**
```bash
# BAD - Don't do this
git commit -m "added my key sk-abc123..."
```

❌ **Never hardcode keys in source files**
```python
# BAD - Don't do this
api_key = "sk-abc123..."  # NEVER!
```

❌ **Never share .env files**
```bash
# BAD - Don't do this
slack send .env @team
```

❌ **Never use production keys in development**
- Use separate keys for dev/staging/prod
- Rotate keys if accidentally exposed

## ✅ Secure Workflows

### Development
```bash
# 1. Create .env file
./scripts/setup_env.sh

# 2. Add your dev API key
nano .env

# 3. Test it
python3 scripts/llm_client.py

# 4. Verify .env is ignored
git status  # Should NOT show .env
```

### Production (CI/CD)

**GitHub Actions**:
```yaml
# .github/workflows/generate.yml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Store keys in: Settings → Secrets and variables → Actions

**Docker**:
```bash
# Don't bake keys into image
docker run -e OPENAI_API_KEY="$OPENAI_API_KEY" economist-agents
```

**AWS/Cloud**:
```bash
# Use secrets manager
aws secretsmanager get-secret-value --secret-id openai-key
```

## 🔍 Key Validation

The project automatically validates keys:

```python
# OpenAI keys must start with 'sk-'
✅ sk-proj-abc123...
❌ abc123  # Invalid format

# Anthropic keys must start with 'sk-ant-'
✅ sk-ant-abc123...
❌ ant-abc123  # Invalid format
```

## 🔄 Key Rotation

**If a key is compromised**:

1. **Revoke immediately** on provider dashboard
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/settings/keys

2. **Generate new key**

3. **Update .env file**:
```bash
nano .env  # Replace old key with new key
```

4. **Test new key**:
```bash
python3 scripts/llm_client.py
```

5. **Update production secrets** (GitHub Actions, AWS, etc.)

## 🔐 File Permissions

**Unix/Linux/macOS**:
```bash
# .env should be user-read-only
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (600)
```

**Windows**:
- Right-click .env → Properties → Security
- Remove all users except yourself

## 🎯 Security Checklist

Before committing code:
- [ ] .env file exists locally
- [ ] .env is in .gitignore
- [ ] No API keys in source files
- [ ] No API keys in commit messages
- [ ] .env has 600 permissions (Unix)
- [ ] Tested with keys in .env only

## 🚨 What If I Accidentally Commit a Key?

**Immediate steps**:

1. **Revoke the key** on provider dashboard (NOW!)

2. **Remove from git history**:
```bash
# Remove file from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all
```

3. **Generate new key** and update .env

4. **Consider repo as compromised** - keys in git history are public forever

## 📚 Additional Resources

- [OpenAI API Key Best Practices](https://platform.openai.com/docs/api-reference/authentication)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## 🤝 Contributing

When contributing:
- Never include your .env file in PRs
- Use .env.example as template
- Document any new environment variables
- Test with fresh .env file

## ❓ FAQ

**Q: Can I use multiple keys for different environments?**
A: Yes! Use .env.dev, .env.prod and load the right one:
```bash
python3 scripts/llm_client.py --env prod
```

**Q: What if I don't have python-dotenv installed?**
A: Scripts fall back to system environment variables automatically.

**Q: Are keys encrypted in .env?**
A: No, .env files store keys in plain text. Security comes from:
- File permissions (600)
- .gitignore (not committed)
- Access control (who can read the file)

**Q: Should I use a password manager for API keys?**
A: Yes! Store backup copies in 1Password, LastPass, etc.

---

**Remember**: Treat API keys like passwords. Never share them, commit them, or expose them publicly.
