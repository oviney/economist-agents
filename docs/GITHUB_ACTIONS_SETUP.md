# GitHub Actions Setup Guide

This guide walks you through setting up automated content generation using GitHub Actions.

## Prerequisites

- GitHub repository with this code pushed
- API keys for OpenAI and/or Anthropic Claude

## Step 1: Add API Secrets

1. Go to your repository on GitHub
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

### Required Secrets

**OPENAI_API_KEY** (if using OpenAI):
- Name: `OPENAI_API_KEY`
- Value: Your OpenAI API key (starts with `sk-proj-...`)

**ANTHROPIC_API_KEY** (if using Anthropic Claude):
- Name: `ANTHROPIC_API_KEY`
- Value: Your Anthropic API key (starts with `sk-ant-...`)

> **Note**: You need at least one of these. The workflow will auto-detect which provider to use.

## Step 2: Verify Workflow File

The workflow file should already exist at `.github/workflows/content-pipeline.yml`

If you need to check or update it:

```bash
cat .github/workflows/content-pipeline.yml
```

## Step 3: Test Manual Trigger

1. Go to **Actions** tab in your GitHub repository
2. Click **Content Generation Pipeline** in the left sidebar
3. Click **Run workflow** dropdown (top right)
4. Fill in the options:
   - **Topic**: Custom topic (or leave blank to use queue)
   - **Run Scout**: Check if you want to discover new topics
   - **Run Board**: Check if you want editorial voting
   - **Interactive**: Leave unchecked for automated run
5. Click **Run workflow**

## Step 4: Review Results

The workflow will:
1. Install dependencies
2. Run the selected pipeline stages
3. Generate article and chart
4. Create a Pull Request with the content

Check:
- **Actions** tab for run status
- **Pull Requests** tab for generated PR
- **Artifacts** section in workflow run for downloads

## Step 5: Scheduled Runs (Optional)

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

### Manual Trigger Inputs

| Input | Description | Default |
|-------|-------------|---------|
| topic | Custom article topic | (uses content queue) |
| run_scout | Run topic discovery | false |
| run_board | Run editorial voting | false |
| interactive | Enable approval gates | false |

### Automatic Behavior

When triggered without inputs, the workflow:
1. Uses the content queue rotation (week-based)
2. Generates article automatically
3. Creates PR for review

## Troubleshooting

### "No API key configured"

**Problem**: Workflow fails with API key error

**Solution**: 
1. Verify secrets are named exactly: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
2. Check secrets are set at repository level (not environment level)
3. Re-run workflow after adding secrets

### "Module not found"

**Problem**: Python import errors

**Solution**: 
- Check `requirements.txt` includes all dependencies
- Verify workflow installs dependencies: `pip install -r requirements.txt`

### "Permission denied"

**Problem**: Workflow can't create PR

**Solution**:
1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **Read and write permissions**
3. Save and re-run workflow

### "Chart generation failed"

**Problem**: matplotlib errors in workflow

**Solution**:
- Charts need headless backend (already configured in code)
- If issues persist, check workflow uses: `matplotlib.use('Agg')`

## Advanced Configuration

### Change Output Directory

To output articles directly to a blog repository:

```yaml
env:
  OUTPUT_DIR: '/path/to/blog/_posts'
```

### Use Different Models

Set environment variables in workflow:

```yaml
env:
  OPENAI_MODEL: 'gpt-4o-mini'  # For cheaper runs
  # or
  ANTHROPIC_MODEL: 'claude-sonnet-4-20250514'
```

### Enable Interactive Mode

Interactive mode requires manual approval gates, which doesn't work in GitHub Actions.

For human review:
1. Use the PR created by the workflow
2. Review article in the PR diff
3. Approve/request changes before merging

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

