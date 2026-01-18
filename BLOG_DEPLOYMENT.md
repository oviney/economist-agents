# 📝 Blog Deployment Guide

Complete setup guide for automatically deploying generated articles to your blog repository via GitHub Actions.

## 🏗️ Architecture

```
Local Development      GitHub Actions         Blog Repository
     ↓                      ↓                       ↓
Generate Article  →  Auto-trigger Pipeline  →  Create PR to Blog
     ↓                      ↓                       ↓
Manual Deploy    →  Schedule (Weekly Mon)   →  Review & Merge
```

## 🔧 Setup Instructions

### Step 1: Configure Repository Variables

Go to your **economist-agents** repository settings:
```
https://github.com/oviney/economist-agents/settings/variables/actions
```

Add these **Repository Variables**:

| Variable Name | Example Value | Description |
|---------------|---------------|-------------|
| `BLOG_REPO_OWNER` | `yourusername` | Your GitHub username |
| `BLOG_REPO_NAME` | `yourusername.github.io` | Your blog repository name |

### Step 2: Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → **Personal access tokens** → **Fine-grained tokens**
2. Click **"Generate new token"**
3. **Repository access:** Select your blog repository
4. **Permissions:** Grant these permissions:
   - **Contents**: Read and Write
   - **Pull requests**: Write
   - **Metadata**: Read
5. Click **"Generate token"** and copy the token

### Step 3: Add Repository Secret

Go to your **economist-agents** repository secrets:
```
https://github.com/oviney/economist-agents/settings/secrets/actions
```

Add this **Repository Secret**:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `BLOG_REPO_TOKEN` | `github_pat_11ABC...` | Your personal access token |

### Step 4: Verify API Keys

Ensure this secret exists in your repository:

| Secret Name | Required For | Get From |
|-------------|--------------|----------|
| `OPENAI_API_KEY` | Article generation | [OpenAI API Keys](https://platform.openai.com/api-keys) |

## 🚀 Usage Options

### Option 1: GitHub Actions (Automatic)

**Scheduled Weekly Generation:**
- Runs every **Monday at 9am UTC**
- Automatically: Scout topics → Editorial board voting → Generate article → Create PR

**Manual Trigger:**
1. Go to repository → **Actions** tab
2. Select **"Content Generation Pipeline"**
3. Click **"Run workflow"**
4. Choose options:
   - Custom topic (optional)
   - Run topic scout (optional)
   - Interactive mode (optional)
5. Click **"Run workflow"**

**Result:** PR automatically created in your blog repository within ~5-10 minutes.

### Option 2: Local + Automated Deploy

**Generate locally, deploy automatically:**

```bash
# 1. Generate article locally
source .venv/bin/activate
PYTHONPATH=/Users/yourusername/code/economist-agents python3 scripts/economist_agent.py

# 2. Deploy to blog (requires GITHUB_TOKEN and BLOG_REPO env vars)
export GITHUB_TOKEN="your_token_here"
export BLOG_REPO="username/blog-repo"
python3 scripts/deploy_to_blog.py
```

**Result:** Creates PR in your blog repository with the locally generated article.

### Option 3: Local Development Only

**Generate and manually copy:**

```bash
# Generate article
source .venv/bin/activate
PYTHONPATH=/Users/yourusername/code/economist-agents python3 scripts/economist_agent.py

# Files created in:
# - output/2026-01-18-article-title.md
# - output/charts/article-title.png
# - output/images/article-title.png

# Manually copy to your blog repository
```

## 📁 Blog Repository Structure

The deployment assumes this Jekyll structure:

```
your-blog-repo/
├── _posts/
│   └── 2026-01-18-article-title.md     # ← Article placed here
├── assets/
│   └── charts/
│       └── article-title.png           # ← Chart placed here
└── (other Jekyll files)
```

If your blog uses a different structure, modify the paths in:
- `.github/workflows/content-pipeline.yml` (lines 163-165)
- `scripts/deploy_to_blog.py` (lines 73-76)

## 🔍 Troubleshooting

### GitHub Actions Failing

**Check logs:** Go to repository → Actions → Content Generation Pipeline → View logs

**Common issues:**
- Missing OpenAI API key
- Wrong repository variables (BLOG_REPO_OWNER/NAME)
- Insufficient token permissions
- Blog repository doesn't exist

### Local Deploy Script Issues

```bash
# Install GitHub CLI if missing
brew install gh  # macOS
# or follow: https://cli.github.com/manual/installation

# Test GitHub authentication
gh auth status

# Test repository access
gh repo view username/blog-repo
```

### Article Quality Issues

Articles may be **quarantined** instead of published if they fail validation:

**Check quarantine:**
```bash
ls output/quarantine/
cat output/quarantine/*-VALIDATION-FAILED.txt
```

**Common validation failures:**
- Missing References section
- Article too short (<800 words)
- Missing YAML frontmatter
- Forbidden phrases ("in conclusion")

## 📊 Monitoring & Analytics

**View deployment history:**
- Repository → Actions → Content Generation Pipeline
- Blog repository → Pull Requests (economist-agent bot)

**Article metrics tracked:**
- Word count: Target 800-1200 words
- Quality gates: 5 gates (Opening, Evidence, Voice, Structure, Chart)
- Publication success rate
- Chart generation success

## 🎯 Best Practices

### Topic Selection
- **Specific topics** work better than broad ones
- Include **talking points** for 800+ word articles
- **Technical depth** produces higher quality content

### Review Process
- **Always review PRs** before merging to blog
- Check **chart rendering** in your blog's preview
- Verify **British spelling** and Economist voice
- Ensure **reference links** work

### Scheduling
- **Weekly cadence** maintains consistent content
- **Monday generation** allows Tuesday review/publish
- **Manual triggers** for urgent/specific topics

## 🚨 Security Notes

- Personal access tokens have **repository scope only**
- Tokens expire - set calendar reminders
- Blog repository should be **public** or token needs access
- Never commit API keys - use repository secrets only

## 📞 Support

**Generated articles not meeting quality?**
- Adjust topic specificity
- Add more detailed talking points
- Review quarantined articles for patterns

**GitHub Actions not working?**
- Check repository variables and secrets
- Verify token permissions
- Review action logs for specific errors

**Blog formatting issues?**
- Verify Jekyll structure matches expectations
- Check chart path references
- Ensure YAML frontmatter compatibility

---

**🎉 Once configured, you'll have fully automated, publication-quality blog content delivered via PR every week!**