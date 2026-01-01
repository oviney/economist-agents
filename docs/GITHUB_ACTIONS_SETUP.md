# GitHub Actions Setup Guide

This guide walks you through setting up automated content generation that pushes directly to your blog repository.

## Architecture: Cross-Repository Integration

```
┌─────────────────────────────────────────────────────────────┐
│  economist-agents repo (this repo)                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ GitHub Actions Workflow                             │    │
│  │ 1. Generate article                                 │    │
│  │ 2. Create charts                                    │    │
│  │ 3. Validate quality ────────────────┐              │    │
│  └─────────────────────────────────────│──────────────┘    │
└────────────────────────────────────────│───────────────────┘
                                         │
                                         │ Push via token
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────┐
│  your-blog repo                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Creates Pull Request with:                          │    │
│  │ • _posts/YYYY-MM-DD-article.md                      │    │
│  │ • assets/charts/article.png                         │    │
│  │                                                     │    │
│  │ ➜ You review and merge to publish                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- economist-agents repository (this repo)
- Your blog repository (Jekyll, Hugo, or any static site)
- GitHub account with access to both repos

## Step 1: Create Personal Access Token (PAT)

The workflow needs permission to push to your blog repo.

1. Go to **GitHub.com** → Your profile icon → **Settings**
2. Scroll to **Developer settings** (bottom left)
3. Click **Personal access tokens** → **Tokens (classic)**
4. Click **Generate new token (classic)**
5. Configure:
   - **Note**: `economist-agents-to-blog`
   - **Expiration**: 90 days (recommended)
   - **Scopes**: Check these boxes:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows)
6. Click **Generate token**
7. **COPY THE TOKEN NOW** - you won't see it again!

Example token: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 2: Add Secrets to economist-agents Repo

Go to your **economist-agents** repository on GitHub:

1. **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

Add these secrets:

Add these secrets:

### Required Secrets

**API Keys** (at least one required):

1. **OPENAI_API_KEY** (if using OpenAI)
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key (starts with `sk-proj-...`)

2. **ANTHROPIC_API_KEY** (if using Anthropic Claude)
   - Name: `ANTHROPIC_API_KEY`
   - Value: Your Anthropic API key (starts with `sk-ant-...`)

**Blog Repository Access** (required for cross-repo push):

3. **BLOG_REPO_TOKEN**
   - Name: `BLOG_REPO_TOKEN`
   - Value: The Personal Access Token you created in Step 1
   - This allows the workflow to push to your blog repo

## Step 3: Add Variables to economist-agents Repo

Still in your **economist-agents** repo settings:

1. **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Click **New repository variable**

Add these variables:

### Required Variables

**BLOG_REPO_OWNER**
- Name: `BLOG_REPO_OWNER`
- Value: Your GitHub username or organization
- Example: `oviney`

**BLOG_REPO_NAME**
- Name: `BLOG_REPO_NAME`
- Value: Your blog repository name (not the full URL, just the name)
- Example: `my-blog` or `oviney.github.io`

> **Important**: These must match your blog repo exactly. For repo `github.com/oviney/my-blog`:
> - BLOG_REPO_OWNER = `oviney`
> - BLOG_REPO_NAME = `my-blog`

## Step 4: Verify Blog Repository Structure

Your blog repo should have this structure:

```
your-blog/
├── _posts/              ← Articles go here
│   └── YYYY-MM-DD-article.md
├── assets/
│   └── charts/          ← Charts go here
│       └── article.png
├── _config.yml
└── ...
```

If your blog uses different paths, you'll need to adjust the workflow (see Advanced Configuration).

## Step 5: Test the Integration

## Step 5: Test the Integration

1. Go to **economist-agents** repo → **Actions** tab
2. Click **Content Generation Pipeline** in the left sidebar
3. Click **Run workflow** dropdown (top right)
4. Leave all options at defaults and click **Run workflow**

### What Happens:

1. ✅ Workflow generates article and chart
2. ✅ Clones your blog repo using BLOG_REPO_TOKEN
3. ✅ Copies files to `_posts/` and `assets/charts/`
4. ✅ Creates a branch like `content/article-20260101-123456`
5. ✅ Pushes to your blog repo
6. ✅ Opens a Pull Request in your **blog repo**

### Expected Results:

Check your **blog repository**:
- **Pull Requests** tab: New PR with article
- PR contains: Article markdown + chart image
- Branch: `content/article-YYYYMMDD-HHMMSS`

## Step 6: Review and Merge

In your **blog repo** PR:

1. ✅ Review article content
2. ✅ Check chart rendering
3. ✅ Verify YAML front matter
4. ✅ Check for British spelling
5. ✅ Approve and merge to `main`
6. 🎉 Jekyll builds and publishes your new post!

## Troubleshooting

### "Push to Blog Repository: skipped"

**Problem**: Workflow doesn't push to blog repo

**Causes & Solutions**:
1. **Missing variables**: Verify `BLOG_REPO_OWNER` and `BLOG_REPO_NAME` are set in Variables (not Secrets)
2. **Wrong variable names**: Must be exactly `BLOG_REPO_OWNER` and `BLOG_REPO_NAME`
3. **Case sensitivity**: Variable values are case-sensitive (`Oviney` ≠ `oviney`)

Check:
```bash
# In workflow logs, look for:
BLOG_OWNER: your-username
BLOG_REPO: your-blog-name
```

### "Authentication failed"

**Problem**: Can't push to blog repo

**Solutions**:
1. **Token expired**: Regenerate PAT (Step 1) and update `BLOG_REPO_TOKEN` secret
2. **Insufficient permissions**: Token needs `repo` and `workflow` scopes
3. **Wrong token**: Verify you copied the entire token (starts with `ghp_`)

### "Remote rejected: permission denied"

**Problem**: Token doesn't have write access

**Solutions**:
1. Verify you have admin/write access to blog repo
2. If blog repo is in an organization, enable SSO for the token
3. Check token hasn't been revoked

### "Could not create pull request"

**Problem**: PR creation fails in blog repo

**Solutions**:
1. Ensure blog repo allows PR creation (not archived/locked)
2. Check if branch already exists with same name
3. Verify token has `workflow` scope (needed for PRs)

### Files go to wrong location

**Problem**: Files copied to wrong directories in blog repo

**Solution**: Your blog structure differs from Jekyll defaults. See Advanced Configuration below.

## Advanced Configuration

### Custom Blog Directory Structure

If your blog uses different paths, edit the workflow:

```yaml
# In .github/workflows/content-pipeline.yml, modify:

# Copy generated files
mkdir -p content/posts public/images  # Your custom paths
cp ../output/*.md content/posts/       # Change to your posts dir
cp ../output/charts/*.png public/images/  # Change to your images dir

# Commit
git add content/posts/*.md public/images/*.png
```

### Hugo, Gatsby, or Other Static Site Generators

**Hugo**:
```yaml
mkdir -p content/posts static/images
cp ../output/*.md content/posts/
cp ../output/charts/*.png static/images/
```

**Gatsby**:
```yaml
mkdir -p content/blog static/charts
cp ../output/*.md content/blog/
cp ../output/charts/*.png static/charts/
```

### Direct Push Instead of PR

To skip PR and push directly to main:

```yaml
# Replace the PR creation section with:
- name: Push directly to main
  run: |
    cd blog-repo
    git checkout main
    # ... copy files ...
    git commit -m "content: Add article"
    git push origin main
```

⚠️ **Warning**: Direct push bypasses review. Only use if you trust the validation completely.

### Multiple Blog Repositories

Create separate workflows for each blog:

```yaml
# .github/workflows/blog1-pipeline.yml
env:
  BLOG_OWNER: ${{ vars.BLOG1_OWNER }}
  BLOG_REPO: ${{ vars.BLOG1_REPO }}

# .github/workflows/blog2-pipeline.yml  
env:
  BLOG_OWNER: ${{ vars.BLOG2_OWNER }}
  BLOG_REPO: ${{ vars.BLOG2_REPO }}
```

### Change PR Title/Body

Customize in workflow:

```yaml
gh pr create \
  --title "📝 [Economics] New Analysis: $(date +%Y-%m-%d)" \
  --body "$(cat ../output/*.md | head -20)..."  # First 20 lines as preview
```

## Workflow Options (Manual Trigger)

The workflow is configured to run automatically:
- **Every Monday at 9am UTC** - Topic scout discovers new topics
- You can modify the schedule in `.github/workflows/content-pipeline.yml`

```yaml
schedule:
  - cron: '0 9 * * 1'  # Change as needed
```

Cron format: `minute hour day-of-month month day-of-week`

Examples:
- `0 9 * * 1`: Monday 9am UTC
- `0 14 * * 3`: Wednesday 2pm UTC
- `0 0 * * *`: Daily at midnight UTC

## Workflow Options

## Workflow Options (Manual Trigger)

When you click **Run workflow**, you can customize:

| Input | Description | Default |
|-------|-------------|---------|
| topic | Custom article topic | (uses content queue) |
| run_scout | Discover new topics first | false |
| run_board | Run editorial voting | false |
| interactive | Enable approval gates | false |

**Recommended first test**: Leave all defaults, just click "Run workflow"

## Scheduled Runs

## Security Best Practices

✅ **DO**:
- Use GitHub Secrets for API keys
- Rotate keys every 90 days
- Monitor API usage in provider dashboards
- Review generated content in PRs before merging

❌ **DON'T**:
- Hardcode API keys in workflow files
- Share secrets across multiple repos
- Auto-merge generated content PRs
- Skip article review process

## Cost Management

Each workflow run costs:
- **OpenAI gpt-4o**: ~$0.10-0.30 per article
- **Anthropic Claude**: ~$0.05-0.20 per article

Tips to reduce costs:
1. Disable scheduled runs if not needed
2. Use interactive mode only for important articles
3. Set usage limits in provider dashboards
4. Use cheaper models for testing: `gpt-4o-mini`

## Next Steps

Once GitHub Actions is working:

1. **Review Quality**: Check first 5 generated articles
2. **Adjust Schedule**: Set optimal frequency for your needs
3. **Integrate Blog**: Configure `OUTPUT_DIR` to point to blog repo
4. **Monitor Usage**: Track API costs and adjust accordingly

## Support

Issues with the workflow?

1. Check workflow run logs in Actions tab
2. Review this project's documentation
3. Open an issue on GitHub with logs

