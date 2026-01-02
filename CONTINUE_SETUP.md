# Continue.dev Setup - Personal OpenAI API Key

**Date**: 2026-01-01  
**Status**: ✅ ACTIVE

## Configuration Summary

### ✅ What's Enabled
- **Continue.dev Chat**: GPT-4o (default), o1 (reasoning), o1-mini (balanced)
- **Tab Autocomplete**: GPT-4o via Continue.dev
- **Codebase Indexing**: Enabled with embeddings
- **GitHub Copilot Inline**: DISABLED (Chat disabled, suggestions disabled)

### 💰 Cost Structure
- **Continue.dev**: Your personal OpenAI API key ($0.005/1K tokens for GPT-4o)
- **GitHub Copilot**: NOT USED (conserving corporate quota)

## Files Created

1. **`~/.continue/config.json`** - User-level configuration (all projects)
2. **`.vscode/settings.json`** - Workspace settings (Copilot disabled)

## How to Use

### Open Continue.dev Chat
- **Keybinding**: `Cmd+L` (macOS) or `Ctrl+L` (Windows/Linux)
- **Sidebar**: Click Continue icon in VS Code sidebar

### Switch Models
In Continue chat:
```
/model
```
Then select:
- `GPT-4o (Default)` - Fast, daily use
- `o1 (Complex Reasoning)` - Hard problems, debugging
- `o1-mini (Balanced)` - Mid-range tasks

### Use Codebase Context
In Continue chat:
```
@codebase What is the Sprint 9 goal?
```

The `@codebase` context provider searches your entire workspace.

### Inline Autocomplete
Just start typing - suggestions appear automatically from GPT-4o.

## Test Commands

### 1. Verify API Key
```bash
echo $OPENAI_API_KEY | cut -c1-10
```
Should show: `sk-proj--Q`

### 2. Test Continue Chat
Open Continue (`Cmd+L`) and paste:
```
What model are you? Please identify yourself and confirm you're using OpenAI's API.

@codebase What are the Sprint 9 Stories and their point values?
```

Expected response:
- Model identifies as GPT-4o or o1
- Confirms OpenAI API (not Copilot)
- Successfully retrieves Sprint 9 data from docs/SPRINT_9_BACKLOG.md

### 3. Test Tab Autocomplete
Open any Python file and type:
```python
def calculate_quality_score():
    """Calculate project quality
```

Autocomplete should suggest the rest of the docstring and function body.

## Troubleshooting

### "API key not found"
```bash
# Check if key is set
echo $OPENAI_API_KEY

# If not, source your .env
source .env
echo $OPENAI_API_KEY
```

### "Model not available"
Check your OpenAI account has API access:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[].id' | grep gpt-4o
```

### "Copilot still active"
1. Open VS Code Command Palette (`Cmd+Shift+P`)
2. Search: "GitHub Copilot: Disable"
3. Reload window (`Cmd+Shift+P` → "Developer: Reload Window")

### "Continue not indexing codebase"
The first indexing takes ~1-2 minutes. Check progress:
1. Open Continue sidebar
2. Bottom status bar shows "Indexing..." progress
3. Wait for completion before using `@codebase`

## Keybindings

| Action | macOS | Windows/Linux |
|--------|-------|---------------|
| Open Continue Chat | `Cmd+L` | `Ctrl+L` |
| Accept Inline Suggestion | `Tab` | `Tab` |
| Reject Suggestion | `Esc` | `Esc` |
| Toggle Continue Sidebar | `Cmd+Shift+L` | `Ctrl+Shift+L` |

## Cost Tracking

Monitor your OpenAI usage:
https://platform.openai.com/usage

**Typical costs** (GPT-4o):
- Chat message (1K tokens): $0.005
- Inline autocomplete (100 tokens): $0.0005
- Codebase embedding (one-time): ~$0.10 per project

**Budget recommendation**: $20/month covers ~4M tokens of GPT-4o

## Switching Back to Copilot

If you need to switch back:

1. **Enable Copilot Chat**:
   Edit `.vscode/settings.json`:
   ```json
   "github.copilot.enable": {
       "*": true
   }
   ```

2. **Disable Continue**:
   ```json
   "continue.enableTabAutocomplete": false
   ```

3. **Reload VS Code**:
   `Cmd+Shift+P` → "Developer: Reload Window"

## References

- Continue.dev Docs: https://continue.dev/docs
- OpenAI API Pricing: https://openai.com/api/pricing/
- VS Code Settings: https://code.visualstudio.com/docs/getstarted/settings

---

**Last Updated**: 2026-01-01  
**Next Review**: When OpenAI releases GPT-5 or pricing changes
